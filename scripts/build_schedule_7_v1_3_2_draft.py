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
checkpoint=ROOT/'outputs/schedule_7_v1_3_2_maintenance/base_maintenance_canonical.json';checkpoint.parent.mkdir(parents=True,exist_ok=True);checkpoint.write_text(json.dumps(c,indent=2)+'\n')
if '--maintenance-only' in sys.argv:
 print('Rebuilt pinned maintenance checkpoint:',checkpoint);sys.exit(0)
round2_path=ROOT/'config/optimizations/schedule_7_v1_3_2_round_2.json'
if round2_path.exists():
 round2=json.loads(round2_path.read_text());assert hashlib.sha256(checkpoint.read_bytes()).hexdigest()==round2['baseSchedule']['sha256']
 maintenance=c;c=apply_optimization_overlay(c,round2)
 c['provenance']['workingDraft']['draftOverlays'].append({'path':round2_path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(round2_path.read_bytes()).hexdigest()})
 old={l['id']:l for l in maintenance['legs']};now={l['id']:l for l in c['legs']}
 assert {old[i]['flight']for i in old.keys()-now.keys()}=={1257,1258}
 added=[now[i]for i in now.keys()-old.keys()];assert {l['flight']for l in added}=={2217,2218}
 assert len(now)==1214 and {(l['origin'],l['destination'])for l in added}=={('SFB','RFD'),('RFD','SFB')}
 for i in old.keys()&now.keys():
  allowed={'departure','arrival','departureMinute','arrivalMinute'}if old[i]['flight']in{1256,1219}else set()
  if old[i]['route']==501:allowed.add('sequenceWithinRoute')
  assert all(now[i][k]==v for k,v in old[i].items()if k not in allowed)
 assert c['cities']==base['cities'] and c['hubBanks']==base['hubBanks'] and c['operatingPolicy']==base['operatingPolicy'] and c['schedule']==maintenance['schedule']
 structure=validate_schedule(c);operating=validate_operating_rules(c);overnight=validate_overnight_turns(c);plan=reconstruct_planning_snapshot(c,demand_data_version='bts-db1c-6mo-jul2025-apr2026-v7');planning=validate_planning_snapshot(plan,c);gates=export_gate_schedule(c)
 assert structure['status']==overnight['status']==planning['status']=='pass' and operating['summary']['effectiveErrorFindings']==0
 checks={x['id']:x for x in operating['checks']};assert [x['id']for x in checks['rolling_ron_grace']['findings']]==['AM']
 assert checks['fleet_capacity']['metrics']==fleet
 stands=[x for city in gates['cities']for x in city['claims']if x['rowType']=='stand'];assert (len(stands),sum(x['end']-x['start']for x in stands))==(15,3061)
 report.update({'retimedFlights':[1219,1256,1817,1904],'newFlights':2,'removedFlights':[1257,1258],'addedFlights':sorted(added,key=lambda l:l['flight']),'netFlightChange':0,'operating':operating['summary'],'acceptedR501':round2['acceptedR501']})
round2_checkpoint=ROOT/'outputs/schedule_7_v1_3_2_r175/base_round_2_canonical.json';round2_checkpoint.parent.mkdir(parents=True,exist_ok=True);round2_checkpoint.write_text(json.dumps(c,indent=2)+'\n')
if '--r501-only' in sys.argv:
 print('Rebuilt pinned R501 checkpoint:',round2_checkpoint);sys.exit(0)
round3_path=ROOT/'config/optimizations/schedule_7_v1_3_2_round_3.json'
if round3_path.exists():
 round3=json.loads(round3_path.read_text());assert hashlib.sha256(round2_checkpoint.read_bytes()).hexdigest()==round3['baseSchedule']['sha256']
 prior=c;c=apply_optimization_overlay(c,round3)
 c['provenance']['workingDraft']['draftOverlays'].append({'path':round3_path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(round3_path.read_bytes()).hexdigest()})
 old={l['id']:l for l in prior['legs']};now={l['id']:l for l in c['legs']};assert old.keys()<=now.keys() and len(now)==1216
 added=[now[i]for i in now.keys()-old.keys()];assert {l['flight']for l in added}=={2219,2220}
 assert {(l['origin'],l['destination'])for l in added}=={('PWM','BWI'),('BWI','PWM')}
 for i,l in old.items():
  allowed={'departure','arrival','departureMinute','arrivalMinute'}if l['flight']in{1892,1699}else set()
  if l['route']==175:allowed.add('sequenceWithinRoute')
  assert all(now[i][k]==v for k,v in l.items()if k not in allowed)
 assert c['cities']==prior['cities'] and c['hubBanks']==prior['hubBanks'] and c['operatingPolicy']==prior['operatingPolicy'] and c['schedule']==prior['schedule']
 structure=validate_schedule(c);operating=validate_operating_rules(c);overnight=validate_overnight_turns(c);plan=reconstruct_planning_snapshot(c,demand_data_version='bts-db1c-6mo-jul2025-apr2026-v7');planning=validate_planning_snapshot(plan,c);gates=export_gate_schedule(c)
 assert structure['status']==overnight['status']==planning['status']=='pass' and operating['summary']['effectiveErrorFindings']==0
 checks={x['id']:x for x in operating['checks']};assert [x['id']for x in checks['rolling_ron_grace']['findings']]==['AM'] and checks['fleet_capacity']['metrics']==fleet
 stands=[x for city in gates['cities']for x in city['claims']if x['rowType']=='stand'];assert (len(stands),sum(x['end']-x['start']for x in stands))==(15,3061)
 report.update({'flights':1216,'retimedFlights':[1219,1256,1699,1817,1892,1904],'newFlights':4,'addedFlights':report['addedFlights']+sorted(added,key=lambda l:l['flight']),'netFlightChange':2,'operating':operating['summary'],'acceptedR175':round3['acceptedR175']})
