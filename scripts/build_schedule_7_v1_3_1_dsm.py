"""Reproduce the accepted DSM additions on the SHA-pinned round-3 draft."""
from pathlib import Path
import hashlib,json,sys,subprocess
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.timetable import export_timetable
def write(path,value):
 temp=path.with_name(path.name+'.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(path)
subprocess.run([sys.executable,str(ROOT/'scripts/build_schedule_7_v1_3_1_draft.py'),'--round-3'],check=True,capture_output=True,text=True)
directory=ROOT/'data/schedules/schedule_7_v1_3_1_draft';source=directory/'canonical_schedule.json';raw=source.read_bytes();base=json.loads(raw)
configpath=ROOT/'config/optimizations/schedule_7_v1_3_1_round_4.json';config=json.loads(configpath.read_text())
assert hashlib.sha256(raw).hexdigest()==config['baseSchedule']['sha256']
checkpoint=ROOT/'outputs/schedule_7_v1_3_1_dsm/base_round_3_canonical.json';checkpoint.parent.mkdir(parents=True,exist_ok=True);checkpoint.write_bytes(raw)
draft=apply_optimization_overlay(base,config)
draft['provenance']['workingDraft']['draftOverlays'].append({'path':configpath.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(configpath.read_bytes()).hexdigest()})
before={l['id']:l for l in base['legs']};after={l['id']:l for l in draft['legs']}
assert len(after)==1214 and before.keys()<=after.keys()
new=[l for l in draft['legs'] if l['id'] not in before];assert [l['flight']for l in new]==[2215,2216]
assert [(l['origin'],l['destination'],l['departure'],l['arrival'])for l in new]==[('MCI','DSM','14:00','14:50'),('DSM','MCI','15:35','16:25')]
changed={r['legId']for r in config['retimeLegs']}
assert {before[x]['flight']for x in changed}=={1209,1210}
for identifier,l in before.items():
 permitted={'departure','arrival','departureMinute','arrivalMinute'}if identifier in changed else set()
 if l['route']==154:permitted.add('sequenceWithinRoute')
 assert all(after[identifier][k]==v for k,v in l.items()if k not in permitted)
assert draft['cities']==base['cities'] and draft['hubBanks']==base['hubBanks'] and draft['operatingPolicy']==base['operatingPolicy'] and draft['schedule']==base['schedule']
structural=validate_schedule(draft);operating=validate_operating_rules(draft);overnight=validate_overnight_turns(draft);plan=reconstruct_planning_snapshot(draft,demand_data_version='bts-db1c-6mo-jul2025-apr2026-v7');planning=validate_planning_snapshot(plan,draft);gates=export_gate_schedule(draft)
assert structural['status']=='pass' and operating['summary']['effectiveErrorFindings']==0 and overnight['status']=='pass' and planning['status']=='pass'
assert not any(c['hardStop'] and c['status']=='fail'for c in operating['checks'])
stands=[s for c in gates['cities']for s in c['claims']if s['rowType']=='stand']
summary=json.loads((directory/'draft_report.json').read_text());summary.update({'flights':1214,'originalFlightClocksPreserved':1177,'originalFlightClocksChanged':15,'newFlights':summary['newFlights']+new,'newBlockMinutes':2178,'operating':operating['summary'],'standClaims':len(stands),'standMinutes':sum(s['end']-s['start']for s in stands),'standChangeSinceRound2':{'claims':len(stands)-16,'minutes':sum(s['end']-s['start']for s in stands)-3595},'dsmOptimization':config['acceptedDsmOptimization']})
metrics=next(c for c in operating['checks']if c['id']=='fleet_capacity')['metrics'];assert summary['fleetUsage']=={k:metrics[k]for k in ['MAX9','CRJ900','CRJ700','CRJ200']}
for name,value in {'canonical_schedule.json':draft,'validation_report.json':structural,'operating_validation_report.json':operating,'overnight_turn_validation.json':overnight,'planning_snapshot.json':plan,'planning_validation_report.json':planning,'gates.json':gates,'timetable.json':export_timetable(draft),'draft_report.json':summary}.items():write(directory/name,value)
print(json.dumps({k:v for k,v in summary.items()if k!='newFlights'}))
