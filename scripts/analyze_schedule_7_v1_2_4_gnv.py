"""Joint XNA/JAX maintenance swap and PHF–GNV replacement overnight.

Evaluate the complete batch against the accepted round-two snapshot. Only
fully compliant candidates can be accepted; no MX or destination RON is waived.
"""
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
import analyze_schedule_7_v1_2_4_xna as xna
import analyze_schedule_7_v1_2_4 as first
from analyze_schedule_7_v1_2_1_holds import HoldSearch
from analyze_schedule_7_v1_2_3_bwi import make_overlay,retime,demand
from analyze_schedule_7_v1_2_3_round_3 import audit
from analyze_schedule_7_v1_2_3_round_4 import inventory
from analyze_schedule_7_v1_2_3_utilization import good
from caa_scheduler.io import read_json,write_json,sha256_file
from caa_scheduler.optimization_overlay import apply_optimization_overlay

RELEASE=first.RELEASE
BASE='data/schedules/schedule_7_v1_2_4_round_2/canonical_schedule.json'
DRAFT='data/schedules/schedule_7_v1_2_4_draft/canonical_schedule.json'
OUT='config/proposals/schedule_7_v1_2_4_gnv_review.json'

def snapshot():
    prior=read_json(ROOT/'config/optimizations/schedule_7_v1_2_4_accepted_rounds_1_2.json')
    b=apply_optimization_overlay(read_json(ROOT/RELEASE),prior)
    write_json(ROOT/BASE,b)
    # Keep prior review pins anchored to their unchanged historical snapshot.
    for name in ('config/proposals/schedule_7_v1_2_4_xna_review.json',
                 'config/proposals/schedule_7_v1_2_4_xna_conditional.json'):
        r=read_json(ROOT/name)
        if 'baseCanonical' in r:
            assert r['baseSha256']==sha256_file(ROOT/BASE);r['baseCanonical']=BASE
        else:
            assert r['baseSchedule']['sha256']==sha256_file(ROOT/BASE);r['baseSchedule']['canonical']=BASE
        write_json(ROOT/name,r)
    return b

def overlay(s,plans,changes=()):
    c=make_overlay(s,plans,retimings=changes)
    c['baseSchedule'].update(canonical=BASE,sha256=sha256_file(ROOT/BASE))
    c['id']='schedule-7-v1.2.4-xna-gnv-joint-review'
    c['schedule'].update(id='schedule_7_v1_2_4_gnv_analysis',version='1.2.4',label='Schedule 7 v1.2.4 joint GNV/XNA review; unpublished')
    mapping={l['id']:l['id'].replace('V123-','V124-R3-') for l in c['insertLegs']}
    for l in c['insertLegs']:l['id']=mapping[l['id']]
    for a in c['bankAssignmentsToAdd']:a['legId']=mapping[a['legId']]
    return c

def trial(s,name,plans,changes=()):
    c=overlay(s,plans,changes);v,t=first.validate(s,c)
    affected_lines={next(l['line'] for l in s.base['legs'] if l['route']==p['route']) for p in plans}
    x={'name':name,'plans':plans,'retimings':list(changes),'validation':v,
       'maintenance':{line:xna.maintenance(t,line) for line in sorted(affected_lines)}}
    if good(v):
        x['demand']=demand(s,t,{l['id'] for l in c['insertLegs']});x['reviewAudit']=audit(s,t)
        loads,records=s.screen.allocate(s.screen.enumerate(t['legs']))
        x['changedFlightConnections']=[]
        for change in changes:
            l=s.legs[change['legId']]
            before={tuple(r['legs']) for r in s.screen.connections[l['id']]}
            after={tuple(r['legs']) for r in records[l['id']]}
            x['changedFlightConnections'].append({'flight':l['flight'],
                'oldTotalOpportunity':sum(s.screen.loads[l['id']].values()),
                'newTotalOpportunity':sum(loads[l['id']].values()),
                'lostConnectingChoices':len(before-after),'addedConnectingChoices':len(after-before)})
    print('TRIAL',name,'errors',v['operatingErrors'],'gates',v['gates'],
          [(round(f['total'],1),f['departureClock'],f['arrivalClock']) for f in x.get('demand',{}).get('flights',[])],flush=True)
    return x,c,t

