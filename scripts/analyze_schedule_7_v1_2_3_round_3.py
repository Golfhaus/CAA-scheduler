"""Accept the user's first two v1.2.3 rounds, then screen Routes 526/163/509.

All changes remain unpublished. New flying is proposed after full constraint and
itinerary review; no violation overrides or demand-as-load claims are introduced.
"""
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from analyze_schedule_7_v1_2_1_holds import HoldSearch
from analyze_schedule_7_v1_2_3_bwi import make_overlay,validate,demand,retime
from analyze_schedule_7_v1_2_3_utilization import good,screen_loops
from caa_scheduler.io import read_json,write_json,sha256_file
from caa_scheduler.optimization_overlay import apply_optimization_overlay
RELEASE='data/schedules/schedule_7_v1_2_2/canonical_schedule.json'
ACCEPTED='config/optimizations/schedule_7_v1_2_3_accepted_rounds_1_2.json'
BASE='data/schedules/schedule_7_v1_2_3_draft/canonical_schedule.json'
REPORT='config/proposals/schedule_7_v1_2_3_round_3_screen.json'

def overlay(s,plans,changes=(),banks=()):
    c=make_overlay(s,plans,banks=banks,retimings=changes)
    c['baseSchedule'].update(canonical=BASE,sha256=sha256_file(ROOT/BASE))
    c['id']='schedule-7-v1.2.3-round-3-screen'
    c['schedule'].update(id='schedule_7_v1_2_3_round_3_analysis',version='1.2.3',label='Schedule 7 v1.2.3 round 3 analysis; unpublished')
    # Use a distinct prefix for subsequent rounds, even when a route already has added legs.
    mapping={l['id']:l['id'].replace('V123-','V123-R3-') for l in c['insertLegs']}
    for l in c['insertLegs']:l['id']=mapping[l['id']]
    for a in c['bankAssignmentsToAdd']:a['legId']=mapping[a['legId']]
    return c

def approve():
    base=read_json(ROOT/RELEASE)
    c=deepcopy(read_json(ROOT/'config/proposals/schedule_7_v1_2_3_rounds_1_and_2_day_morning.json'))
    tul=read_json(ROOT/'config/proposals/schedule_7_v1_2_3_route_305_tul_conditional.json')
    for key in ('insertLegs','retimeLegs','bankAssignmentsToAdd','bankAssignmentReplacements','hubBankChanges'):
        c.setdefault(key,[]).extend(deepcopy(tul.get(key,[])))
    c['id']='schedule-7-v1.2.3-accepted-rounds-1-2'
    c['schedule'].update(id='schedule_7_v1_2_3_draft',version='1.2.3',label='Schedule 7 v1.2.3 accepted working draft; unpublished')
    c['approval']={'status':'approved for draft implementation; unpublished','userInstruction':"Very good. We'll proceed as you suggest above, including 305.",'publication':'Reserved to user decision','scope':'DAY morning and evening on 331; DAY-B9 and CLT/SDF feeders; PGD–JAX on 327; PWM–PHF and SYR–BUF on 145; Flight 1853 +5 minutes; MCI–TUL on 305, HRL originator 06:39, MCI-B3 shifted +2 minutes.'}
    s=HoldSearch(base);v,t=validate(s,c)
    assert good(v),v
    write_json(ROOT/ACCEPTED,c);write_json(ROOT/BASE,t)
    print('ACCEPTED',len(t['legs']),'flights; 0 errors; unpublished',flush=True)
    return v,t

def audit(s,trial):
    options=s.screen.enumerate(trial['legs'])
    slower=[];lost=[];improved=[]
    for od,old in s.screen.options.items():
        if not old:continue
        now=options.get(od,[])
        if not now:
            lost.append({'origin':od[0],'destination':od[1],'od':s.screen.od[od[0]][od[1]]});continue
        before=min(c['elapsed'] for c in old);after=min(c['elapsed'] for c in now)
        if before!=after:
            item={'origin':od[0],'destination':od[1],'od':s.screen.od[od[0]][od[1]],'oldFastestMinutes':before,'newFastestMinutes':after,'differenceMinutes':after-before}
            (slower if after>before else improved).append(item)
    return {'marketsWithSlowerBestItinerary':sorted(slower,key=lambda x:-x['od']),
            'marketsLosingAllConnections':lost,'lostUnderlyingOd':sum(x['od'] for x in lost),
            'marketsWithFasterBestItinerary':len(improved)}

