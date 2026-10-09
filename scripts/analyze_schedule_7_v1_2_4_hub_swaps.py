"""Review reciprocal hub-terminator exchanges; do not modify accepted flying."""
from collections import defaultdict,Counter
from copy import deepcopy
from itertools import combinations,product
from pathlib import Path
import sys,time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from analyze_schedule_7_v1_2_1_holds import HoldSearch
from analyze_schedule_7_v1_2_3_bwi import make_overlay,validate as raw_validate,demand
from analyze_schedule_7_v1_2_3_round_3 import audit
from analyze_schedule_7_v1_2_3_round_4 import inventory
from analyze_schedule_7_v1_2_3_utilization import good
from analyze_schedule_7_v1_2_4_xna import maintenance
from analyze_schedule_7_v1_2_4 import cache_network
from caa_scheduler.io import read_json,write_json,sha256_file
from caa_scheduler.optimization_overlay import apply_optimization_overlay
BASE='data/schedules/schedule_7_v1_2_4_round_4/canonical_schedule.json'
OUT='config/proposals/schedule_7_v1_2_4_hub_swaps_review.json'

def clock(t):return f'{t%1440//60:02}:{t%60:02}'+(' +1' if t>=1440 else '')

def load():
    if not (ROOT/BASE).exists():write_json(ROOT/BASE,read_json(ROOT/'data/schedules/schedule_7_v1_2_4_draft/canonical_schedule.json'))
    b=read_json(ROOT/BASE);s=HoldSearch(b);cache_network(s)
    allroutes={r:inventory(s,r) for r in sorted({l['route'] for l in b['legs']})}
    for r,x in allroutes.items():
        x['originator']=x['legs'][0]['origin'];x['startMinute']=x['legs'][0]['departureMinute']
    hubs=set(b['operatingPolicy']['hubs'])
    partners=[x for x in allroutes.values() if x['terminator'] in hubs]
    eligible=[x for x in partners if 1170<=x['finishMinute']<=1335]
    r=read_json(ROOT/OUT) if (ROOT/OUT).exists() else {'baseCanonical':BASE,'baseSha256':sha256_file(ROOT/BASE),
      'status':'Review only; no flying, bank or line change implemented.',
      'scope':'29 primary terminators, 19:30–22:15 inclusive local, at the five policy hubs. Partners may end outside the window; same fleet and different hub required. BHM is a focus city and is excluded from primary hub inventory.',
      'model':'Pinned O-D; seat-uncapped full-capture relative-choice one/two-stop opportunities, not predicted loads or incremental passengers.',
      'eligible':eligible,'allHubTerminators':partners,'pairs':[]}
    assert r['baseSha256']==sha256_file(ROOT/BASE)
    return s,r,allroutes

def fast_score(s,l):
    a,b=l['origin'],l['destination'];dep,arr,block=s.screen.utc(l)
    weights=defaultdict(float);weights[a,b]=1/block**2
    def connect(cities,elapsed):
        if len(set(cities))!=len(cities):return
        src,dst=cities[0],cities[-1]
        circle=sum(s.screen.distances[x,y] for x,y in zip(cities,cities[1:]))/s.screen.distances[src,dst]
        if circle<=2.25:weights[src,dst]+=.35/elapsed**2/circle**2
    for old in s.arrivals[a]:
        _,arrival,duration=s.clocks[old['id']];wait=(dep-arrival)%1440
        if 30<=wait<=240:connect([old['origin'],a,b],duration+wait+block)
    for old in s.departures[b]:
        departure,_,duration=s.clocks[old['id']];wait=(departure-arr)%1440
        if 30<=wait<=240:connect([a,b,old['destination']],block+wait+duration)
    return sum(s.screen.od[x][y]*w/(s.weights.get((x,y),0)+w) for (x,y),w in weights.items())