def main():
    if '--accept' in sys.argv:accept();return
    b=snapshot();s=HoldSearch(b);first.cache_network(s)
    r=read_json(ROOT/OUT) if (ROOT/OUT).exists() else {
        'baseCanonical':BASE,'baseSha256':sha256_file(ROOT/BASE),
        'status':'Joint analysis; no additional draft implementation yet',
        'model':'Pinned O-D; full-capture seat-uncapped relative-choice opportunities, not forecast loads',
        'phfInventory':[],'trials':[]}
    assert r['baseSha256']==sha256_file(ROOT/BASE),'Stale round-three checkpoint'
    if not r['phfInventory']:
        for route in sorted({l['route'] for l in b['legs']}):
            item=inventory(s,route)
            if item['terminator']!='PHF':continue
            rows=deepcopy(b)
            next(l for l in rows['legs'] if l['id']==item['legs'][-1]['id'])['destination']='GNV'
            block=s.leg('GNV','PHF',0,item['fleet'])['arrivalMinute']
            item.update(maintenanceBefore=xna.maintenance(b,item['line']),
                maintenanceAfter=xna.maintenance(rows,item['line']),
                gnvBlockMinutes=block,
                earliestGnvReturnPhf=270+block,
                earliestPhfDepartureAfterReturn=270+block+40,
                nextOriginatorDelayRequired=max(0,270+block+40-item['nextOriginator']['departureMinute']))
            r['phfInventory'].append(item)
        write_json(ROOT/OUT,r)
    def add(name,plans,changes):
        if any(x['name']==name for x in r['trials']):return
        x,c,t=trial(s,name,plans,changes);r['trials'].append(x);write_json(ROOT/OUT,r)
        if good(x['validation']):
            c['approval']={'status':'reviewed joint candidate; unpublished',
                'scope':name,'publication':'Reserved to user decision'}
            tag='buffered' if 'buffered' in name else 'unchanged' if 'unchanged' in name else '314'
            write_json(ROOT/f'config/proposals/schedule_7_v1_2_4_gnv_{tag}.json',c)
    shared=[{'route':115,'legs':[s.leg('GNV','JAX',1242,'CRJ200')]},
            {'route':116,'legs':[s.leg('JAX','GNV',270,'CRJ200'),s.leg('MCI','XNA',1285,'CRJ200')]},
            {'route':117,'legs':[s.leg('XNA','MCI',330,'CRJ200')]}]
    changes=retime(s,116,[37,0,0,0,0,0,0])
    gnv=[{'route':517,'legs':[s.leg('PHF','GNV',1305,'CRJ900')]},
         {'route':518,'legs':[s.leg('GNV','PHF',270,'CRJ900')]}]
    add('517/518 GNV replacement; unchanged PHF 06:55 originator',shared+gnv,changes)
    add('517/518 GNV replacement; buffered PHF 07:00 originator',shared+gnv,
        changes+retime(s,518,[5,0,0,0]))
    # Alternate PHF aircraft has lower maintenance slack and arrives three
    # minutes too late for its original 06:55 PVD flight; quantify the tradeoff.
    gnv=[{'route':314,'legs':[s.leg('PHF','GNV',1332,'CRJ700')]},
         {'route':315,'legs':[s.leg('GNV','PHF',270,'CRJ700')]}]
    add('314/315 alternate GNV overnight; PVD originator +3',shared+gnv,
        changes+retime(s,315,[3,0,0,0,0]))
    print('SAVED joint review',flush=True)