def shortlist(s,name,route,city,fleet,start,end,markets,changes=(),limit=4):
    timed=HoldSearch(apply_optimization_overlay(s.base,overlay(s,[],changes)),allocate_gates=False) if changes else s
    # Reject permanent bank/30-minute-spacing conflicts before scoring a wide hold.
    # Added loops cannot repair an existing retimed flight outside every bank.
    bad=[]
    for change in changes:
        leg=next(l for l in timed.base['legs'] if l['id']==change['legId'])
        for op,station,minute in [('departure',leg['origin'],leg['departureMinute']),('arrival',leg['destination'],leg['arrivalMinute'])]:
            if station in timed.base['operatingPolicy']['hubs'] and timed.bank(station,minute) is None:
                bad.append({'kind':'bank_alignment','flight':leg['flight'],'station':station,'minute':minute,'operation':op})
        times=sorted(timed.pairs[leg['origin'],leg['destination']])
        if len(times)>1 and min((y-x)%1440 for x,y in zip(times,times[1:]+times[:1]))<30:
            bad.append({'kind':'hard_pair_spacing','origin':leg['origin'],'destination':leg['destination']})
    if bad:
        print(name,'permanent retiming conflicts',bad,flush=True)
        return {'name':name,'route':route,'retimings':list(changes),'selected':[],'retainedTimings':0,'preScreenRejection':bad}
    grid_minutes=15 if end-start>240 else 5
    if grid_minutes==15:
        timed.grid=lambda a,b:sorted({a,b,*range((a+14)//15*15,b+1,15)}) if b>=a else []
    if grid_minutes==15:
        # A wide rebuilt hub hold has many two-stop combinations. Rank the
        # timing grid with one-stop marginals, then fully enumerate selected
        # candidates. This is a bounded screen, not an exhaustive optimizer.
        cache={}
        def fast_score(added):
            values=[]
            for leg in added:
                key=(leg['origin'],leg['destination'],leg['departureMinute'],leg['arrivalMinute'])
                if key not in cache:
                    a,b,_,_=key;dep,arr,block=timed.screen.utc(leg)
                    weights=defaultdict(float);weights[a,b]+=1/block**2
                    def connect(airports,elapsed):
                        if len(set(airports))!=len(airports):return
                        source,target=airports[0],airports[-1]
                        circle=sum(timed.screen.distances[x,y] for x,y in zip(airports,airports[1:]))/timed.screen.distances[source,target]
                        if circle<=2.25:weights[source,target]+=.35/elapsed**2/circle**2
                    if a in timed.screen.hubs:
                        for oldleg in timed.arrivals[a]:
                            _,arrival,duration=timed.clocks[oldleg['id']];wait=(dep-arrival)%1440
                            if 30<=wait<=240:connect([oldleg['origin'],a,b],duration+wait+block)
                    if b in timed.screen.hubs:
                        for oldleg in timed.departures[b]:
                            departure,_,duration=timed.clocks[oldleg['id']];wait=(departure-arr)%1440
                            if 30<=wait<=240:connect([a,b,oldleg['destination']],block+wait+duration)
                    cache[key]=sum(timed.screen.od[x][y]*w/(timed.weights.get((x,y),0)+w) for (x,y),w in weights.items())
                values.append(cache[key])
            return sum(values),values
        timed.score=fast_score
    options=screen_loops(timed,route,city,fleet,start,end,markets)
    result={'name':name,'route':route,'station':city,'window':[start,end],'retimings':list(changes),'retainedTimings':len(options),'gridMinutes':grid_minutes,'rankingModel':'one-stop marginal for wide holds; full one/two-stop final comparison' if grid_minutes==15 else 'full marginal one/two-stop','selected':[],'rejected':[]}
    seen=set();attempts=defaultdict(int)
    for p in options:
        if p['city'] in seen or attempts[p['city']]>=2:continue
        attempts[p['city']]+=1
        c=overlay(s,[p],changes);v,t=validate(s,c)
        if good(v):
            result['selected'].append({'plans':[p],'retimings':list(changes),'score':p['score'],'validation':v})
            seen.add(p['city'])
            if len(seen)==limit:break
        elif len(result['rejected'])<10:result['rejected'].append({'plan':p,'validation':v})
    result['validatedTimingsByMarket']=dict(attempts)
    print(name,'retained',len(options),'selected',[(x['plans'][0]['city'],round(x['score'],1)) for x in result['selected']],flush=True)
    return result

def main():
    v,t=approve();s=HoldSearch(t);hubs=sorted(s.screen.hubs)
    r={'baseCanonical':BASE,'baseSha256':sha256_file(ROOT/BASE),'status':'proposed; unpublished','acceptedRoundsValidation':v,'model':'Pinned O-D, seat-uncapped full-capture relative-choice opportunities; not forecast loads or net incremental passengers','screens':[]}
    old=read_json(ROOT/REPORT) if (ROOT/REPORT).exists() and '--fresh' not in sys.argv else {}
    if old and old.get('baseSha256')!=r['baseSha256']:raise ValueError('Stale round-3 checkpoint')
    def add(*args,**kw):
        previous=next((x for x in old.get('screens',[]) if x['name']==args[0]),None)
        item=previous or shortlist(s,*args,**kw)
        r['screens'].append(item);write_json(ROOT/REPORT,r)
        return item
    def near(city,fleet,cap):
        return [c for c in s.screen.cities if c!=city and s.screen.utc(s.leg(city,c,0,fleet))[2]<=cap]
    add('526 DAL morning, unchanged existing clocks',526,'DAL','CRJ900',270,520,near('DAL','CRJ900',105),limit=5)
    add('163 DSM morning, unchanged existing clocks',163,'DSM','CRJ200',270,505,hubs+near('DSM','CRJ200',75),limit=4)
    add('509 SAT morning, unchanged existing clocks',509,'SAT','CRJ900',270,485,hubs+near('SAT','CRJ900',85),limit=4)
    add('526 PHF hold, unchanged clocks',526,'PHF','CRJ900',833,885,near('PHF','CRJ900',85))
    add('163 JAX hold, unchanged clocks',163,'JAX','CRJ200',1100,1125,near('JAX','CRJ200',85))
    add('509 BHM hold, unchanged clocks',509,'BHM','CRJ900',877,920,near('BHM','CRJ900',85))
    # A small shift of the 526 originator preserves its later PHF departure.
    for delay in (10,20):
        add(f'526 DAL morning, first flight +{delay} minutes',526,'DAL','CRJ900',270,520+delay,near('DAL','CRJ900',125),changes=retime(s,526,[delay,0,0,0]),limit=4)
    # Consolidate 163 idle time at MCI by moving its first flight into an earlier bank.
    for first in (335,395):
        add(f'163 earlier DSM originator {first//60:02}:{first%60:02}, MCI hold',163,'MCI','CRJ200',first+50+40,595,
            [c for c in near('MCI','CRJ200',100) if 1<=len(s.pairs['MCI',c])<=4],changes=retime(s,163,[first-545,0,0,0]),limit=4)
    # Move SAT's existing flight into an early arrival bank; preserve later service.
    for first in (270,329):
        add(f'509 earlier SAT originator {first//60:02}:{first%60:02}, MCI hold',509,'MCI','CRJ900',first+116+40,695,
            [c for c in near('MCI','CRJ900',120) if 1<=len(s.pairs['MCI',c])<=4],changes=retime(s,509,[first-525,0,0,0,0]),limit=4)
    add('509 earlier SAT originator 05:28, MCI hold',509,'MCI','CRJ900',444+40,695,
        [c for c in near('MCI','CRJ900',120) if 1<=len(s.pairs['MCI',c])<=4],changes=retime(s,509,[-197,0,0,0,0]),limit=3)
    add('163 consolidate idle time at JAX; three-leg advance',163,'JAX','CRJ200',970,1125,
        [c for c in near('JAX','CRJ200',80) if 1<=len(s.pairs['JAX',c])<=4],changes=retime(s,163,[-200,-120,-130,0]),limit=4)
    add('526 earlier DAL–PHF and later PHF–DAL; consolidate PHF hold',526,'PHF','CRJ900',693,985,
        [c for c in near('PHF','CRJ900',100) if 1<=len(s.pairs['PHF',c])<=4],changes=retime(s,526,[-140,100,88,84]),limit=4)
    add('509 earlier MCI–BHM; consolidate BHM hold',509,'BHM','CRJ900',777,920,
        [c for c in near('BHM','CRJ900',90) if 1<=len(s.pairs['BHM',c])<=4],changes=retime(s,509,[-154,-140,0,0,0]),limit=4)
    add('526 valid PHF hold rebuild, retain a DAL overnight',526,'PHF','CRJ900',733,1025,
        [c for c in near('PHF','CRJ900',110) if 1<=len(s.pairs['PHF',c])<=4],changes=retime(s,526,[-100,140,128,124]),limit=4)
    add('163 JAN evening extension with after-midnight return, unchanged existing clocks',163,'JAN','CRJ200',1243,1500,
        hubs+near('JAN','CRJ200',60),limit=3)
    for item in r['screens']:
        for x in item['selected'][:2]:
            if 'demand' in x:continue
            c=overlay(s,x['plans'],x['retimings']);_,trial=validate(s,c)
            x['demand']=demand(s,trial,{l['id'] for l in c['insertLegs']});x['reviewAudit']=audit(s,trial)
            print('AUDIT',item['name'],x['plans'][0]['city'],'slower',len(x['reviewAudit']['marketsWithSlowerBestItinerary']),'lost',len(x['reviewAudit']['marketsLosingAllConnections']),flush=True)
            write_json(ROOT/REPORT,r)
    write_json(ROOT/REPORT,r)

if __name__=='__main__':main()
