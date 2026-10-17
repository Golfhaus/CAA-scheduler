"""Build and validate maintenance repair alternatives from the released v1.3.1."""
from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
source=ROOT/'data/schedules/schedule_7_v1_3_1/canonical_schedule.json';base=json.loads(source.read_text());by={l['flight']:l for l in base['legs']}
out=ROOT/'outputs/schedule_7_v1_3_2_maintenance';out.mkdir(parents=True,exist_ok=True)
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def move(o,f,r):o.setdefault('legReassignments',[]).append({'legId':by[f]['id'],'expectedRoute':by[f]['route'],'targetRoute':r})
def retime(o,f,d):
 l=by[f];delta=d-l['departureMinute'];o.setdefault('retimeLegs',[]).append({'legId':l['id'],'expectedDepartureMinute':l['departureMinute'],'expectedArrivalMinute':l['arrivalMinute'],'departureMinute':d,'arrivalMinute':l['arrivalMinute']+delta})
def bank(o,f,op,b):o.setdefault('bankAssignmentReplacements',[]).append({'legId':by[f]['id'],'operation':op,'bankId':b})
o={'schemaVersion':'1.0.0','id':'schedule-7-v1.3.2-maintenance-repair','baseSchedule':{'scheduleId':base['schedule']['id'],'canonical':source.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'commit':'d0b728cab36c0d1f3e04d5140d755c8760b3809b'},'schedule':{'id':'schedule_7_v1_3_2_draft','version':'1.3.2-draft','label':'Schedule 7, Version 1.3.2 draft','status':'draft'},'approval':{'scope':'Repair repeating-line maintenance validation and AO/AQ/AC rotations','publication':'Not authorized'}}
for f,r in [(2156,336),(1352,331),(1454,351),(1904,156),(1817,166),(2039,108),(2040,108)]:move(o,f,r)
assignments={'AL':[330,331,351,332,333,334,335,336,350,337,327,321],'AK':[338,339,340,341,322,323,324,325,352,326,328,329],'AC':[101,102,103,104,105,106,107,108,167,156],'AM':[157,158,159,160,161,162,163,164,165,166,109,110]}
o['routeReassignments']=[]
for line,routes in assignments.items():
 for day,r in enumerate(routes,1):
  l=next(l for l in base['legs']if l['route']==r);o['routeReassignments'].append({'sourceRoute':r,'expectedLine':l['line'],'expectedDay':l['day'],'expectedFleet':l['fleet'],'line':line,'day':day})
retime(o,1817,1176)
variants={}
p=json.loads(json.dumps(o));retime(p,1904,1268);bank(p,1904,'departure','DAY-B9');variants['two_delays']=p
p=json.loads(json.dumps(o));retime(p,2071,984);bank(p,2071,'departure','DAY-B6');retime(p,2072,1046);bank(p,2072,'arrival','DAY-B8');variants['earlier_rfd']=p
results={}
for name,cfg in variants.items():
 c=apply_optimization_overlay(base,cfg);structural=validate_schedule(c);operating=validate_operating_rules(c);overnight=validate_overnight_turns(c);plan=reconstruct_planning_snapshot(c,demand_data_version='bts-db1c-6mo-jul2025-apr2026-v7');planning=validate_planning_snapshot(plan,c)
 try:gates=export_gate_schedule(c);gate_status='pass'
 except Exception as e:gates=None;gate_status=str(e)
 checks={x['id']:x for x in operating['checks']};valid=structural['status']==overnight['status']==planning['status']=='pass' and operating['summary']['effectiveErrorFindings']==0 and gate_status=='pass'
 results[name]={'valid':valid,'structural':structural,'operating':operating,'overnight':overnight,'planning':planning,'gateStatus':gate_status,'rollingGrace':checks['rolling_ron_grace']['findings'],'lineWarnings':checks['line_route_count']['findings']}
 write(out/(name+'_overlay.json'),cfg);write(out/(name+'_canonical.json'),c)
 print(name,valid,operating['summary'],'grace',checks['rolling_ron_grace']['findings'],'failedChecks',[x['id']for x in operating['checks']if x['status']=='fail'],gate_status,flush=True)
write(out/'native_review.json',results)
