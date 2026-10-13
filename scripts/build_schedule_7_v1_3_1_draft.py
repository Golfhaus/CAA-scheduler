"""Reproduce the unpublished v1.3.1 draft and pinned historical review inputs."""
from pathlib import Path
import hashlib,json,sys,subprocess
ROOT=Path(__file__).resolve().parents[1]
if not any(x in sys.argv for x in ['--round-1','--round-2','--round-3']) and (ROOT/'config/optimizations/schedule_7_v1_3_1_round_4.json').exists():
 subprocess.run([sys.executable,str(ROOT/'scripts/build_schedule_7_v1_3_1_dsm.py')],check=True)
 sys.exit(0)
sys.path.insert(0,str(ROOT/'src'))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.timetable import export_timetable
from caa_scheduler.bank_placement import TIMEZONE_OFFSETS,_block_minutes
ROUND=1 if '--round-1' in sys.argv else 2 if '--round-2' in sys.argv else 3
CONFIG=ROOT/f'config/optimizations/schedule_7_v1_3_1_round_{ROUND}.json'
config=json.loads(CONFIG.read_text());source=ROOT/config['baseSchedule']['canonical']
assert hashlib.sha256(source.read_bytes()).hexdigest()==config['baseSchedule']['sha256'],'Stale published source'
base=json.loads(source.read_text())
def construct(configuration,path):
 result=apply_optimization_overlay(base,configuration)
 result['provenance']['workingDraft']={'baseCommit':configuration['baseSchedule']['commit'],'baseCanonicalSha256':configuration['baseSchedule']['sha256'],'draftOverlays':[{'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}],'publication':'Not authorized; app default remains schedule_7_v1_3_0'}
 return result

def historical(round_number):
 path=ROOT/f'config/optimizations/schedule_7_v1_3_1_round_{round_number}.json'
 result=construct(json.loads(path.read_text()),path);payload=json.dumps(result,indent=2)+'\n'
 expected={1:'448a9d9b15b871751d19371fad893d9313bf803f801775979aaecac985bbd23e',2:'f0b475b7038c20a9e3bdd93110dfbc802ebe7726a12bcfba775a849bc9077546'}[round_number]
 assert hashlib.sha256(payload.encode()).hexdigest()==expected
 target=ROOT/('outputs/schedule_7_v1_3_1_evening/base_four_leg_canonical.json' if round_number==1 else 'outputs/schedule_7_v1_3_1_ne_service/base_round_2_canonical.json')
 target.parent.mkdir(parents=True,exist_ok=True);target.write_text(payload)
 return target

if ROUND<3:
 historical(ROUND);print(f'Reproduced pinned round {ROUND} input; accepted draft unchanged');sys.exit(0)
historical(2)
draft=construct(config,CONFIG)
before={l['id']:l for l in base['legs']};after={l['id']:l for l in draft['legs']}
new=[l for r in config['addRoutes'] for l in r['legs']]+config.get('insertLegs',[])
assert before.keys()<=after.keys() and after.keys()-before.keys()=={l['id'] for l in new}
assert [after[l['id']]['flight'] for l in new]==list(range(2195,2215))
assert len(after)==1212
retimes={r['legId']:r for r in config['retimeLegs']};moves={r['legId']:r for r in config['legReassignments']};route_changes={r['sourceRoute']:r for r in config['routeReassignments']}
assert len(retimes)==13
for identifier,old in before.items():
 current=after[identifier]
 assert all(current[k]==old[k] for k in ['id','flight','fleet','pairing','origin','destination'])
 expected=retimes.get(identifier,old)
 assert current['departureMinute']==expected['departureMinute'] and current['arrivalMinute']==expected['arrivalMinute']
 target=moves.get(identifier,{}).get('targetRoute',old['route']);assert current['route']==target
 identity=next(l for l in base['legs'] if l['route']==target)
 assignment=route_changes.get(target,identity)
 assert current['line']==assignment['line'] and current['day']==assignment['day']
assert draft['schedule']['fleetCounts']==base['schedule']['fleetCounts']
assert draft['cities']==base['cities'] and draft['hubBanks']==base['hubBanks']
expected_assignments=[dict(x) for x in base['bankAssignments']]
for change in config['bankAssignmentReplacements']:
 next(x for x in expected_assignments if x['legId']==change['legId'] and x['operation']==change['operation'])['bankId']=change['bankId']
assert draft['bankAssignments']==expected_assignments+config['bankAssignmentsToAdd']
assert all(draft['operatingPolicy'][k]==v for k,v in base['operatingPolicy'].items() if k!='overrides')
assert draft['operatingPolicy']['overrides']==base['operatingPolicy']['overrides']+config['operatingOverrides']
for line,count in [('A',12),('B',12),('AS',12),('AK',10)]:
 assert sorted({l['day'] for l in draft['legs'] if l['line']==line})==list(range(1,count+1))
assert draft['schedule']['status']=='draft'
structural=validate_schedule(draft);operating=validate_operating_rules(draft);overnight=validate_overnight_turns(draft)
plan=reconstruct_planning_snapshot(draft,demand_data_version='bts-db1c-6mo-jul2025-apr2026-v7');planning=validate_planning_snapshot(plan,draft);gates=export_gate_schedule(draft)
assert structural['summary']['failed']==0 and operating['summary']['effectiveErrorFindings']==0
assert not any(x['hardStop'] and x['status']=='fail' for x in operating['checks'])
assert overnight['status']=='pass' and planning['status']=='pass'
stand=[s for c in gates['cities'] for s in c['claims'] if s['rowType']=='stand']
assert len(stand)==16 and sum(s['end']-s['start'] for s in stand)==3595
fleet_metrics=next(x for x in operating['checks'] if x['id']=='fleet_capacity')['metrics']
fleet={k:fleet_metrics[k] for k in ['MAX9','CRJ900','CRJ700','CRJ200']}
assert fleet=={'MAX9':{'used':24,'capacity':35},'CRJ900':{'used':28,'capacity':45},'CRJ700':{'used':56,'capacity':65},'CRJ200':{'used':76,'capacity':80}}
cities={c['code']:c for c in draft['cities']}
profiles={p['fleet']:p for p in json.loads((ROOT/'config/policies/planning_rules_v7.json').read_text())['frequencyAllocation']['fleetProfiles']}
def block(l):
 return (l['arrivalMinute']-l['departureMinute'])%1440-(TIMEZONE_OFFSETS[cities[l['destination']]['timezone']]-TIMEZONE_OFFSETS[cities[l['origin']]['timezone']])
new_legs=[after[l['id']] for l in new]
for l in new_legs:assert block(l)==_block_minutes(l['origin'],l['destination'],profiles[l['fleet']],cities)
assert sum(block(l) for l in new_legs)==2078
route_block={r:sum(block(l) for l in new_legs if l['route']==r) for r in [724,355,356]}
assert route_block=={724:692,355:717,356:569}
out=ROOT/'data/schedules/schedule_7_v1_3_1_draft';out.mkdir(parents=True,exist_ok=True)
summary={'status':'draft; not published','baseScheduleId':base['schedule']['id'],'scheduleId':draft['schedule']['id'],'flights':len(draft['legs']),'routes':len({l['route'] for l in draft['legs']}),'lines':len({l['line'] for l in draft['legs']}),'originalFlightClocksPreserved':1192-len(retimes),'originalFlightClocksChanged':len(retimes),'newFlights':new_legs,'newBlockMinutes':2078,'newRouteBlockMinutes':route_block,'newNortheastRoundBlockMinutesIncludingBridges':1386,'fleetUsage':fleet,'operating':operating['summary'],'standClaims':len(stand),'standMinutes':3595,'standChangeSinceRound2':{'claims':0,'minutes':0},'publication':'Not authorized; manifest and app default unchanged'}
artifacts={'canonical_schedule.json':draft,'validation_report.json':structural,'operating_validation_report.json':operating,'overnight_turn_validation.json':overnight,'planning_snapshot.json':plan,'planning_validation_report.json':planning,'gates.json':gates,'timetable.json':export_timetable(draft),'draft_report.json':summary}
for name,value in artifacts.items():
 temp=out/(name+'.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(out/name)
print(json.dumps({k:v for k,v in summary.items() if k!='newFlights'}))
