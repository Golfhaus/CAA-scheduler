"""Bounded extension review of Routes 304, 125 and 157; no implementation."""
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
import analyze_schedule_7_v1_2_4 as first
import analyze_schedule_7_v1_2_3_round_3 as screens
from analyze_schedule_7_v1_2_1_holds import HoldSearch
from analyze_schedule_7_v1_2_3_bwi import make_overlay,retime,demand
from analyze_schedule_7_v1_2_3_round_3 import audit
from analyze_schedule_7_v1_2_3_round_4 import inventory
from analyze_schedule_7_v1_2_3_utilization import good
from analyze_schedule_7_v1_2_4_xna import maintenance
from caa_scheduler.io import read_json,write_json,sha256_file
BASE='data/schedules/schedule_7_v1_2_4_round_3/canonical_schedule.json'
OUT='config/proposals/schedule_7_v1_2_4_extensions_review.json'

def overlay(s,plans,changes=(),banks=()):
    c=make_overlay(s,plans,banks=banks,retimings=changes)
    c['baseSchedule'].update(canonical=BASE,sha256=sha256_file(ROOT/BASE))
    c['id']='schedule-7-v1.2.4-extension-review'
    c['schedule'].update(id='schedule_7_v1_2_4_extension_analysis',version='1.2.4',label='Schedule 7 v1.2.4 extension review; unpublished')
    mapping={l['id']:l['id'].replace('V123-','V124-R4-') for l in c['insertLegs']}
    for l in c['insertLegs']:l['id']=mapping[l['id']]
    for a in c['bankAssignmentsToAdd']:a['legId']=mapping[a['legId']]
    return c

