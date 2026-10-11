"""Replay accepted v1.2.5 rounds against pinned checkpoints; never publish."""
from copy import deepcopy
from pathlib import Path
import math
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from caa_scheduler.io import read_json,write_json,sha256_file
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.timetable import export_timetable
from analyze_schedule_7_v1_2_1_holds import HoldSearch
from analyze_schedule_7_v1_2_3_bwi import validate,demand
from analyze_schedule_7_v1_2_3_round_3 import audit
from analyze_schedule_7_v1_2_3_utilization import good
from analyze_schedule_7_v1_2_4 import cache_network
from analyze_schedule_7_v1_2_4_xna import maintenance
from analyze_schedule_7_v1_2_5_mci import b1_view,departure_demand
from review_crj200_line_alignment import routes,longest_gap
CONFIG='config/optimizations/schedule_7_v1_2_5.json'

def same(actual,expected,path='review'):
    if isinstance(actual,(int,float)) and isinstance(expected,(int,float)):
        assert math.isclose(actual,expected,rel_tol=1e-9,abs_tol=1e-8),path
    elif isinstance(actual,dict) and isinstance(expected,dict):
        assert actual.keys()==expected.keys(),path
        for key in actual:same(actual[key],expected[key],path+'.'+str(key))
    elif isinstance(actual,list) and isinstance(expected,list):
        assert len(actual)==len(expected),path
        for i,(a,b) in enumerate(zip(actual,expected)):same(a,b,path+'.'+str(i))
    else:assert actual==expected,(path,actual,expected)

def plain(schedule):
    result=deepcopy(schedule)
    for key in ('optimizationDraft','optimizationRelease'):result['provenance'].pop(key,None)
    return result

