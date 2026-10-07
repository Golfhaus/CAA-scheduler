"""Unpublished utilization screen for Routes 327, 305 and 145.

Read the pinned released canonical. Preserve prior round-one proposal separately.
Rank timed loops with the existing demand model; fully validate selected options.
No automatic release or operating-rule overrides.
"""
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from analyze_schedule_7_v1_2_1_holds import HoldSearch
from analyze_schedule_7_v1_2_3_bwi import make_overlay,validate,demand,retime,review_audit
from caa_scheduler.io import read_json,write_json,sha256_file
from caa_scheduler.optimization_overlay import apply_optimization_overlay
BASE='data/schedules/schedule_7_v1_2_2/canonical_schedule.json'
REPORT='config/proposals/schedule_7_v1_2_3_utilization_screen.json'

def good(v):
    return not v['operatingErrors'] and not v['hardStopFailures'] and all(v[k]=='pass' for k in ('structural','overnight','planning','gates'))

def screen_loops(s,route,city,fleet,start,end,markets):
    candidates=defaultdict(list)
    for dest in markets:
        if dest==city or dest not in s.screen.cities:continue
        offset=s.leg(city,dest,0,fleet)['arrivalMinute']
        backoffset=s.leg(dest,city,0,fleet)['arrivalMinute']
        for departure in s.grid(start,min(end-offset-backoffset-40,1410 if city in s.screen.hubs else 1260)):
            out=s.leg(city,dest,departure,fleet)
            if s.bank(city,departure) is None or s.bank(dest,out['arrivalMinute']) is None:continue
            for back in s.grid(out['arrivalMinute']+40,min(end-backoffset,out['arrivalMinute']+150,1410 if dest in s.screen.hubs else 1260)):
                incoming=s.leg(dest,city,back,fleet)
                if s.bank(dest,back) is None or s.bank(city,incoming['arrivalMinute']) is None:continue
                if not s.spacing([out,incoming]):continue
                value,values=s.score([out,incoming])
                candidates[dest].append({'route':route,'city':dest,'legs':[out,incoming],'score':value,'legScores':values})
    best=[]
    for dest,choices in candidates.items():
        choices.sort(key=lambda c:-c['score'])
        retained=[]
        for c in choices:
            if any(abs(c['legs'][0]['departureMinute']-p['legs'][0]['departureMinute'])<10 and abs(c['legs'][1]['departureMinute']-p['legs'][1]['departureMinute'])<10 for p in retained):continue
            retained.append(c)
            if len(retained)==8:break
        best.extend(retained)
    return sorted(best,key=lambda c:-c['score'])

def shortlist(s,name,route,city,fleet,start,end,markets,changes=(),limit=5):
    # Pair spacing/connection opportunities must use the retimed comparison grid.
    change=make_overlay(s,[],retimings=changes)
    timed=HoldSearch(apply_optimization_overlay(s.base,change),allocate_gates=False) if changes else s
    options=screen_loops(timed,route,city,fleet,start,end,markets)
    result={'name':name,'route':route,'station':city,'window':[start,end],'retimings':list(changes),'screenedTimingCount':len(options),'selected':[],'rejected':[]}
    seen=set()
    for p in options:
        if p['city'] in seen:continue
        overlay=make_overlay(s,[p],retimings=changes)
        v,t=validate(s,overlay)
        item={'plans':[p],'banks':[],'retimings':list(changes),'score':p['score'],'validation':v}
        if good(v):
            result['selected'].append(item);seen.add(p['city'])
            if len(result['selected'])==limit:break
        elif len(result['rejected'])<12:result['rejected'].append({'city':p['city'],'legs':p['legs'],'validation':v})
    print(name,'screened',len(options),'selected',[(x['plans'][0]['city'],round(x['score'],1)) for x in result['selected']],flush=True)
    return result