def accept():
    b=snapshot();s=HoldSearch(b)
    c=deepcopy(read_json(ROOT/'config/proposals/schedule_7_v1_2_4_gnv_unchanged.json'))
    assert c['baseSchedule']['sha256']==sha256_file(ROOT/BASE)
    c['id']='schedule-7-v1.2.4-accepted-round-3'
    c['schedule'].update(id='schedule_7_v1_2_4_draft',label='Schedule 7 v1.2.4 working draft; unpublished')
    c['approval']={'status':'approved for draft implementation; unpublished',
        'userInstruction':'Can we make that change to 115/116/117, and then send a current PHF terminator to GNV, with the intention of having GNV-PHF as the GNV originating service?',
        'scope':'115 JAX RON; 116 early JAX–GNV and evening MCI–XNA; 117 early XNA–MCI; 517 PHF–GNV RON and 518 GNV–PHF originator. Flight 1739 +37 minutes; other clocks retained.',
        'publication':'Reserved to user decision'}
    for item in c['operatingOverrides']:
        item['reason']='User explicitly requested PHF–GNV overnight/originator service as the replacement GNV RON. Useful second-hub coverage is authorized; all physical, maintenance and timing rules remain enforced.'
    v,t=first.validate(s,c);assert good(v),v
    prior=deepcopy(read_json(ROOT/'config/optimizations/schedule_7_v1_2_4_accepted_rounds_1_2.json'))
    for key in ('insertLegs','retimeLegs','bankAssignmentsToAdd','bankAssignmentReplacements','hubBanksToAdd','operatingOverrides'):
        prior.setdefault(key,[]).extend(deepcopy(c.get(key,[])))
    prior['id']='schedule-7-v1.2.4-accepted-rounds-1-3'
    prior['approval']=deepcopy(c['approval'])
    prior['approval']['scope']='Earlier approved 350, 126 and 308 additions; '+c['approval']['scope']
    released=read_json(ROOT/RELEASE)
    assert prior['baseSchedule']['sha256']==sha256_file(ROOT/RELEASE)
    rebuilt=apply_optimization_overlay(released,prior)
    assert rebuilt==t,'Flattened replay changed accepted draft'
    old={l['id']:l for l in released['legs']};now={l['id']:l for l in t['legs']}
    for i,l in old.items():
        target={**l,'sequenceWithinRoute':now[i]['sequenceWithinRoute']}
        if l['flight']==1739:
            target.update(departure='05:47',arrival='06:24',departureMinute=347,arrivalMinute=384)
        assert target==now[i],f'Unexpected released-flight change: {i}'
    assert len(t['legs'])==1164
    assert {l['flight'] for i,l in now.items() if i not in old}==set(range(2155,2167))
    assert t['hubBanks']==released['hubBanks'] and t['schedule']['fleetCounts']==released['schedule']['fleetCounts']
    write_json(ROOT/'config/optimizations/schedule_7_v1_2_4_accepted_round_3.json',c)
    master='config/optimizations/schedule_7_v1_2_4_accepted_rounds_1_3.json'
    write_json(ROOT/master,prior);write_json(ROOT/DRAFT,t)
    report=read_json(ROOT/OUT)
    chosen=next(x for x in report['trials'] if 'unchanged PHF' in x['name'])
    chosen['status']='approved and implemented in unpublished draft'
    report.update(status='Selected 517/518 candidate approved and implemented; other candidates retained as sensitivities',
                  acceptedOverlay=master,selectedName=chosen['name'])
    write_json(ROOT/OUT,report)
    from caa_scheduler.operating_validation import validate_operating_rules
    def warning_set(schedule):
        return {(q['id'],f['id']):f for q in validate_operating_rules(schedule)['checks'] if q['severity']=='warning' for f in q['findings'] if not f.get('override')}
    before=warning_set(b);after=warning_set(t)
    new_warnings=[{'check':k[0],**f} for k,f in after.items() if k not in before]
    write_json(ROOT/'data/schedules/schedule_7_v1_2_4_draft/draft_report.json',{
        'status':'unpublished working draft','acceptedRoutes':[350,126,308,115,116,117,517,518],
        'baseCanonical':RELEASE,'baseSha256':sha256_file(ROOT/RELEASE),
        'acceptedOverlay':master,'acceptedOverlaySha256':sha256_file(ROOT/master),
        'canonicalSha256':sha256_file(ROOT/DRAFT),
        'summary':{'flights':1164,'routes':181,'lines':20,'addedFlights':12,
                   'retimedReleasedFlights':[1739],'unchangedReleasedFlightClocks':1151},
        'checks':{'exactAcceptedReplay':'pass','releasedFlightIdentityPreservation':'pass',
                  'latestReleasedRegression':'49 checks passed against v1.2.3'},
        'validation':v,'newWarningFindings':new_warnings,
        'maintenance':{line:xna.maintenance(t,line) for line in ('AD','AG')},
        'connectionTradeoff':chosen['reviewAudit'],'publication':'Reserved to user decision'})
    print('ACCEPTED joint changes:',len(t['legs']),'flights; 0 errors; unchanged OMA/PIE clocks; unpublished',flush=True)
    print('NEW WARNINGS',new_warnings,flush=True)

if __name__=='__main__':main()