def main():
    cfg=read_json(ROOT/CONFIG);assert cfg['schedule']['status']=='draft' and cfg['acceptedRound']==2
    for pathkey,hashkey in [('baseCanonical','baseCanonicalSha256'),('acceptedOverlay','acceptedOverlaySha256'),('roundOneCheckpoint','roundOneCheckpointSha256'),('roundOneOverlay','roundOneOverlaySha256'),('latestRoundOverlay','latestRoundOverlaySha256')]:
        assert sha256_file(ROOT/cfg[pathkey])==cfg[hashkey],cfg[pathkey]
    base=read_json(ROOT/cfg['baseCanonical']);previous=read_json(ROOT/cfg['roundOneCheckpoint'])
    first=read_json(ROOT/cfg['roundOneOverlay']);latest=read_json(ROOT/cfg['latestRoundOverlay']);accepted=read_json(ROOT/cfg['acceptedOverlay'])
    for source in accepted['sourceProposals']:assert sha256_file(ROOT/source['path'])==source['sha256'],source['path']
    assert latest['baseSchedule']['sha256']==cfg['roundOneCheckpointSha256']
    assert plain(apply_optimization_overlay(base,first))==plain(previous)
    trial=apply_optimization_overlay(base,accepted);sequential=apply_optimization_overlay(previous,latest)
    assert plain(trial)==plain(sequential),'Cumulative replay differs from reviewed sequence'
    assert all(trial['schedule'][key]==value for key,value in cfg['schedule'].items())
    review=read_json(ROOT/latest['sourceProposals'][1]['path']);selected=next(q for q in review['candidates'] if q['id']==cfg['reviewedCandidate'])
    original_proposal=read_json(ROOT/latest['sourceProposals'][0]['path'])
    reviewed_trial=apply_optimization_overlay(previous,original_proposal);reviewed_trial['schedule']=deepcopy(trial['schedule']);reviewed_trial['gatePlan']['label']=trial['gatePlan']['label']
    assert plain(reviewed_trial)==plain(trial)
    old={leg['id']:leg for leg in previous['legs']};now={leg['id']:leg for leg in trial['legs']}
    timings={c['legId']:c for c in latest['retimeLegs']};inserted={l['id'] for l in latest['insertLegs']}
    assert set(now)-set(old)==inserted and set(old)<=set(now)
    for identifier,leg in old.items():
        expected=deepcopy(leg)
        if identifier in timings:expected.update(departureMinute=timings[identifier]['departureMinute'],arrivalMinute=timings[identifier]['arrivalMinute'],departure=now[identifier]['departure'],arrival=now[identifier]['arrival'])
        expected['sequenceWithinRoute']=now[identifier]['sequenceWithinRoute'];assert expected==now[identifier],identifier
    assert [now[l['id']]['flight'] for l in latest['insertLegs']]==list(range(2177,2185))
    assert len(trial['legs'])==1182 and trial['cities']==base['cities'] and trial['operatingPolicy']==base['operatingPolicy']
    assert trial['schedule']['fleetCounts']==base['schedule']['fleetCounts']
    rows=routes(trial);assert len(rows)==181 and len({l['line'] for l in trial['legs']})==19
    proof=[];targets=set(trial['operatingPolicy']['ronTargetCities']);hubs=set(trial['operatingPolicy']['hubs']+trial['operatingPolicy']['focusCities'])
    for line in ('AD','AE','AF','AI','AM','AN'):
        days=sorted((ls for ls in rows.values() if ls[0]['line']==line),key=lambda ls:ls[0]['day'])
        assert 9<=len(days)<=12 and {l['fleet'] for ls in days for l in ls}=={'CRJ200'}
        assert [ls[0]['day'] for ls in days]==list(range(1,len(days)+1))
        for current,following in zip(days,days[1:]+days[:1]):assert current[-1]['destination']==following[0]['origin']
        independent=[{'route':ls[0]['route'],'day':ls[0]['day'],'city':ls[-1]['destination']} for ls in days if ls[-1]['destination'] in hubs and ls[0]['route'] not in {125,136}]
        worst=longest_gap([ls[-1]['destination'] in targets and ls[0]['route'] not in {125,136} for ls in days])
        assert independent and worst<=trial['operatingPolicy']['rollingRonWindowDays']
        proof.append({'line':line,'fleet':'CRJ200','routes':len(days),'routeRange':[days[0][0]['route'],days[-1][0]['route']],'independentHubOrFocusRons':independent,'maximumNonMxRunExcluding125And136':worst})
    print('Pinned replay, preserved flights, fixed inventory and independent maintenance pass',flush=True)
    search=HoldSearch(previous);cache_network(search)
    validation,_=validate(search,latest);assert good(validation),validation
    compact={k:v for k,v in validation.items() if k!='affectedStations'};same(compact,selected['validation'])
    actual=demand(search,trial,inserted)
    for flight in actual['flights']:
        refs=flight.pop('connectingFlights');flight.update(connectingFlightCount=len(refs),connectingFlightNumbers=[l['flight'] for l in refs]);flight['topMarkets']=flight['topMarkets'][:5]
    same(actual,selected['demand']);delta_audit=audit(search,trial);same(delta_audit,selected['connectionAudit'])
    options=search.screen.enumerate(trial['legs']);loads,records=search.screen.allocate(options)
    changed=[]
    for change in latest['retimeLegs']:
        identifier=change['legId'];before={tuple(r['legs']) for r in search.screen.connections[identifier]};after={tuple(r['legs']) for r in records[identifier]}
        changed.append({'flight':old[identifier]['flight'],'lostConnectingChoices':len(before-after),'addedConnectingChoices':len(after-before),'oldOpportunity':sum(search.screen.loads[identifier].values()),'newOpportunity':sum(loads[identifier].values())})
    same(changed,selected['changedFlightConnections']);same(departure_demand(trial,loads,records),selected['b1DepartureDemand']);same(b1_view(trial),selected['b1'])
    for line,expected in selected['maintenance'].items():
        detail=maintenance(trial,line);detail.pop('longestRun',None);same(detail,expected)
    print('Reviewed MCI demand, B1 feed, retiming choices and network tradeoffs reproduced',flush=True)
    released_search=HoldSearch(base,allocate_gates=False);cache_network(released_search);cumulative_audit=audit(released_search,trial)
    manifest_sha=sha256_file(ROOT/'web/schedules.json')
    trial['provenance']['optimizationDraft']={'configuration':CONFIG,'configurationSha256':sha256_file(ROOT/CONFIG),'baseCanonical':cfg['baseCanonical'],'baseCanonicalSha256':cfg['baseCanonicalSha256'],'acceptedOverlay':cfg['acceptedOverlay'],'acceptedOverlaySha256':cfg['acceptedOverlaySha256'],'acceptedRound':2,'status':'draft; unpublished','publication':'Reserved to user decision','baseRelease':trial['provenance'].pop('optimizationRelease')}
    op=validate_operating_rules(trial);snapshot=reconstruct_planning_snapshot(trial)
    artifacts={'canonical_schedule.json':trial,'validation_report.json':validate_schedule(trial),'operating_validation_report.json':op,'overnight_turn_validation.json':validate_overnight_turns(trial),'planning_snapshot.json':snapshot,'planning_validation_report.json':validate_planning_snapshot(snapshot,trial),'gates.json':export_gate_schedule(trial),'timetable.json':export_timetable(trial),'connection_audit.json':cumulative_audit}
    output=ROOT/cfg['outputDirectory']
    for filename,artifact in artifacts.items():write_json(output/filename,artifact,indent=1 if filename in {'gates.json','timetable.json'} else 2)
    retimed=sorted(next(l['flight'] for l in base['legs'] if l['id']==c['legId']) for c in accepted['retimeLegs'])
    prior_report=read_json(ROOT/Path(cfg['roundOneCheckpoint']).parent/'draft_report.json')
    report={'status':'validated unpublished v1.2.5 draft','version':'1.2.5','acceptedRound':2,'acceptedOverlay':cfg['acceptedOverlay'],'acceptedOverlaySha256':cfg['acceptedOverlaySha256'],'baseCanonical':cfg['baseCanonical'],'baseCanonicalSha256':cfg['baseCanonicalSha256'],'canonicalSha256':sha256_file(output/'canonical_schedule.json'),'approval':accepted['approval'],'summary':{'flights':1182,'routes':181,'lines':19,'addedFlights':12,'addedFlightNumbers':list(range(2173,2185)),'retimedReleasedFlights':retimed,'unchangedReleasedFlightClocks':1170-len(retimed),'selectedAircraftDays':66,'fleetInventoryChanged':False,'effectiveOperatingErrors':validation['operatingErrors'],'operatingWarnings':validation['operatingWarnings'],'standClaims':validation['standClaims'],'standMinutes':validation['standMinutes']},'validation':compact,'lineProof':proof,'routeMapping':accepted['routeReassignments'],'demandModel':review['model'],'addedFlightDemand':{'round1':prior_report['addedFlightDemand'],'round2':actual},'changedFlightConnections':changed,'connectionTradeoff':cumulative_audit,'latestRoundConnectionTradeoff':delta_audit,'b1':b1_view(trial),'b1DepartureDemand':departure_demand(trial,loads,records),'hubBankChanges':accepted['hubBankChanges'],'checks':{'shaPinnedSourceReplay':'pass','cumulativeEqualsSequential':'pass','reviewReproduction':'pass','originalFlightPreservationAndApprovedRetimings':'pass','independentMaintenanceWithout125And136':'pass','noNewOperatingExceptions':'pass','appManifestUnchanged':'pass'},'publication':'Unpublished; main branch and app default remain released v1.2.4','limitations':['Demand is a seat-uncapped relative-choice opportunity model, not a passenger forecast.','SGF feeder has exactly 30 minutes to the 05:50 departures.','Aircraft overnight feasibility does not establish crew duty/rest.']}
    write_json(output/'draft_report.json',report);assert sha256_file(ROOT/'web/schedules.json')==manifest_sha
    print(report['summary']);print('SAVED: v1.2.5 draft only; no app publication')
if __name__=='__main__':main()
