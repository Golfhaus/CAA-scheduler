"""Reproduce the unpublished RFD/JAX v1.3.1 draft from SHA-pinned v1.3.0."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.timetable import export_timetable
HISTORICAL='--round-1' in sys.argv
CONFIG=ROOT/('config/optimizations/schedule_7_v1_3_1_round_1.json' if HISTORICAL else 'config/optimizations/schedule_7_v1_3_1_round_2.json')
expected_flights=[2195,2196,2197,2198] if HISTORICAL else [2195,2196,2197,2198,2199,2200]
expected_block=544 if HISTORICAL else 692
expected_stand_minutes=3903 if HISTORICAL else 3595
config=json.loads(CONFIG.read_text());source=ROOT/config['baseSchedule']['canonical']
if hashlib.sha256(source.read_bytes()).hexdigest()!=config['baseSchedule']['sha256']:
 raise ValueError('Stale v1.3.0 source canonical')
base=json.loads(source.read_text());draft=apply_optimization_overlay(base,config)
before={l['id']:l for l in base['legs']};after={l['id']:l for l in draft['legs']}
new=config['addRoutes'][0]['legs'];expected_new={l['id'] for l in new}
assert before.keys()<=after.keys() and after.keys()-before.keys()==expected_new
assert [after[l['id']]['flight'] for l in new]==expected_flights
assert len(after)==1192+len(expected_flights)
# The rotation rebalance is not a flight retime or an aircraft-type swap.
changed_routes={r['sourceRoute']:r for r in config['routeReassignments']}
for identifier,old in before.items():
 current=after[identifier]
 assert all(current[k]==v for k,v in old.items() if k not in {'line','day'})
 expected=changed_routes.get(old['route'],{'line':old['line'],'day':old['day']})
 assert current['line']==expected['line'] and current['day']==expected['day']
assert draft['schedule']['fleetCounts']==base['schedule']['fleetCounts']
assert draft['cities']==base['cities'] and draft['hubBanks']==base['hubBanks']
assert draft['bankAssignments']==base['bankAssignments']+config['bankAssignmentsToAdd']
assert all(draft['operatingPolicy'][k]==v for k,v in base['operatingPolicy'].items() if k!='overrides')
assert draft['operatingPolicy']['overrides']==base['operatingPolicy']['overrides']+config['operatingOverrides']
for line in ['A','B']: assert sorted({l['day'] for l in draft['legs'] if l['line']==line})==list(range(1,13))
assert draft['schedule']['status']=='draft'
draft['provenance']['workingDraft']={'baseCommit':config['baseSchedule']['commit'],'baseCanonicalSha256':config['baseSchedule']['sha256'],'draftOverlays':[{'path':CONFIG.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(CONFIG.read_bytes()).hexdigest()}],'publication':'Not authorized; app default remains schedule_7_v1_3_0'}
structural=validate_schedule(draft);operating=validate_operating_rules(draft);overnight=validate_overnight_turns(draft)
plan=reconstruct_planning_snapshot(draft,demand_data_version='bts-db1c-6mo-jul2025-apr2026-v7');planning=validate_planning_snapshot(plan,draft);gates=export_gate_schedule(draft)
assert structural['summary']['failed']==0
assert operating['summary']['effectiveErrorFindings']==0
assert not any(x['hardStop'] and x['status']=='fail' for x in operating['checks'])
assert overnight['status']=='pass' and planning['status']=='pass'
stand=[s for c in gates['cities'] for s in c['claims'] if s['rowType']=='stand']
assert len(stand)==16 and sum(s['end']-s['start'] for s in stand)==expected_stand_minutes
fleet_check=next(x for x in operating['checks'] if x['id']=='fleet_capacity')
assert fleet_check['metrics']['MAX9']=={'used':24,'capacity':35}
new_legs=[after[l['id']] for l in new]
from caa_scheduler.bank_placement import TIMEZONE_OFFSETS
cities={c['code']:c for c in draft['cities']}
assert sum(l['arrivalMinute']-l['departureMinute']-(TIMEZONE_OFFSETS[cities[l['destination']]['timezone']]-TIMEZONE_OFFSETS[cities[l['origin']]['timezone']]) for l in new_legs)==expected_block
if HISTORICAL:
 out=ROOT/'outputs/schedule_7_v1_3_1_evening';out.mkdir(parents=True,exist_ok=True)
 payload=json.dumps(draft,indent=2)+'\n'
 assert hashlib.sha256(payload.encode()).hexdigest()=='448a9d9b15b871751d19371fad893d9313bf803f801775979aaecac985bbd23e'
 (out/'base_four_leg_canonical.json').write_text(payload)
 print('Reproduced pinned historical four-leg input; accepted draft unchanged')
 sys.exit(0)
out=ROOT/'data/schedules/schedule_7_v1_3_1_draft';out.mkdir(parents=True,exist_ok=True)
summary={'status':'draft; not published','baseScheduleId':base['schedule']['id'],'scheduleId':draft['schedule']['id'],'flights':len(draft['legs']),'routes':len({l['route'] for l in draft['legs']}),'lines':len({l['line'] for l in draft['legs']}),'originalFlightClocksPreserved':1192,'newFlights':new_legs,'newBlockMinutes':expected_block,'sameDayTurnsMinutes':[44,78,40,120,40],'fleetUsage':fleet_check['metrics'],'operating':operating['summary'],'standClaims':len(stand),'standMinutes':sum(s['end']-s['start'] for s in stand),'standChange':{'additionalClaims':2,'additionalMinutes':342,'station':'RFD'},'publication':'Not authorized; manifest and app default unchanged'}
artifacts={'canonical_schedule.json':draft,'validation_report.json':structural,'operating_validation_report.json':operating,'overnight_turn_validation.json':overnight,'planning_snapshot.json':plan,'planning_validation_report.json':planning,'gates.json':gates,'timetable.json':export_timetable(draft),'draft_report.json':summary}
for name,value in artifacts.items():
 temp=out/(name+'.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(out/name)
print(json.dumps(summary))
