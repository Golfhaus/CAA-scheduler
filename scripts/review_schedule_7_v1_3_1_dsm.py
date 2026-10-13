"""Screen DSM day-distribution alternatives without changing the accepted draft."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
checkpoint=ROOT/'outputs/schedule_7_v1_3_1_dsm/base_round_3_canonical.json'
source=checkpoint if checkpoint.exists() else ROOT/'data/schedules/schedule_7_v1_3_1_draft/canonical_schedule.json';base=json.loads(source.read_text())
out=ROOT/'outputs/schedule_7_v1_3_1_dsm';out.mkdir(parents=True,exist_ok=True)
byflight={l['flight']:l for l in base['legs']}
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def overlay():return {'baseSchedule':{'scheduleId':base['schedule']['id'],'canonical':source.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()},'schedule':base['schedule'].copy()}
def retime(o,f,d):
 l=byflight[f];delta=d-l['departureMinute'];o.setdefault('retimeLegs',[]).append({'legId':l['id'],'expectedDepartureMinute':l['departureMinute'],'expectedArrivalMinute':l['arrivalMinute'],'departureMinute':d,'arrivalMinute':(l['arrivalMinute']+delta)%1440})
def bank(o,f,op,b):o.setdefault('bankAssignmentReplacements',[]).append({'legId':byflight[f]['id'],'operation':op,'bankId':b})
def addturn(o,r,d,a,bankout,bankin):
 legs=[{'id':f'V131-DSM-R{r}-MCI-DSM','route':r,'origin':'MCI','destination':'DSM','departureMinute':d,'arrivalMinute':d+50},{'id':f'V131-DSM-R{r}-DSM-MCI','route':r,'origin':'DSM','destination':'MCI','departureMinute':a,'arrivalMinute':a+50}]
 o['insertLegs']=legs;o['bankAssignmentsToAdd']=[{'legId':legs[0]['id'],'operation':'departure','bankId':bankout},{'legId':legs[1]['id'],'operation':'arrival','bankId':bankin}]
candidates={}
for name,r,d,a,bo,bi in [('add_noon',155,736,835,'MCI-B5','MCI-B7'),('add_afternoon',154,840,935,'MCI-B6','MCI-B8'),('add_late',114,975,1075,'MCI-B7','MCI-B9')]:
 o=overlay();addturn(o,r,d,a,bo,bi);candidates[name]=o
 for move in [False,True]:
  if not move:continue
  q=overlay();q['legReassignments']=[{'legId':byflight[f]['id'],'expectedRoute':141,'targetRoute':r}for f in [1731,1736]]
  retime(q,1731,d);retime(q,1736,a);bank(q,1731,'departure',bo);bank(q,1736,'arrival',bi);candidates[name.replace('add','move')]=q
for dep in [355,375,445]:
 o=overlay();retime(o,1735,dep);bank(o,1735,'arrival','MCI-B2' if dep+50<445 else 'MCI-B3');candidates[f'early_150_{dep}']=o
o=overlay();retime(o,1210,435);retime(o,1209,535);candidates['rfd_75_later']=o
o=overlay()
o['removeLegs']=[{'legId':byflight[1735]['id'],'expectedRoute':150}]
o['insertLegs']=[{'id':'V131-DSM-R150-DSM-DAY','route':150,'origin':'DSM','destination':'DAY','departureMinute':327,'arrivalMinute':484},{'id':'V131-DSM-R150-DAY-MCI','route':150,'origin':'DAY','destination':'MCI','departureMinute':550,'arrivalMinute':595}]
o['bankAssignmentsToAdd']=[{'legId':'V131-DSM-R150-DSM-DAY','operation':'arrival','bankId':'DAY-B2'},{'legId':'V131-DSM-R150-DAY-MCI','operation':'departure','bankId':'DAY-B3'},{'legId':'V131-DSM-R150-DAY-MCI','operation':'arrival','bankId':'MCI-B4'}]
candidates['day_150']=o
q=overlay();addturn(q,154,840,935,'MCI-B6','MCI-B8');retime(q,1210,435);retime(q,1209,535);candidates['combined_basic']=q
q=json.loads(json.dumps(q))
for k in ['removeLegs','insertLegs','bankAssignmentsToAdd']:
 q.setdefault(k,[]).extend(o.get(k,[]))
candidates['combined_day']=q
results={}
for name,o in candidates.items():
 if len(sys.argv)>1 and name not in sys.argv[1:]:continue
 c=apply_optimization_overlay(base,o);structure=validate_schedule(c);operating=validate_operating_rules(c);overnight=validate_overnight_turns(c)
 try:
  gates=export_gate_schedule(c);gate='pass'
 except Exception as e:gate=str(e)
 valid=structure['status']=='pass' and operating['summary']['effectiveErrorFindings']==0 and overnight['status']=='pass' and gate=='pass'
 results[name]={'valid':valid,'structure':structure['summary'],'operating':operating['summary'],'overnight':overnight['status'],'gate':gate,'failedChecks':[x for x in operating['checks'] if x['status']=='fail'],'overlay':o}
 write(out/(name+'_canonical.json'),c);write(out/(name+'_overlay.json'),o)
 print(name,valid,operating['summary'],[x['id']for x in operating['checks']if x['status']=='fail'],gate,flush=True)
write(out/'native_screen.json',results)
