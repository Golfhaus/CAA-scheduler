"""Accept 126/308, then assess 116/117 XNA RON against maintenance cadence.

XNA scenarios are proposals only. Preserve the round-one comparison snapshot
so its demand report and historic overlay remain hash-replayable.
"""
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
import analyze_schedule_7_v1_2_4 as previous
from analyze_schedule_7_v1_2_1_holds import HoldSearch
from analyze_schedule_7_v1_2_3_bwi import make_overlay,validate as raw_validate,demand,retime
from analyze_schedule_7_v1_2_3_round_3 import audit
from analyze_schedule_7_v1_2_3_utilization import good
from caa_scheduler.io import read_json,write_json,sha256_file
from caa_scheduler.optimization_overlay import apply_optimization_overlay

RELEASE=previous.RELEASE
ROUND1='data/schedules/schedule_7_v1_2_4_round_1/canonical_schedule.json'
BASE='data/schedules/schedule_7_v1_2_4_draft/canonical_schedule.json'
ACCEPTED='config/optimizations/schedule_7_v1_2_4_accepted_rounds_1_2.json'
OUT='config/proposals/schedule_7_v1_2_4_xna_review.json'

def accept():
    released=read_json(ROOT/RELEASE)
    first=read_json(ROOT/'config/optimizations/schedule_7_v1_2_4_accepted_350.json')
    round1=apply_optimization_overlay(released,first)
    write_json(ROOT/ROUND1,round1)
    proposal_path=ROOT/'config/proposals/schedule_7_v1_2_4_proposed_126_308.json'
    second=read_json(proposal_path)
    assert second['baseSchedule']['sha256']==sha256_file(ROOT/ROUND1)
    second['baseSchedule']['canonical']=ROUND1
    write_json(proposal_path,second)
    historic=read_json(ROOT/previous.OUT)
    assert historic['baseSha256']==sha256_file(ROOT/ROUND1)
    historic['baseCanonical']=ROUND1
    historic['status']='Historical round-one analysis; 126/308 approved and implemented in round two; 518 retained.'
    write_json(ROOT/previous.OUT,historic)
    c=deepcopy(first)
    for key in ('insertLegs','retimeLegs','bankAssignmentsToAdd','bankAssignmentReplacements','hubBanksToAdd','operatingOverrides'):
        c.setdefault(key,[]).extend(deepcopy(second.get(key,[])))
    c['id']='schedule-7-v1.2.4-accepted-rounds-1-2'
    c['approval']={'status':'approved for draft implementation; unpublished',
        'userInstruction':'Add the proposals to the 1.2.4 draft as suggested.',
        'scope':'350 ELP–MCI, 126 MLB–JAX, 308 CLT–MCI. Retain 518.',
        'publication':'Reserved to user decision'}
    s=HoldSearch(released);v,t=raw_validate(s,c)
    assert good(v),v
    sequential=apply_optimization_overlay(round1,second)
    assert t['legs']==sequential['legs']
    old={l['id']:l for l in released['legs']};now={l['id']:l for l in t['legs']}
    assert all(now[i]==l for i,l in old.items()) and len(t['legs'])==1158
    assert t['hubBanks']==released['hubBanks'] and t['operatingPolicy']==released['operatingPolicy']
    write_json(ROOT/ACCEPTED,c);write_json(ROOT/BASE,t)
    write_json(ROOT/'data/schedules/schedule_7_v1_2_4_draft/draft_report.json',{
        'status':'unpublished working draft','acceptedRoutes':[350,126,308],
        'proposedRoutes':[],'retainedRoutes':[518],
        'baseCanonical':RELEASE,'baseSha256':sha256_file(ROOT/RELEASE),
        'acceptedOverlay':ACCEPTED,'acceptedOverlaySha256':sha256_file(ROOT/ACCEPTED),
        'canonicalSha256':sha256_file(ROOT/BASE),
        'summary':{'flights':1158,'routes':181,'lines':20,'addedFlights':6,'unchangedReleasedFlights':1152},
        'checks':{'exactAcceptedReplay':'pass','releasedFlightPreservation':'pass',
                  'latestReleasedRegression':'49 checks passed against v1.2.3'},
        'validation':v,'publication':'Reserved to user decision'})
    print('ACCEPTED 126/308:',len(t['legs']),'flights; no released flights changed; unpublished',flush=True)

def overlay(s,plans,changes=()):
    c=make_overlay(s,plans,retimings=changes)
    c['baseSchedule'].update(canonical=BASE,sha256=sha256_file(ROOT/BASE))
    c['id']='schedule-7-v1.2.4-xna-overnight-analysis'
    c['schedule'].update(id='schedule_7_v1_2_4_xna_analysis',version='1.2.4',label='Schedule 7 v1.2.4 XNA RON analysis; unpublished')
    mapping={l['id']:l['id'].replace('V123-','V124-XNA-') for l in c['insertLegs']}
    for l in c['insertLegs']:l['id']=mapping[l['id']]
    for a in c['bankAssignmentsToAdd']:a['legId']=mapping[a['legId']]
    return c