def direction(s,a,b):
    city,dest,fleet=a['terminator'],b['terminator'],a['fleet']
    earliest=a['finishMinute']+40;latest=1410
    result={'fromRoute':a['route'],'toRoute':b['route'],'origin':city,'destination':dest,
       'earliestDeparture':earliest,'latestDeparture':latest,'existingFrequency':len(s.pairs[city,dest]),
       'peerNextRoute':b['nextOriginator']['route'],'peerOriginatorMinute':b['nextOriginator']['departureMinute'],
       'timings':[],'rejectCounts':Counter()}
    if result['existingFrequency']>=6:
        result['rejectCounts']['six-flight frequency ceiling']=1;return result
    if earliest>latest:
        result['rejectCounts']['terminator too late for evening departure']=1;return result
    # Exact bank edges, connection thresholds and spacing edges supplement a
    # five-minute grid. Each departure is screened independently and both
    # directions are combined only after directional feasibility is established.
    offset=s.leg(city,dest,0,fleet)['arrivalMinute']
    points=set(s.grid(earliest,latest))
    for bank in s.base['hubBanks']:
        for edge in (bank['startMinute'],bank['endMinute']-1):
            if bank['hub']==city:points.add(edge)
            if bank['hub']==dest:points.add(edge-offset)
    for old in s.arrivals[city]:points.add(old['arrivalMinute']+30)
    for t in s.pairs[city,dest]:points.update((t-30,t+30))
    for dep in sorted(p for p in points if earliest<=p<=latest):
        leg=s.leg(city,dest,dep,fleet)
        # An aircraft operating day ends at 03:00. Do not conceal a crossing
        # as a wrap-around overnight or grant a bank/turn exception.
        if leg['arrivalMinute']>=1620:
            result['rejectCounts']['arrival after route operating-day end']=result['rejectCounts'].get('arrival after route operating-day end',0)+1;continue
        ron=1440+b['nextOriginator']['departureMinute']-leg['arrivalMinute']
        if ron<40:
            result['rejectCounts']['misses peer next-day originator']=result['rejectCounts'].get('misses peer next-day originator',0)+1;continue
        if not s.spacing([leg]):
            result['rejectCounts']['section 2.6 hard spacing']=result['rejectCounts'].get('section 2.6 hard spacing',0)+1;continue
        missing=[]
        for op,hub,minute in [('departure',city,dep),('arrival',dest,leg['arrivalMinute'])]:
            if s.bank(hub,minute) is None:missing.append({'hub':hub,'operation':op,'minute':minute%1440,'clock':clock(minute)})
        result['timings'].append({'leg':leg,'missingBanks':missing,'strict':not missing,'score':fast_score(s,leg),'ronMinutes':ron})
    result['timings'].sort(key=lambda x:(len(x['missingBanks']),-x['score'],x['leg']['departureMinute']))
    return result

def screen():
    s,r,allroutes=load();eligible={x['route'] for x in r['eligible']}
    done={tuple(x['routes']) for x in r['pairs']}
    for a,b in combinations(r['allHubTerminators'],2):
        key=(a['route'],b['route'])
        if not eligible.intersection(key) or a['fleet']!=b['fleet'] or a['terminator']==b['terminator'] or key in done:continue
        d1,d2=direction(s,a,b),direction(s,b,a)
        q={'id':f'{a["route"]}-{b["route"]}','routes':list(key),'fleet':a['fleet'],'hubs':[a['terminator'],b['terminator']],
           'lines':[a['line'],b['line']],'directions':[d1,d2]}
        if not d1['timings'] or not d2['timings']:q['status']='No reciprocal evening timing with current clocks'
        else:
            strict1=[x for x in d1['timings'] if x['strict']];strict2=[x for x in d2['timings'] if x['strict']]
            q['strictTimingsEachWay']=[len(strict1),len(strict2)]
            xs=sorted(d1['timings'],key=lambda x:(len(x['missingBanks']),-x['score']))[:6]
            ys=sorted(d2['timings'],key=lambda x:(len(x['missingBanks']),-x['score']))[:6]
            if strict1 and strict2:xs=strict1[:6];ys=strict2[:6]
            choices=[{'legs':[x['leg'],y['leg']],'score':x['score']+y['score'],
              'missingBanks':x['missingBanks']+y['missingBanks'],'rons':[x['ronMinutes'],y['ronMinutes']]} for x,y in product(xs,ys)]
            q['selectedTiming']=min(choices,key=lambda x:(len(x['missingBanks']),-x['score']))
            q['status']='Strict timing possible; requires line proof' if strict1 and strict2 else 'Conditional: existing banks do not cover the reciprocal exchange'
        # Save compact directional evidence; the complete candidate count and
        # strict count are retained while avoiding thousands of repeated rows.
        for d in q['directions']:
            d['validTimingCount']=len(d['timings']);d['strictTimingCount']=sum(x['strict'] for x in d['timings']);d['timings']=d['timings'][:8];d['rejectCounts']=dict(d['rejectCounts'])
        r['pairs'].append(q);write_json(ROOT/OUT,r)
        print('SCREEN',q['id'],q['hubs'],q['status'],q.get('strictTimingsEachWay'),flush=True)
    r['counts']={'eligibleTerminators':len(r['eligible']),'partnerHubTerminators':len(r['allHubTerminators']),
      'uniqueReciprocalPairs':len(r['pairs']),'strictTimingPairs':sum(x.get('strictTimingsEachWay',[0,0])[0]>0 and x.get('strictTimingsEachWay',[0,0])[1]>0 for x in r['pairs']),
      'conditionalTimingPairs':sum('selectedTiming' in x and not x.get('strictTimingsEachWay',[0,0])[0]*x.get('strictTimingsEachWay',[0,0])[1] for x in r['pairs'])}
    write_json(ROOT/OUT,r);print('COUNTS',r['counts'],flush=True)

