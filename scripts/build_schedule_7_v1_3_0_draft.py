"""Replay the accepted unpublished v1.3.0 changes from the pinned release."""
from pathlib import Path
import copy,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.timetable import export_timetable
CONFIG=ROOT/'config/optimizations/schedule_7_v1_3_0_round_2.json'
config=json.loads(CONFIG.read_text());source=ROOT/config['baseSchedule']['canonical']
assert hashlib.sha256(source.read_bytes()).hexdigest()==config['baseSchedule']['sha256'],'Stale canonical input'
base=json.loads(source.read_text());draft=apply_optimization_overlay(base,config)
changed={x['legId'] for x in config['retimeLegs']}
before={l['id']:l for l in base['legs']};after={l['id']:l for l in draft['legs']}
assert before.keys()==after.keys()
assert len(changed)==7
assert {after[x]['flight'] for x in changed}=={1437,1036,2017,2019,1727,1723,1589}
for identifier,leg in after.items():
 if identifier not in changed:assert leg==before[identifier]
 else:
  assert all(leg[k]==before[identifier][k] for k in leg if k not in {'departure','arrival','departureMinute','arrivalMinute'})
assert draft['schedule']['fleetCounts']==base['schedule']['fleetCounts']
assert draft['hubBanks']==base['hubBanks'] and draft['operatingPolicy']==base['operatingPolicy']
assert draft['bankAssignments']==base['bankAssignments']
try:apply_optimization_overlay(draft,config)
except ValueError:pass
else:raise AssertionError('Overlay accepted a wrong base')
draft['provenance']['workingDraft']={'baseCommit':config['baseSchedule']['commit'],'baseCanonicalSha256':config['baseSchedule']['sha256'],'acceptedOverlays':[{'path':CONFIG.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(CONFIG.read_bytes()).hexdigest()}],'publication':'Not authorized; app remains on released v1.2.5'}
structural=validate_schedule(draft);operating=validate_operating_rules(draft);overnight=validate_overnight_turns(draft)
plan=reconstruct_planning_snapshot(draft,demand_data_version='bts-db1c-6mo-jul2025-apr2026-v7');planning=validate_planning_snapshot(plan,draft);gates=export_gate_schedule(draft)
assert structural['summary']['failed']==0
assert operating['summary']['effectiveErrorFindings']==0
assert overnight['status']=='pass' and planning['status']=='pass'
out=ROOT/'data/schedules/schedule_7_v1_3_0_draft';out.mkdir(parents=True,exist_ok=True)
artifacts={'canonical_schedule.json':draft,'validation_report.json':structural,'operating_validation_report.json':operating,'overnight_turn_validation.json':overnight,'planning_snapshot.json':plan,'planning_validation_report.json':planning,'gates.json':gates,'timetable.json':export_timetable(draft)}
for name,value in artifacts.items():
 temp=out/(name+'.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(out/name)
stand=[s for c in gates['cities'] for s in c['claims'] if s['rowType']=='stand']
print(json.dumps({'schedule':draft['schedule']['id'],'flights':len(draft['legs']),'operating':operating['summary'],'planning':planning['summary'],'standClaims':len(stand),'standMinutes':sum(s['end']-s['start']for s in stand)}))