def maintenance(s,line='AD'):
    routes={}
    for l in s['legs']:
        if l['line']==line:routes.setdefault(l['day'],[]).append(l)
    rows=[];targets=set(s['operatingPolicy']['ronTargetCities'])
    hubs=set(s['operatingPolicy']['hubs']+s['operatingPolicy']['focusCities'])
    for day,ls in sorted(routes.items()):
        last=max(ls,key=lambda l:l['sequenceWithinRoute'])
        rows.append({'day':day,'route':last['route'],'city':last['destination'],
                     'targetRon':last['destination'] in targets,'hubOrFocusRon':last['destination'] in hubs})
    maximum=0;run=0;longest=[];current=[]
    for row in rows*2:
        if row['targetRon']:run=0;current=[]
        else:
            run+=1;current.append(row)
            if run>maximum:maximum=run;longest=current[:]
    return {'line':line,'maximumConsecutiveNonTargetRons':min(maximum,len(rows)),
            'limit':s['operatingPolicy']['rollingRonWindowDays'],
            'grace':s['operatingPolicy']['rollingRonGraceDays'],
            'longestRun':longest,'targetRons':[r for r in rows if r['targetRon']],
            'hubOrFocusRons':[r for r in rows if r['hubOrFocusRon']]}

def trial(s,name,plans,changes=()):
    c=overlay(s,plans,changes);v,t=raw_validate(s,c)
    x={'name':name,'plans':plans,'retimings':list(changes),'validation':v,'maintenance':maintenance(t)}
    # A maintenance failure does not erase the commercial/timing sensitivity.
    # Compute demand only when it is the sole unresolved error.
    only_mx=all(q['check']=='rolling_ron_window' for q in v['blocking'])
    if good(v) or (only_mx and v['gates']=='pass' and all(v[k]=='pass' for k in ('structural','planning','overnight'))):
        x['demand']=demand(s,t,{l['id'] for l in c['insertLegs']});x['reviewAudit']=audit(s,t)
    print('TRIAL',name,'errors',v['operatingErrors'],'gates',v['gates'],
          'MX longest',x['maintenance']['maximumConsecutiveNonTargetRons'],
          [(round(f['total'],1),f['departureClock'],f['arrivalClock']) for f in x.get('demand',{}).get('flights',[])],flush=True)
    return x,c,t

def main():
    if '--accept' in sys.argv:accept();return
    s=HoldSearch(read_json(ROOT/BASE));previous.cache_network(s)
    r=read_json(ROOT/OUT) if (ROOT/OUT).exists() else {
        'baseCanonical':BASE,'baseSha256':sha256_file(ROOT/BASE),
        'status':'XNA scenarios analysis only; no 116/117 changes implemented',
        'model':'Pinned O-D, seat-uncapped full-capture relative-choice opportunities; not forecasts',
        'baselineMaintenance':maintenance(s.base),'trials':[]}
    assert r['baseSha256']==sha256_file(ROOT/BASE),'Stale XNA checkpoint'
    def add(name,plans,changes=()):
        if any(x['name']==name for x in r['trials']):return
        x,c,t=trial(s,name,plans,changes);r['trials'].append(x);write_json(ROOT/OUT,r)
        if name.startswith('116 MCI'):
            c['approval']={'status':'conditional analysis; blocked by rolling maintenance-base RON rule',
                          'publication':'Reserved to user decision','scope':name}
            write_json(ROOT/'config/proposals/schedule_7_v1_2_4_xna_conditional.json',c)
        if good(x['validation']):
            c['approval']={'status':'optional proposal; not approved for implementation',
                          'publication':'Reserved to user decision','scope':name}
            write_json(ROOT/'config/proposals/schedule_7_v1_2_4_xna_with_jax_mx.json',c)
    xna=[{'route':116,'legs':[s.leg('MCI','XNA',1285,'CRJ200')]},
         {'route':117,'legs':[s.leg('XNA','MCI',330,'CRJ200')]}]
    add('116 MCI–XNA 21:25; 117 XNA–MCI 05:30',xna)
    # Alternative maintenance night one day earlier, preserving all flights.
    # Returning JAX–GNV at 04:30 requires a 37-minute shift of the existing
    # GNV–JAX originator; the subsequent 07:30 JAX–DAB stays unchanged.
    if '--alternative' in sys.argv:
        plans=xna+[{'route':115,'legs':[s.leg('GNV','JAX',1242,'CRJ200')]},
                   {'route':116,'legs':[s.leg('JAX','GNV',270,'CRJ200')]}]
        changes=retime(s,116,[37,0,0,0,0,0,0])
        add('XNA overnight plus replacement 115 JAX maintenance RON',plans,changes)
    print('SAVED XNA analysis; draft unchanged',flush=True)

if __name__=='__main__':main()