def main():
    if '--accept' in sys.argv:accept();return
    p=ROOT/BASE
    if not p.exists():write_json(p,read_json(ROOT/'data/schedules/schedule_7_v1_2_4_draft/canonical_schedule.json'))
    s=HoldSearch(read_json(p));first.cache_network(s)
    r=read_json(ROOT/OUT) if (ROOT/OUT).exists() else {'baseCanonical':BASE,'baseSha256':sha256_file(p),
      'status':'Analysis only; proposed flying not implemented. Publication reserved to user.',
      'model':'Pinned O-D; seat-uncapped full-capture relative-choice one/two-stop opportunities, not forecast loads or incremental passengers',
      'inventory':[inventory(s,n) for n in (304,125,157)],'screens':[],'trials':[]}
    assert r['baseSha256']==sha256_file(p)
    screens.overlay=overlay;screens.validate=first.validate
    def add(name,route,city,fleet,start,end,markets,changes=(),limit=5):
        if any(x['name']==name for x in r['screens']):return
        x=screens.shortlist(s,name,route,city,fleet,start,end,markets,changes=changes,limit=limit)
        r['screens'].append(x);write_json(ROOT/OUT,r)
    def near(city,fleet,start,end):return [d for d in s.screen.cities if d!=city and s.screen.utc(s.leg(city,d,0,fleet))[2]<=(end-start-40)/2]
    if '--screen' in sys.argv:
        for item in r['inventory']:
            city=item['terminator'];fleet=item['fleet'];start=item['finishMinute']+40
            end=min(1560,item['nextOriginator']['departureMinute']+1440-40)
            add(f"{item['route']} evening; all current clocks retained",item['route'],city,fleet,start,end,near(city,fleet,start,end))
    if '--audit' in sys.argv:
        for item in r['screens']:
            for x in item['selected'][:5]:
                if 'demand' in x:continue
                c=overlay(s,x['plans'],x['retimings']);v,t=first.validate(s,c);assert good(v)
                x['demand']=demand(s,t,{l['id'] for l in c['insertLegs']});x['reviewAudit']=audit(s,t)
                x['maintenance']={line:maintenance(t,line) for line in {i['line'] for i in r['inventory'] if i['route']==item['route']}}
                print('AUDIT',item['name'],x['plans'][0]['city'],[(round(f['total'],1),f['departureClock'],f['arrivalClock']) for f in x['demand']['flights']],flush=True)
                write_json(ROOT/OUT,r)
    if '--rebuild' in sys.argv:
        # Earlier final MCI–HRL requires retiming the preceding BLV cycle;
        # screen modest advances into banks, preserving the next HRL originator.
        for shifts in ([0,0,0,0,-60,-40],[0,0,0,0,-90,-70]):
            start=1182+shifts[-1]+40
            add(f'304 earlier HRL terminator {shifts[-1]}',304,'HRL','CRJ700',start,1560,near('HRL','CRJ700',start,1560),retime(s,304,shifts),limit=3)
        # Moving the SDF return earlier might reach more of DAY's evening banks.
        for shift in (-30,-60,-90):
            start=1183+shift+40
            add(f'125 earlier SDF return {shift}',125,'DAY','CRJ200',start,1500,near('DAY','CRJ200',start,1500),retime(s,125,[0,0,0,0,0,shift]),limit=3)
        for shift in (-30,-60):
            start=1184+shift+40
            add(f'157 earlier OMA terminator {shift}',157,'OMA','CRJ200',start,1560,near('OMA','CRJ200',start,1560),retime(s,157,[0,0,0,0,shift-30,shift]),limit=3)
    if '--holds' in sys.argv:
        for delay in (0,9):
            add(f'125 morning SYR hold; PVD outbound +{delay}',125,'SYR','CRJ200',366,475+delay,near('SYR','CRJ200',366,475+delay),retime(s,125,[0,delay,0,0,0,0]),limit=4)
    if '--buffered' in sys.argv:
        plans=[{'route':157,'city':'BHM','legs':[s.leg('OMA','BHM',1230,'CRJ200'),s.leg('BHM','OMA',1408,'CRJ200')]}]
        c=overlay(s,plans);v,t=first.validate(s,c)
        x={'name':'157 buffered unchanged OMA–BHM evening turn','plans':plans,'retimings':[], 'validation':v}
        if good(v):
            x['demand']=demand(s,t,{l['id'] for l in c['insertLegs']});x['reviewAudit']=audit(s,t);x['maintenance']=maintenance(t,'AE')
        print('BUFFERED',v,flush=True)
        r['trials']=[z for z in r['trials'] if z['name']!=x['name']]+[x]
    if '--finalize' in sys.argv:
        roc=deepcopy(next(x for q in r['screens'] if q['name']=='125 morning SYR hold; PVD outbound +9' for x in q['selected']))
        bhm={'route':157,'city':'BHM','legs':[s.leg('OMA','BHM',1230,'CRJ200'),s.leg('BHM','OMA',1403,'CRJ200')]}
        plans=roc['plans']+[bhm];changes=roc['retimings']
        c=overlay(s,plans,changes);v,t=first.validate(s,c);assert good(v),v
        x={'name':'Recommended: 125 morning ROC and 157 evening BHM; retain 304','plans':plans,'retimings':changes,'validation':v,
           'demand':demand(s,t,{l['id'] for l in c['insertLegs']}),'reviewAudit':audit(s,t),
           'maintenance':{line:maintenance(t,line) for line in ('AA','AD','AE')}}
        options=s.screen.enumerate(t['legs']);loads,records=s.screen.allocate(options)
        x['retimingDemandAudit']=[]
        for change in changes:
            old=s.legs[change['legId']];new=next(l for l in t['legs'] if l['id']==old['id'])
            before={tuple(z['legs']) for z in s.screen.connections[old['id']]};after={tuple(z['legs']) for z in records[old['id']]}
            x['retimingDemandAudit'].append({'flight':old['flight'],'oldDeparture':old['departure'],'newDeparture':new['departure'],
              'oldTotalOpportunity':sum(s.screen.loads[old['id']].values()),'newTotalOpportunity':sum(loads[old['id']].values()),
              'lostConnectingChoices':len(before-after),'addedConnectingChoices':len(after-before)})
        for route in (304,125,157):
            inv=next(i for i in r['inventory'] if i['route']==route)
            ls=sorted((l for l in t['legs'] if l['route']==route),key=lambda l:l['sequenceWithinRoute'])
            added=[l for l in ls if l['id'] not in s.legs]
            x.setdefault('utilization',[]).append({'route':route,'line':inv['line'],'day':inv['day'],
              'oldBlockMinutes':inv['blockMinutes'],'newBlockMinutes':sum(s.screen.utc(l)[2] for l in ls),
              'oldFinish':inv['arrival'],'newFinish':ls[-1]['arrival'],
              'nextOriginator':inv['nextOriginator'],'ronMinutes':1440+inv['nextOriginator']['departureMinute']-ls[-1]['arrivalMinute'],
              'addedAircraftTurnsMinutes':[b['departureMinute']-a['arrivalMinute'] for a,b in zip(ls,ls[1:]) if a['id'] not in s.legs or b['id'] not in s.legs]})
        c['approval']={'status':'proposed; not implemented','userInstruction':'Look at routes 304, 125, and 157 for extension.',
          'scope':'125 SYR–ROC morning turn, Flight 1811 +9 minutes; 157 OMA–BHM evening turn; retain 304.',
          'publication':'Reserved to user decision'}
        c['id']='schedule-7-v1.2.4-proposed-125-157'
        c['schedule'].update(id='schedule_7_v1_2_4_extensions_proposed',label='Schedule 7 v1.2.4 proposed 125/157 extensions; unpublished')
        # No working canonical is mutated. Provisional flight numbers reflect this joint proposal.
        old={l['id']:l for l in s.base['legs']};now={l['id']:l for l in t['legs']}
        for i,l in old.items():
            expected={**l,'sequenceWithinRoute':now[i]['sequenceWithinRoute']}
            if l['flight']==1811:expected.update(departure='08:44',arrival='09:47',departureMinute=524,arrivalMinute=587)
            assert expected==now[i],i
        assert len(t['legs'])==1168 and t['hubBanks']==s.base['hubBanks']
        r['recommended']=x;r['recommendedOverlay']='config/proposals/schedule_7_v1_2_4_proposed_125_157.json'
        r['searchScope']='Bounded 5/15-minute timing screens for same-city evening returns; modest route retiming; 125 SYR morning hold. No new banks, fleet swaps, or network-wide exhaustive rebuilding.'
        write_json(ROOT/r['recommendedOverlay'],c)
        print('JOINT',v,'opportunities',[(l['flight'],round(l['total'],1)) for l in x['demand']['flights']],flush=True)
    write_json(ROOT/OUT,r)