if __name__=='__main__':
    if '--screen' in sys.argv:screen()


def line_cover(s,q,allroutes,pool,seconds=3):
    """Exact-cover bounded search of closed 9–12-day route cycles.

    Edges are complete unchanged aircraft days. Only terminal destinations on
    the two extension days change; the two next-day handoffs are mandatory.
    Other overnight handoffs may be reclosed at a common station. No flight
    suffix swap, timing change or extra aircraft day is hidden in the proof.
    """
    t0=time.monotonic();routes=sorted(r for r,x in allroutes.items() if x['line'] in pool)
    ix={r:i for i,r in enumerate(routes)};full=(1<<len(routes))-1
    ends={r:allroutes[r]['terminator'] for r in routes};finish={r:allroutes[r]['finishMinute'] for r in routes}
    for route,leg in zip(q['routes'],q['selectedTiming']['legs']):ends[route]=leg['destination'];finish[route]=leg['arrivalMinute']
    forced={}
    for a,b in q.get('peerPairs',[q['routes']]):
        forced.update({a:allroutes[b]['nextOriginator']['route'],b:allroutes[a]['nextOriginator']['route']})
    pred={target:source for source,target in forced.items()}
    origins=defaultdict(list)
    for route in routes:origins[allroutes[route]['originator']].append(route)
    allowed={}
    for route in routes:
        following=origins[ends[route]]
        if route in forced:following=[forced[route]]
        allowed[route]=[v for v in following if v in ix and (v not in pred or pred[v]==route)
          and 1440+allroutes[v]['startMinute']-finish[route]>=40]
        allowed[route].sort(key=lambda v:(v!=allroutes[route]['nextOriginator']['route'],v))
    hubtargets=set(s.base['operatingPolicy']['hubs']+s.base['operatingPolicy']['focusCities'])
    mxtargets=set(s.base['operatingPolicy']['ronTargetCities']);limit=s.base['operatingPolicy']['rollingRonWindowDays']+s.base['operatingPolicy']['rollingRonGraceDays']
    count=0;dead=set();cycle_cache={};timedout=False
    def legal(cycle):
        if not any(ends[r] in hubtargets for r in cycle):return False
        flags=[ends[r] in mxtargets for r in cycle];run=maximum=0
        for flag in flags*2:
            run=0 if flag else run+1;maximum=max(maximum,run)
        return min(maximum,len(cycle))<=limit
    def cycles(first,mask):
        nonlocal count
        key=(first,mask)
        if key in cycle_cache:return cycle_cache[key]
        found=[]
        def walk(path,used):
            nonlocal count
            count+=1
            if count%128==0 and time.monotonic()-t0>seconds:raise TimeoutError
            last=path[-1]
            if len(path)>=9 and first in allowed[last] and legal(path):found.append(path[:])
            if len(path)==12:return
            for v in allowed[last]:
                bit=1<<ix[v]
                if mask&bit and not used&bit:walk(path+[v],used|bit)
        walk([first],1<<ix[first])
        found.sort(key=lambda p:(len(p)!=11,-len(p),sum(allroutes[x]['nextOriginator']['route']!=y for x,y in zip(p,p[1:]+p[:1])),p))
        cycle_cache[key]=found;return found
    def cover(mask):
        if not mask:return []
        if mask in dead:return None
        n=mask.bit_count()
        if not any(9*k<=n<=12*k for k in range(1,n//9+1)):dead.add(mask);return None
        first=routes[(mask&-mask).bit_length()-1]
        for cycle in cycles(first,mask):
            used=sum(1<<ix[v] for v in cycle)
            answer=cover(mask^used)
            if answer is not None:return [cycle]+answer
        dead.add(mask);return None
    try:answer=cover(full)
    except TimeoutError:answer=None;timedout=True
    result={'poolLines':sorted(pool),'routeCount':len(routes),'status':'proved' if answer else 'search budget exhausted' if timedout else 'no 9–12-day cover in this pool',
      'visitedStates':count,'elapsedSeconds':round(time.monotonic()-t0,3),'cycles':answer or []}
    if answer:
        result['cycleLengths']=[len(c) for c in answer]
        result['newOvernightHandoffs']=[{'fromRoute':x,'toRoute':y,'station':ends[x],
            'ronMinutes':1440+allroutes[y]['startMinute']-finish[x],
            'oldNextRoute':allroutes[x]['nextOriginator']['route']}
          for cycle in answer for x,y in zip(cycle,cycle[1:]+cycle[:1]) if allroutes[x]['nextOriginator']['route']!=y]
    return result


def prove_lines():
    s,r,allroutes=load()
    for q in r['pairs']:
        if 'selectedTiming' not in q or 'lineProof' in q:continue
        base=set(q['lines']);fleet=q['fleet']
        other=sorted({x['line'] for x in allroutes.values() if x['fleet']==fleet}-base)
        attempts=[];answer=None
        # Start with exactly the paired lines; add at most two other existing
        # same-fleet lines if common overnight stations can reclose the graph.
        for n in range(min(2,len(other))+1):
            for extra in combinations(other,n):
                pool=base|set(extra)
                sizes=Counter(x['line'] for x in allroutes.values() if x['line'] in pool)
                total=sum(sizes.values())
                if not any(9*k<=total<=12*k for k in range(1,total//9+1)):continue
                nodes={line:{x['originator'] for x in allroutes.values() if x['line']==line}|{x['terminator'] for x in allroutes.values() if x['line']==line} for line in pool}
                reached=set(base)
                while True:
                    new={v for v in pool-reached if any(nodes[v]&nodes[w] for w in reached)}
                    if not new:break
                    reached|=new
                if reached!=pool:continue
                result=line_cover(s,q,allroutes,pool,seconds=2)
                attempts.append(result)
                if result['status']=='proved':answer=result;break
            if answer:break
        q['lineProof']=answer or {'status':'not proved in bounded pool search','attempts':attempts}
        if answer:q['lineProof']['attemptedPools']=len(attempts)
        write_json(ROOT/OUT,r)
        print('LINES',q['id'],q['lineProof']['status'],q['lineProof'].get('cycleLengths'),q['lineProof'].get('poolLines'),flush=True)
    r['counts']['lineProvedConditionalPairs']=sum(q.get('lineProof',{}).get('status')=='proved' for q in r['pairs'])
    write_json(ROOT/OUT,r)

if __name__=='__main__' and '--lines' in sys.argv:prove_lines()


def candidate_overlay(s,q,allroutes,legs=None):
    legs=legs or q['selectedTiming']['legs']
    plans=[{'route':route,'legs':[leg]} for route,leg in zip(q['routes'],legs)]
    c=make_overlay(s,plans)
    c['baseSchedule'].update(canonical=BASE,sha256=sha256_file(ROOT/BASE))
    c['id']='schedule-7-v1.2.4-hub-swap-'+q['id']
    c['schedule'].update(id='schedule_7_v1_2_4_swap_'+q['id'].replace('-','_'),version='1.2.4',label='Unapproved reciprocal hub-swap candidate '+q['id'])
    ids={l['id']:l['id'].replace('V123-',f'V124-SWAP-{q["id"]}-') for l in c['insertLegs']}
    for l in c['insertLegs']:l['id']=ids[l['id']]
    for x in c['bankAssignmentsToAdd']:x['legId']=ids[x['legId']]
    c['approval']={'status':'analysis only; bank/line changes not approved','publication':'Reserved to user decision',
      'scope':f'{len(legs)} reciprocal extension legs with explicit line rebuilding and additional bank windows. Original clocks retained.'}
    # Assign every missing touch to an explicitly proposed window. No overlap
    # with existing windows, no wider-than-60-minute bank, no silent exception.
    available=deepcopy(s.base['hubBanks']);assignments=[];newbanks=[]
    for l in c['insertLegs']:
        for op,hub,minute in [('departure',l['origin'],l['departureMinute']%1440),('arrival',l['destination'],l['arrivalMinute']%1440)]:
            bank=next((b for b in available if b['hub']==hub and b['startMinute']<=minute<b['endMinute']),None)
            if bank is None:
                lo=max([0]+[b['endMinute'] for b in available if b['hub']==hub and b['endMinute']<=minute])
                hi=min([1440]+[b['startMinute'] for b in available if b['hub']==hub and b['startMinute']>minute])
                start=max(lo,min(minute//60*60,hi-60));end=min(start+60,hi)
                assert start<=minute<end and end-start<=60
                bank={'id':f'{hub}-SWAP-{q["id"]}-N{len(newbanks)+1}','hub':hub,'startMinute':start,'endMinute':end}
                available.append(bank);newbanks.append(bank)
            assignments.append({'legId':l['id'],'operation':op,'bankId':bank['id']})
    c['bankAssignmentsToAdd']=assignments;c['hubBanksToAdd']=newbanks
    c['hubBankCountOverrides']={hub:s.base['operatingPolicy']['hubBankCounts'][hub]+sum(b['hub']==hub for b in newbanks) for hub in {b['hub'] for b in newbanks}}
    proof=q['lineProof'];pool=set(proof['poolLines']);cycles=proof['cycles']
    labels=sorted(pool);used={l['line'] for l in s.base['legs']}-pool
    for a in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        for b in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            label=a+b
            if len(labels)>=len(cycles):break
            if label not in labels and label not in used:labels.append(label)
        if len(labels)>=len(cycles):break
    numbers=sorted(route for route,x in allroutes.items() if x['line'] in pool)
    mapping={};i=0;changes=[]
    for label,cycle in zip(labels,cycles):
        for day,source in enumerate(cycle,1):
            target=numbers[i];i+=1;old=allroutes[source];mapping[source]=target
            changes.append({'sourceRoute':source,'expectedLine':old['line'],'expectedDay':old['day'],'expectedFleet':q['fleet'],
              'targetRoute':target,'line':label,'day':day})
    assert i==len(numbers)
    c['routeReassignments']=changes
    for l in c['insertLegs']:l['route']=mapping[l['route']]
    return c


def validate_candidates():
    s,r,allroutes=load()
    for q in sorted(r['pairs']+r.get('coordinatedCandidates',[]),key=lambda q:-q.get('selectedTiming',{}).get('score',0)):
        if q.get('lineProof',{}).get('status')!='proved' or 'fullValidation' in q:continue
        c=candidate_overlay(s,q,allroutes);v,t=raw_validate(s,c)
        q['fullValidation']=v;q['proposedBanks']=c['hubBanksToAdd'];q['routeReassignments']=c['routeReassignments']
        q['validationStatus']='passes only with the proposed new banks and line reconstruction' if good(v) else 'candidate rejected by full validation'
        if good(v):
            # Day clocks and every original leg survive; only route/line/day
            # identities in the proof pool change. Outside-pool identities stay.
            now={l['id']:l for l in t['legs']};pool=set(q['lineProof']['poolLines'])
            for old in s.base['legs']:
                target=now[old['id']]
                keys=('flight','pairing','fleet','origin','destination','departure','arrival','departureMinute','arrivalMinute')
                assert all(old[k]==target[k] for k in keys)
                if old['line'] not in pool:assert old==target
            assert len(t['legs'])==len(s.base['legs'])+len(c['insertLegs']) and t['schedule']['fleetCounts']==s.base['schedule']['fleetCounts']
            lengths=Counter({line:len({l['day'] for l in t['legs'] if l['line']==line}) for line in {x['line'] for x in c['routeReassignments']}})
            assert all(9<=n<=12 for n in lengths.values())
            q['demand']=demand(s,t,{l['id'] for l in c['insertLegs']});q['connectionAudit']=audit(s,t)
            options=s.screen.enumerate(t['legs']);loads,records=s.screen.allocate(options)
            legby={l['id']:l for l in t['legs']}
            for f in q['demand']['flights']:
                feeders=set();onwards=set();sourcegroups=Counter();targetgroups=Counter()
                for x in records[f['id']]:
                    n=x['legs'].index(f['id'])
                    if n:feeders.add(x['legs'][n-1])
                    if n+1<len(x['legs']):onwards.add(x['legs'][n+1])
                    sourcegroups[s.screen.cities[x['origin']]['group']]+=x['opportunity']
                    targetgroups[s.screen.cities[x['destination']]['group']]+=x['opportunity']
                f['inboundFeeders']=[{k:legby[j][k] for k in ('flight','origin','destination','departure','arrival')} for j in sorted(feeders)]
                f['outboundConnections']=[{k:legby[j][k] for k in ('flight','origin','destination','departure','arrival')} for j in sorted(onwards)]
                f['originGroups']=dict(sourcegroups);f['destinationGroups']=dict(targetgroups)
            q['maintenance']={line:maintenance(t,line) for line in lengths}
            baseline_handoffs={x['route']:x['nextOriginator']['route'] for x in allroutes.values()}
            newhandoffs={}
            for line in lengths:
                ls=defaultdict(list)
                for l in t['legs']:
                    if l['line']==line:ls[l['day']].append(l)
                for day in sorted(ls):
                    nxt=1 if day==max(ls) else day+1
                    a=max(ls[day],key=lambda l:l['sequenceWithinRoute']);b=min(ls[nxt],key=lambda l:l['sequenceWithinRoute'])
                    newhandoffs[a['route']]=b['route']
            # Per-line evidence uses original routes to make the handoff easy
            # to follow even though canonical numbering must remain sequential.
            path='config/proposals/schedule_7_v1_2_4_swap_'+q['id'].replace('-','_')+'.json'
            write_json(ROOT/path,c);q['overlay']=path
        write_json(ROOT/OUT,r)
        print('VALIDATED',q['id'],v['operatingErrors'],v['gates'],q['lineProof']['cycleLengths'],
              [(round(f['total'],1),f['departureClock'],f['arrivalClock']) for f in q.get('demand',{}).get('flights',[])],flush=True)
    r['counts']['fullyValidatedConditionalPairs']=sum(good(q['fullValidation']) for q in r['pairs'] if 'fullValidation' in q)
    write_json(ROOT/OUT,r)

if __name__=='__main__' and '--validate' in sys.argv:validate_candidates()


def coordinated():
    s,r,allroutes=load();r.setdefault('coordinatedCandidates',[])
    done={x['id'] for x in r['coordinatedCandidates']}
    poolpairs=[q for q in r['pairs'] if 'selectedTiming' in q and set(q['lines'])=={'AD'}]
    tests=0;proved=0
    for a,b in combinations(poolpairs,2):
        if set(a['routes'])&set(b['routes']):continue
        tests+=1;key=a['id']+'__'+b['id']
        if key in done:continue
        q={'id':key,'routes':a['routes']+b['routes'],'peerPairs':[a['routes'],b['routes']],
          'fleet':'CRJ200','hubs':a['hubs']+b['hubs'],'lines':['AD'],
          'status':'Coordinated two-pair review; every paired terminator is inside the requested window',
          'selectedTiming':{'legs':a['selectedTiming']['legs']+b['selectedTiming']['legs'],
            'score':a['selectedTiming']['score']+b['selectedTiming']['score'],
            'missingBanks':a['selectedTiming']['missingBanks']+b['selectedTiming']['missingBanks'],
            'rons':a['selectedTiming']['rons']+b['selectedTiming']['rons']}}
        if not s.spacing(q['selectedTiming']['legs']):continue
        proof=line_cover(s,q,allroutes,{'AD'},seconds=3)
        if proof['status']!='proved':continue
        q['lineProof']=proof;r['coordinatedCandidates'].append(q);proved+=1
        write_json(ROOT/OUT,r);print('COORDINATED',key,proof['cycleLengths'],flush=True)
    r['coordinatedSearch']={'scope':'Two disjoint reciprocal pairs on Line AD; unchanged complete route days and forced peer successors. No other fleet-wide multi-pair search.',
                           'testedCombinations':tests,'provedCombinations':len(r['coordinatedCandidates'])}
    write_json(ROOT/OUT,r);print('COORDINATED SEARCH',r['coordinatedSearch'],flush=True)

if __name__=='__main__' and '--coordinated' in sys.argv:coordinated()