round3_checkpoint=ROOT/'outputs/schedule_7_v1_3_2_r125/base_round_3_canonical.json';round3_checkpoint.parent.mkdir(parents=True,exist_ok=True);round3_checkpoint.write_text(json.dumps(c,indent=2)+'\n')
if '--r175-only' in sys.argv:
 print('Rebuilt pinned R175 checkpoint:',round3_checkpoint);sys.exit(0)
round4_path=ROOT/'config/optimizations/schedule_7_v1_3_2_round_4.json'
if round4_path.exists():
 round4=json.loads(round4_path.read_text());assert hashlib.sha256(round3_checkpoint.read_bytes()).hexdigest()==round4['baseSchedule']['sha256']
 prior=c;c=apply_optimization_overlay(c,round4)
 c['provenance']['workingDraft']['draftOverlays'].append({'path':round4_path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(round4_path.read_bytes()).hexdigest()})
 old={l['id']:l for l in prior['legs']};now={l['id']:l for l in c['legs']};assert old.keys()<=now.keys() and len(now)==1218
 added=[now[i]for i in now.keys()-old.keys()];assert {l['flight']for l in added}=={2221,2222}
 assert {(l['origin'],l['destination'])for l in added}=={('PVD','BWI'),('BWI','PVD')}
 for i,l in old.items():
  allowed={'departure','arrival','departureMinute','arrivalMinute'}if l['flight']==1418 else set()
  if l['route']==125:allowed.add('sequenceWithinRoute')
  assert all(now[i][k]==v for k,v in l.items()if k not in allowed)
 assert c['cities']==prior['cities'] and c['hubBanks']==prior['hubBanks'] and c['operatingPolicy']==prior['operatingPolicy'] and c['schedule']==prior['schedule']
 structure=validate_schedule(c);operating=validate_operating_rules(c);overnight=validate_overnight_turns(c);plan=reconstruct_planning_snapshot(c,demand_data_version='bts-db1c-6mo-jul2025-apr2026-v7');planning=validate_planning_snapshot(plan,c);gates=export_gate_schedule(c)
 assert structure['status']==overnight['status']==planning['status']=='pass' and operating['summary']['effectiveErrorFindings']==0
 checks={x['id']:x for x in operating['checks']};assert [x['id']for x in checks['rolling_ron_grace']['findings']]==['AM'] and checks['fleet_capacity']['metrics']==fleet
 stands=[x for city in gates['cities']for x in city['claims']if x['rowType']=='stand'];assert (len(stands),sum(x['end']-x['start']for x in stands))==(15,3061)
 report.update({'flights':1218,'retimedFlights':[1219,1256,1418,1699,1817,1892,1904],'newFlights':6,'addedFlights':report['addedFlights']+sorted(added,key=lambda l:l['flight']),'netFlightChange':4,'operating':operating['summary'],'acceptedR125':round4['acceptedR125']})
round4_checkpoint=ROOT/'outputs/schedule_7_v1_3_2_r111_r312/base_round_4_canonical.json';round4_checkpoint.parent.mkdir(parents=True,exist_ok=True);round4_checkpoint.write_text(json.dumps(c,indent=2)+'\n')
if '--r125-only' in sys.argv:
 print('Rebuilt pinned R125 checkpoint:',round4_checkpoint);sys.exit(0)