def accept():
    release='data/schedules/schedule_7_v1_2_3/canonical_schedule.json'
    draft='data/schedules/schedule_7_v1_2_4_draft/canonical_schedule.json'
    master='config/optimizations/schedule_7_v1_2_4_accepted_rounds_1_4.json'
    from caa_scheduler.optimization_overlay import apply_optimization_overlay
    from caa_scheduler.operating_validation import validate_operating_rules
    b=read_json(ROOT/BASE);s=HoldSearch(b);first.cache_network(s)
    c=deepcopy(read_json(ROOT/'config/proposals/schedule_7_v1_2_4_proposed_125_157.json'))
    assert c['baseSchedule']['sha256']==sha256_file(ROOT/BASE)
    c['id']='schedule-7-v1.2.4-accepted-round-4'
    c['schedule'].update(id='schedule_7_v1_2_4_draft',label='Schedule 7 v1.2.4 working draft; unpublished')
    c['approval']={'status':'approved for draft implementation; unpublished',
        'userInstruction':'Add the suggested additions from the last few messages to 1.2.4.',
        'scope':'125 SYR–ROC morning turn and Flight 1811 +9 minutes; 157 OMA–BHM evening turn. Retain 304.',
        'publication':'Reserved to user decision'}
    v,t=first.validate(s,c);assert good(v),v
    current=read_json(ROOT/draft)
    assert current==b or current==t,'Working draft diverged from reviewed proposal'
    historic_report=ROOT/'data/schedules/schedule_7_v1_2_4_round_3/draft_report.json'
    if not historic_report.exists():
        old_report=read_json(ROOT/'data/schedules/schedule_7_v1_2_4_draft/draft_report.json')
        assert old_report['canonicalSha256']==sha256_file(ROOT/BASE)
        write_json(historic_report,old_report)
    prior=deepcopy(read_json(ROOT/'config/optimizations/schedule_7_v1_2_4_accepted_rounds_1_3.json'))
    for key in ('insertLegs','retimeLegs','bankAssignmentsToAdd','bankAssignmentReplacements','hubBanksToAdd','operatingOverrides'):
        prior.setdefault(key,[]).extend(deepcopy(c.get(key,[])))
    prior['id']='schedule-7-v1.2.4-accepted-rounds-1-4'
    earlier_scope=prior['approval']['scope'];prior['approval']=deepcopy(c['approval'])
    prior['approval']['scope']=earlier_scope+' '+c['approval']['scope']
    released=read_json(ROOT/release)
    assert prior['baseSchedule']['sha256']==sha256_file(ROOT/release)
    rebuilt=apply_optimization_overlay(released,prior)
    assert rebuilt==t,'Cumulative replay differs from sequential approval'
    old={l['id']:l for l in released['legs']};now={l['id']:l for l in t['legs']}
    for i,l in old.items():
        target={**l,'sequenceWithinRoute':now[i]['sequenceWithinRoute']}
        if l['flight']==1739:target.update(departure='05:47',arrival='06:24',departureMinute=347,arrivalMinute=384)
        if l['flight']==1811:target.update(departure='08:44',arrival='09:47',departureMinute=524,arrivalMinute=587)
        assert target==now[i],f'Unexpected released-flight change: {i}'
    assert len(t['legs'])==1168 and {l['flight'] for i,l in now.items() if i not in old}==set(range(2155,2171))
    assert t['hubBanks']==released['hubBanks'] and t['schedule']['fleetCounts']==released['schedule']['fleetCounts']
    r=read_json(ROOT/OUT);assert r['baseSha256']==sha256_file(ROOT/BASE)
    ids={l['id'] for l in c['insertLegs']}
    actual_demand=demand(s,t,ids);incremental_audit=audit(s,t)
    # Allocation sums can differ in their final floating-point digits between
    # Python processes. Verify material model values with a tight tolerance.
    import math
    def same(a,b,path='model'):
        if isinstance(a,(float,int)) and isinstance(b,(float,int)):
            assert math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-8),(path,a,b)
        elif isinstance(a,dict) and isinstance(b,dict):
            assert a.keys()==b.keys(),(path,a.keys(),b.keys())
            for k in a:same(a[k],b[k],path+'.'+str(k))
        elif isinstance(a,list) and isinstance(b,list):
            assert len(a)==len(b),(path,len(a),len(b))
            for i,(x,y) in enumerate(zip(a,b)):same(x,y,path+'.'+str(i))
        else:assert a==b,(path,a,b)
    same(actual_demand,r['recommended']['demand'])
    same(incremental_audit,r['recommended']['reviewAudit'])
    rs=HoldSearch(released,allocate_gates=False)
    cumulative_audit=audit(rs,t)
    def warnings(schedule):
        return {(q['id'],f['id']):f for q in validate_operating_rules(schedule)['checks'] if q['severity']=='warning' for f in q['findings'] if not f.get('override')}
    before=warnings(released);after=warnings(t)
    write_json(ROOT/'config/optimizations/schedule_7_v1_2_4_accepted_round_4.json',c)
    write_json(ROOT/master,prior);write_json(ROOT/draft,t)
    r['status']='Recommended 125/157 turns approved and implemented in unpublished v1.2.4; 304 retained. Other candidates remain sensitivities.'
    r['acceptedOverlay']=master;r['recommended']['status']='approved and implemented in unpublished draft'
    write_json(ROOT/OUT,r)
    write_json(ROOT/'data/schedules/schedule_7_v1_2_4_draft/draft_report.json',{
        'status':'unpublished working draft','acceptedRoutes':[350,126,308,115,116,117,517,518,125,157],'retainedReviewedRoutes':[304],
        'baseCanonical':release,'baseSha256':sha256_file(ROOT/release),
        'acceptedOverlay':master,'acceptedOverlaySha256':sha256_file(ROOT/master),'canonicalSha256':sha256_file(ROOT/draft),
        'summary':{'flights':1168,'routes':181,'lines':20,'addedFlights':16,'retimedReleasedFlights':[1739,1811],'unchangedReleasedFlightClocks':1150},
        'checks':{'exactAcceptedReplay':'pass','releasedFlightIdentityPreservation':'pass','reviewedDemandAndAuditReproduction':'pass',
                  'latestReleasedRegression':'49 checks passed against v1.2.3'},
        'validation':v,'newWarningFindings':[{'check':k[0],**f} for k,f in after.items() if k not in before],
        'maintenance':{line:maintenance(t,line) for line in ('AA','AD','AE','AG')},
        'connectionTradeoff':cumulative_audit,'round4IncrementalTradeoff':incremental_audit,
        'round4Utilization':r['recommended']['utilization'],'publication':'Reserved to user decision'})
    print('ACCEPTED round 4: 1168 flights; zero blocking findings; only Flight 1811 newly retimed; unpublished',flush=True)

if __name__=='__main__':main()
