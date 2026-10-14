"""Reproduce the unpublished maintenance repair against pinned released v1.3.1."""
from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.timetable import export_timetable
config_path=ROOT/'config/optimizations/schedule_7_v1_3_2_round_1.json';cfg=json.loads(config_path.read_text());source=ROOT/cfg['baseSchedule']['canonical']
assert hashlib.sha256(source.read_bytes()).hexdigest()==cfg['baseSchedule']['sha256'];base=json.loads(source.read_text());before=validate_operating_rules(base)
errors=next(x for x in before['checks']if x['id']=='rolling_ron_window');assert {x['id']for x in errors['findings']}=={'AC','AO','AQ'} and before['summary']['effectiveErrorFindings']==3
c=apply_optimization_overlay(base,cfg);c['provenance']['workingDraft']={'baseCommit':cfg['baseSchedule']['commit'],'baseCanonicalSha256':cfg['baseSchedule']['sha256'],'draftOverlays':[{'path':config_path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(config_path.read_bytes()).hexdigest()}],'publication':'Not authorized; app default remains v1.3.1'}
old={l['id']:l for l in base['legs']};new={l['id']:l for l in c['legs']};assert old.keys()==new.keys() and len(new)==1214
assert c['cities']==base['cities'] and c['hubBanks']==base['hubBanks'] and c['operatingPolicy']==base['operatingPolicy'] and c['schedule']['fleetCounts']==base['schedule']['fleetCounts']
changed=[]
for identifier,l in old.items():
 current=new[identifier];assert all(current[k]==l[k]for k in ['flight','fleet','pairing','origin','destination'])
 if (l['departureMinute'],l['arrivalMinute'])!=(current['departureMinute'],current['arrivalMinute']):changed.append(l['flight'])
assert sorted(changed)==[1817,1904]
structure=validate_schedule(c);operating=validate_operating_rules(c);overnight=validate_overnight_turns(c);plan=reconstruct_planning_snapshot(c,demand_data_version='bts-db1c-6mo-jul2025-apr2026-v7');planning=validate_planning_snapshot(plan,c);gates=export_gate_schedule(c)
assert structure['status']==overnight['status']==planning['status']=='pass' and operating['summary']['effectiveErrorFindings']==0
checks={x['id']:x for x in operating['checks']};assert not checks['line_route_count']['findings'];assert [x['id']for x in checks['rolling_ron_grace']['findings']]==['AM']
assert not any(l['line']in{'AO','AQ'}for l in c['legs'])
fleet=checks['fleet_capacity']['metrics'];assert {k:fleet[k]for k in c['schedule']['fleetCounts']}=={'MAX9':{'used':24,'capacity':35},'CRJ900':{'used':28,'capacity':45},'CRJ700':{'used':56,'capacity':65},'CRJ200':{'used':76,'capacity':80}}
stands=[x for city in gates['cities']for x in city['claims']if x['rowType']=='stand']
report={'status':'draft; not published','flights':1214,'routes':184,'lines':len({l['line']for l in c['legs']}),'retimedFlights':sorted(changed),'newFlights':0,'operating':operating['summary'],'beforeMaintenanceFindings':errors['findings'],'standingGrace':checks['rolling_ron_grace']['findings'],'lineCounts':{line:len({l['day']for l in c['legs']if l['line']==line})for line in sorted({l['line']for l in c['legs']})},'standClaims':len(stands),'standMinutes':sum(x['end']-x['start']for x in stands),'fleetUse':{k:fleet[k]for k in c['schedule']['fleetCounts']}}
out=ROOT/'data/schedules/schedule_7_v1_3_2_draft';out.mkdir(parents=True,exist_ok=True)
for name,x in {'canonical_schedule.json':c,'validation_report.json':structure,'operating_validation_report.json':operating,'overnight_turn_validation.json':overnight,'planning_snapshot.json':plan,'planning_validation_report.json':planning,'gates.json':gates,'timetable.json':export_timetable(c),'draft_report.json':report}.items():(out/name).write_text(json.dumps(x,indent=2)+'\n')
print(json.dumps(report))