def main():
    s=HoldSearch(read_json(ROOT/BASE));hubs=sorted(s.screen.hubs)
    report={'baseCanonical':BASE,'baseSha256':sha256_file(ROOT/BASE),'status':'analysis-only; publication reserved to user','model':'Pinned O-D, 30–240-minute one/two-stop choice opportunities; seat uncapped, full capture, not forecast loads or net incremental passengers','screens':[]}
    previous=read_json(ROOT/REPORT) if (ROOT/REPORT).exists() and '--fresh' not in sys.argv else {}
    if previous and previous.get('baseSha256')!=report['baseSha256']:
        raise ValueError('Stale utilization checkpoint: released baseline changed')
    for key in ('mciBankSensitivity','hrlRebuild','buffered327'):
        if key in previous:report[key]=previous[key]
    def add(*args,**kwargs):
        old=next((x for x in previous.get('screens',[]) if x['name']==args[0]),None)
        if old:
            report['screens'].append(old);return old
        r=shortlist(s,*args,**kwargs);report['screens'].append(r);write_json(ROOT/REPORT,report);return r
    add('327 PGD morning; unchanged existing clocks',327,'PGD','CRJ700',270,555,hubs+['PIE'])
    add('305 HRL morning; unchanged existing clocks',305,'HRL','CRJ700',270,550,hubs+['AUS','SAT','DAL','IAH','HOU'])
    add('305 SYR hold; unchanged existing clocks',305,'SYR','CRJ700',1042,1135,[c for c in s.screen.cities if len(s.pairs['SYR',c])<=4])
    # Earlier MCI arrival preserves 13:05 departure and creates a useful hub hold.
    for departure in (270,438,538):
        shifts=[departure-590,0,0]
        arrival=departure+147
        add(f'305 earlier HRL originator {departure//60:02}:{departure%60:02}; MCI hold',305,'MCI','CRJ700',arrival+40,745,
            [c for c in s.screen.cities if 1<=len(s.pairs['MCI',c])<=3],changes=retime(s,305,shifts),limit=4)
    # A 42-minute MCI–SYR advance makes the SYR-B5 arrival edge and preserves CLT clock.
    add('305 advance MCI–SYR 42 minutes; SYR hold',305,'SYR','CRJ700',1000,1135,
        [c for c in s.screen.cities if 1<=len(s.pairs['SYR',c])<=4],changes=retime(s,305,[-42,-42,0]),limit=6)
    add('145 PWM morning; unchanged existing clocks',145,'PWM','CRJ200',270,530,hubs)
    add('145 SYR hold; unchanged existing clocks',145,'SYR','CRJ200',678,805,[c for c in s.screen.cities if 1<=len(s.pairs['SYR',c])<=4])
    add('145 HPN hold; unchanged existing clocks',145,'HPN','CRJ200',939,1040,hubs)
    add('145 earlier PWM by 8 and HPN outbound later by 9; SYR hold',145,'SYR','CRJ200',670,814,
        [c for c in s.screen.cities if 1<=len(s.pairs['SYR',c])<=4],changes=retime(s,145,[-8,9,0,0]),limit=6)
    add('145 move HPN outbound to next SYR bank; consolidate hold',145,'SYR','CRJ200',678,920,
        [c for c in s.screen.cities if 1<=len(s.pairs['SYR',c])<=4],changes=retime(s,145,[0,115,0,0]),limit=6)
    for delay in (5,9):
        add(f'145 delay HPN outbound only {delay} minutes; SYR hold',145,'SYR','CRJ200',678,805+delay,
            [c for c in s.screen.cities if 1<=len(s.pairs['SYR',c])<=4],changes=retime(s,145,[0,delay,0,0]),limit=4)
    for item in report['screens']:
        for selected in item['selected'][:2]:
            if 'demand' in selected:continue
            change,t=review_audit(s,selected)
            selected['demand']=demand(s,t,{l['id'] for l in change['insertLegs']})
            print('audit',item['name'],selected['plans'][0]['city'],'slower',len(selected['reviewAudit']['marketsWithSlowerBestItinerary']),'lost',len(selected['reviewAudit']['marketsLosingAllConnections']),flush=True)
    write_json(ROOT/REPORT,report)




def mci_sensitivity():
    s=HoldSearch(read_json(ROOT/BASE))
    changes=retime(s,305,[-191,0,0])
    bc=[{'bankId':'MCI-B3','expectedStartMinute':485,'expectedEndMinute':545,'startMinute':487,'endMinute':547}]
    c=make_overlay(s,[],retimings=changes);c['hubBankChanges']=bc
    timed=HoldSearch(apply_optimization_overlay(s.base,c),allocate_gates=False)
    opts=screen_loops(timed,305,'MCI','CRJ700',586,745,[d for d in s.screen.cities if 1<=len(s.pairs['MCI',d])<=4])
    res={'name':'305 HRL 06:39 with two-minute MCI-B3 shift; preserve NEC feed','route':305,'bankChanges':bc,'retimings':changes,'selected':[],'rejected':[]}
    seen=set()
    for p in opts:
     if p['city'] in seen:continue
     c=make_overlay(s,[p],retimings=changes);c['hubBankChanges']=bc
     c['bankAssignmentReplacements'].append({'legId':changes[0]['legId'],'operation':'arrival','bankId':'MCI-B3'})
     v,t=validate(s,c)
     if good(v):
      x={'plans':[p],'banks':[],'bankChanges':bc,'retimings':changes,'score':p['score'],'validation':v}
      _,_=review_audit(s,x)
      x['demand']=demand(s,t,{l['id'] for l in c['insertLegs']})
      res['selected'].append(x);seen.add(p['city'])
      print('PASS',p['city'],round(p['score'],1),'slower',len(x['reviewAudit']['marketsWithSlowerBestItinerary']),'lost',len(x['reviewAudit']['marketsLosingAllConnections']),flush=True)
      if len(res['selected'])==4:break
     elif len(res['rejected'])<8:res['rejected'].append({'plan':p,'validation':v})
    r=read_json(ROOT/REPORT);r['mciBankSensitivity']=res;write_json(ROOT/REPORT,r)