round5_path=ROOT/'config/optimizations/schedule_7_v1_3_2_round_5.json'
if round5_path.exists():
 round5=json.loads(round5_path.read_text());assert hashlib.sha256(round4_checkpoint.read_bytes()).hexdigest()==round5['baseSchedule']['sha256']
 prior=c;c=apply_optimization_overlay(c,round5)
 c['provenance']['workingDraft']['draftOverlays'].append({'path':round5_path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(round5_path.read_bytes()).hexdigest()})
 old={l['id']:l for l in prior['legs']};now={l['id']:l for l in c['legs']};assert len(now)==1221
 assert {old[i]['flight']for i in old.keys()-now.keys()}=={1360}
 added=[now[i]for i in now.keys()-old.keys()];assert {l['flight']for l in added}=={2223,2224,2225,2226}
 assert {(l['origin'],l['destination'])for l in added}=={('BHM','PIE'),('PIE','BHM'),('DAB','PHF'),('PHF','BDL')}
 for i in old.keys()&now.keys():
  l=old[i];allowed={'departure','arrival','departureMinute','arrivalMinute'}if l['flight']==1991 else set()
  if l['route']in{111,312}:allowed.add('sequenceWithinRoute')
  assert all(now[i][k]==v for k,v in l.items()if k not in allowed)
 assert c['cities']==prior['cities'] and c['hubBanks']==prior['hubBanks'] and c['operatingPolicy']==prior['operatingPolicy'] and c['schedule']==prior['schedule']
 structure=validate_schedule(c);operating=validate_operating_rules(c);overnight=validate_overnight_turns(c);plan=reconstruct_planning_snapshot(c,demand_data_version='bts-db1c-6mo-jul2025-apr2026-v7');planning=validate_planning_snapshot(plan,c);gates=export_gate_schedule(c)
 assert structure['status']==overnight['status']==planning['status']=='pass' and operating['summary']['effectiveErrorFindings']==0
 checks={x['id']:x for x in operating['checks']};assert [x['id']for x in checks['rolling_ron_grace']['findings']]==['AM'] and checks['fleet_capacity']['metrics']==fleet
 stands=[x for city in gates['cities']for x in city['claims']if x['rowType']=='stand'];assert (len(stands),sum(x['end']-x['start']for x in stands))==(15,3061)
 report.update({'flights':1221,'retimedFlights':[1219,1256,1418,1699,1817,1892,1904,1991],'newFlights':10,'removedFlights':[1257,1258,1360],'addedFlights':report['addedFlights']+sorted(added,key=lambda l:l['flight']),'netFlightChange':7,'operating':operating['summary'],'acceptedR111':round5['acceptedR111'],'acceptedR312':round5['acceptedR312']})
# The original five rounds remain independently reproducible for pinned historical checks.
# Ordinary execution now produces the cumulative, unpublished 1,229-flight working draft.
if '--five-round-only' not in sys.argv:
 baseline={l['id']:l for l in c['legs']}
 for selected_path in [
  ROOT/'config/proposals/schedule_7_v1_3_2_r144_jax_bna.json',
  ROOT/'config/optimizations/schedule_7_v1_3_2_r146_selected.json',
  ROOT/'config/optimizations/schedule_7_v1_3_2_r176_selected.json',
  ROOT/'config/optimizations/schedule_7_v1_3_2_r158_selected.json',
 ]:
  selected=json.loads(selected_path.read_text())
  c=apply_optimization_overlay(c,selected)
  c['provenance']['workingDraft']['draftOverlays'].append({
   'path':selected_path.relative_to(ROOT).as_posix(),
   'sha256':hashlib.sha256(selected_path.read_bytes()).hexdigest()
  })
 assert len(c['legs'])==1229
 new={l['id']:l for l in c['legs']}
 assert {baseline[i]['flight']for i in baseline.keys()-new.keys()}=={2053,2054}
 assert {(new[i]['origin'],new[i]['destination']) for i in new.keys()-baseline.keys()}=={
  ('JAN','JAX'),('JAX','JAN'),('MCI','BNA'),('BNA','MCI'),
  ('FSD','MCI'),('MCI','FSD'),('PHF','GSO'),('GSO','PHF'),
  ('ALB','RDU'),('RDU','ALB')}
 assert c['cities']==base['cities'] and c['hubBanks']==base['hubBanks']
 assert c['schedule']['fleetCounts']==base['schedule']['fleetCounts']
 structure=validate_schedule(c);operating=validate_operating_rules(c)
 overnight=validate_overnight_turns(c)
 plan=reconstruct_planning_snapshot(c,demand_data_version='bts-db1c-6mo-jul2025-apr2026-v7')
 planning=validate_planning_snapshot(plan,c);gates=export_gate_schedule(c)
 assert structure['status']==planning['status']==overnight['status']=='pass'
 assert operating['summary']['effectiveErrorFindings']==0
 checks={x['id']:x for x in operating['checks']}
 assert [x['id']for x in checks['rolling_ron_grace']['findings']]==['AM']
 assert checks['fleet_capacity']['metrics']==fleet
 stands=[x for city in gates['cities']for x in city['claims']if x['rowType']=='stand']
 assert (len(stands),sum(x['end']-x['start']for x in stands))==(15,3061)
 report.update({'flights':1229,'lines':17,'newFlights':20,'netFlightChange':15,
  'removedFlights':[1257,1258,1360,2053,2054],
  'selectedGroupRoutes':[144,146,158,176],
  'publication':'Not authorized; app default remains v1.3.1',
  'operating':operating['summary'],'standClaims':len(stands),
  'standMinutes':sum(x['end']-x['start']for x in stands)})
out=ROOT/'data/schedules/schedule_7_v1_3_2_draft';out.mkdir(parents=True,exist_ok=True)
for name,x in {'canonical_schedule.json':c,'validation_report.json':structure,'operating_validation_report.json':operating,'overnight_turn_validation.json':overnight,'planning_snapshot.json':plan,'planning_validation_report.json':planning,'gates.json':gates,'timetable.json':export_timetable(c),'draft_report.json':report}.items():(out/name).write_text(json.dumps(x,indent=2)+'\n')
print(json.dumps(report))