def hrl_rebuild():
    s=HoldSearch(read_json(ROOT/BASE));results=[]
    for out,back,old1,old2,old3 in [(270,485,672,908,1175),(270,490,677,908,1175),(270,485,677,908,1175),(275,485,672,908,1175),(270,485,688,920,1180)]:
     p={'route':305,'legs':[s.leg('HRL','MCI',out,'CRJ700'),s.leg('MCI','HRL',back,'CRJ700')]}
     changes=retime(s,305,[old1-590,old2-785,old3-1175]);c=make_overlay(s,[p],retimings=changes);v,t=validate(s,c)
     x={'name':f'305 early HRL–MCI turn; rebuild {out}/{back}/{old1}/{old2}/{old3}','plans':[p],'banks':[],'retimings':changes,'validation':v}
     if good(v):
      _,_=review_audit(s,x);x['demand']=demand(s,t,{l['id'] for l in c['insertLegs']})
      print('PASS',x['name'],'slower',len(x['reviewAudit']['marketsWithSlowerBestItinerary']),'lost',len(x['reviewAudit']['marketsLosingAllConnections']),flush=True)
     else:print('FAIL',x['name'],[(z['check'],[f['message'] for f in z['findings']]) for z in v['blocking']],flush=True)
     results.append(x)
    r=read_json(ROOT/REPORT);r['hrlRebuild']=results;write_json(ROOT/REPORT,r)



def buffered_pgd():
    s=HoldSearch(read_json(ROOT/BASE));results=[]
    for dep,back in [(350,480),(355,480),(365,480)]:
     p={'route':327,'legs':[s.leg('PGD','JAX',dep,'CRJ700'),s.leg('JAX','PGD',back,'CRJ700')]}
     c=make_overlay(s,[p]);v,t=validate(s,c);x={'name':f'327 buffered later start {dep}/{back}','plans':[p],'banks':[],'retimings':[],'validation':v}
     if good(v):
      x['demand']=demand(s,t,{l['id'] for l in c['insertLegs']});print(x['name'],[(round(f['total'],1),f['departureClock'],f['arrivalClock']) for f in x['demand']['flights']],flush=True)
     results.append(x)
    r=read_json(ROOT/REPORT);r['buffered327']=results;write_json(ROOT/REPORT,r)

def finalize():
    s=HoldSearch(read_json(ROOT/BASE));r=read_json(ROOT/REPORT)
    find=lambda prefix:next(x for x in r['screens'] if x['name'].startswith(prefix))['selected'][0]
    chosen=[r['buffered327'][1],find('145 PWM'),find('145 delay HPN outbound only 5')]
    plans=[p for x in chosen for p in x['plans']]
    changes=[c for x in chosen for c in x['retimings']]
    c=make_overlay(s,plans,retimings=changes)
    c['id']='schedule-7-v1.2.3-utilization-round-2-proposal'
    c['schedule'].update(id='schedule_7_v1_2_3_utilization_round_2',version='1.2.3',label='Schedule 7 v1.2.3 utilization round 2; unpublished')
    c['approval']={'status':'proposed; unpublished','publication':'Reserved to user decision','scope':'PGD–JAX on 327; PWM–PHF and SYR–BUF on 145; five-minute delay to Flight 1853. Route 305 conditional rebuild stored separately.'}
    v,t=validate(s,c);assert good(v),v
    x={'plans':plans,'banks':[],'retimings':changes,'validation':v}
    _,_=review_audit(s,x);x['demand']=demand(s,t,{l['id'] for l in c['insertLegs']})
    write_json(ROOT/'config/proposals/schedule_7_v1_2_3_round_2.json',c)
    r['recommendedRound2']=x
    # Evaluate cumulatively, while leaving the saved round-one proposal intact.
    # Reconstruct the historical round-one snapshot: the working draft moves on.
    prior=read_json(ROOT/'config/proposals/schedule_7_v1_2_3_round_1.json')
    ds=HoldSearch(apply_optimization_overlay(s.base,prior));dc=make_overlay(ds,plans,retimings=changes)
    dc['id']='schedule-7-v1.2.3-utilization-cumulative-round-2'
    dc['schedule'].update(id='schedule_7_v1_2_3_cumulative_draft',version='1.2.3',label='Schedule 7 v1.2.3 rounds 1 and 2 proposed; unpublished')
    dc['approval']=deepcopy(c['approval'])
    cv,ct=validate(ds,dc)
    r['cumulativeOriginalRound1Validation']=cv
    # The prior morning PHF choice and the new PWM–PHF turn cannot coexist.
    # Use the previously screened DAY alternative, with all old flights intact.
    first=read_json(ROOT/'config/proposals/schedule_7_v1_2_3_round_1.json')
    byroute=defaultdict(list)
    for leg in first['insertLegs']:
        if leg['route']==331 and 'PHF' in (leg['origin'],leg['destination']):continue
        byroute[leg['route']].append(leg)
    byroute[331]=[s.leg('BWI','DAY',343,'CRJ700'),s.leg('DAY','BWI',473,'CRJ700')]+byroute[331]
    oldplans=[{'route':route,'legs':legs} for route,legs in byroute.items()]
    dc=make_overlay(s,oldplans+plans,banks=first['hubBanksToAdd'],retimings=changes)
    dc['id']='schedule-7-v1.2.3-rounds-1-and-2-day-morning-proposal'
    dc['schedule'].update(id='schedule_7_v1_2_3_cumulative_draft',version='1.2.3',label='Schedule 7 v1.2.3 proposed rounds 1 and 2; DAY morning on 331; unpublished')
    dc['approval']={'status':'proposed; unpublished','publication':'Reserved to user decision','scope':'Round 1 with DAY morning alternative on 331, plus Route 327 buffered PGD–JAX and Route 145 PWM–PHF/SYR–BUF; Flight 1853 five minutes later. Route 305 unchanged.'}
    cv,ct=validate(s,dc);assert good(cv),cv
    cx={'plans':oldplans+plans,'banks':first['hubBanksToAdd'],'retimings':changes,'validation':cv}
    _,_=review_audit(s,cx);cx['demand']=demand(s,ct,{l['id'] for l in dc['insertLegs']})
    write_json(ROOT/'config/proposals/schedule_7_v1_2_3_rounds_1_and_2_day_morning.json',dc)
    write_json(ROOT/'builds/schedule_7_v1_2_3_utilization/canonical_schedule.json',ct)
    r['cumulativeRound2']=cx
    conditional=r['mciBankSensitivity']['selected'][0]
    tc=make_overlay(s,conditional['plans'],retimings=conditional['retimings'])
    tc['hubBankChanges']=conditional['bankChanges']
    tc['bankAssignmentReplacements'].append({'legId':conditional['retimings'][0]['legId'],'operation':'arrival','bankId':'MCI-B3'})
    tc['id']='schedule-7-v1.2.3-route-305-tul-conditional'
    tc['schedule'].update(id='schedule_7_v1_2_3_route_305_tul_conditional',version='1.2.3',label='Schedule 7 v1.2.3 Route 305 TUL conditional; unpublished')
    tc['approval']={'status':'conditional; not included in recommended round 2','publication':'Reserved to user decision','requiredDecision':'Accept earlier HRL departure and longer city departure gap; eight modeled lost connections and 17 slower best itineraries; two-minute MCI-B3 shift.'}
    tv,_=validate(s,tc);assert good(tv)
    write_json(ROOT/'config/proposals/schedule_7_v1_2_3_route_305_tul_conditional.json',tc)
    r['conditional305Validation']=tv
    write_json(ROOT/REPORT,r)
    print('FINAL: standalone and combined pass; 0 errors, 0 hard-stop failures; unpublished',flush=True)

if __name__=='__main__':
    main()
    checkpoint=read_json(ROOT/REPORT)
    if 'mciBankSensitivity' not in checkpoint:mci_sensitivity()
    if 'hrlRebuild' not in checkpoint:hrl_rebuild()
    if 'buffered327' not in checkpoint:buffered_pgd()
    finalize()
