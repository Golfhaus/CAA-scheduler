"""Screen R175 alternatives against the cumulative draft; never adopt them."""
from pathlib import Path
import json,sys,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.bank_placement import _block_minutes,_local_arrival
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
source=ROOT/'data/schedules/schedule_7_v1_3_2_draft/canonical_schedule.json';base=json.loads(source.read_text());out=ROOT/'outputs/schedule_7_v1_3_2_r175';out.mkdir(parents=True,exist_ok=True)
assert hashlib.sha256(source.read_bytes()).hexdigest()=='1f38ce33278f9b330ca8a38d831e7294b626de25924676a5232bb7cc68f81af4'
cities={c['code']:c for c in base['cities']};profile=next(p for p in json.loads((ROOT/'config/policies/planning_rules_v7.json').read_text())['frequencyAllocation']['fleetProfiles']if p['fleet']=='CRJ200');by={l['flight']:l for l in base['legs']}
def overlay():return {'baseSchedule':{'scheduleId':base['schedule']['id'],'sha256':hashlib.sha256(source.read_bytes()).hexdigest()},'schedule':base['schedule'].copy()}
def bank(o,identifier,city,op,t):
 if city not in base['operatingPolicy']['hubs']:return
 b=next((b for b in base['hubBanks']if b['hub']==city and b['startMinute']<=t<b['endMinute']),None)
 if b is None:raise ValueError(f'No bank for {city} {op} {t}')
 o.setdefault('bankAssignmentReplacements'if identifier in {l['id']for l in base['legs']}else'bankAssignmentsToAdd',[]).append({'legId':identifier,'operation':op,'bankId':b['id']})
def retime(o,f,d):
 l=by[f];ar=l['arrivalMinute']+d-l['departureMinute'];o.setdefault('retimeLegs',[]).append({'legId':l['id'],'expectedDepartureMinute':l['departureMinute'],'expectedArrivalMinute':l['arrivalMinute'],'departureMinute':d,'arrivalMinute':ar})
 bank(o,l['id'],l['origin'],'departure',d);bank(o,l['id'],l['destination'],'arrival',ar)
def leg(o,a,b,d):
 ar=_local_arrival(d,_block_minutes(a,b,profile,cities),a,b,cities);identifier=f'R175-REVIEW-{a}-{b}'
 o.setdefault('insertLegs',[]).append({'id':identifier,'route':175,'origin':a,'destination':b,'departureMinute':d,'arrivalMinute':ar})
 bank(o,identifier,a,'departure',d);bank(o,identifier,b,'arrival',ar);return ar
def turn(o,a,b,d,r=None):
 ar=leg(o,a,b,d);return leg(o,b,a,ar+40 if r is None else r)
candidates={}
for d in [623,630,640]:
 o=overlay();turn(o,'PWM','BWI',d);candidates['bwi_'+str(d)]=o
o=overlay();retime(o,1892,407);retime(o,1699,505);turn(o,'PWM','BWI',613);candidates['bwi_minor_retiming']=o
o=overlay();retime(o,1892,270);retime(o,1699,368);turn(o,'PWM','BWI',540);candidates['early_bwi']=o
o=overlay();retime(o,1892,407);retime(o,1699,505);retime(o,1704,901);retime(o,1907,1011);turn(o,'PWM','PIT',613);candidates['pit_minor_retiming']=o
o=overlay();retime(o,1892,407);retime(o,1699,505);retime(o,1704,903);retime(o,1907,1013);turn(o,'PWM','SYR',613,795);candidates['syr_midday']=o
for depart,back in [(476,646),(510,654),(520,664)]:
 o=overlay();retime(o,1892,270);retime(o,1699,368);turn(o,'PWM','PHF',depart,back);candidates['early_phf_'+str(depart)]=o
for depart in [270,310,407]:
 o=overlay();retime(o,1892,depart);candidates['earlier_start_'+str(depart)]=o
results={}
for name,o in candidates.items():
 if len(sys.argv)>1 and name not in sys.argv[1:]:continue
 c=apply_optimization_overlay(base,o);s=validate_schedule(c);v=validate_operating_rules(c);n=validate_overnight_turns(c);p=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
 try:
  g=export_gate_schedule(c);gate='pass';stands=[x for city in g['cities']for x in city['claims']if x['rowType']=='stand'];stand={'claims':len(stands),'minutes':sum(x['end']-x['start']for x in stands)}
 except Exception as e:gate=str(e);stand=None
 valid=s['status']==n['status']==p['status']=='pass'and v['summary']['effectiveErrorFindings']==0 and gate=='pass'
 results[name]={'valid':valid,'operating':v['summary'],'structural':s['status'],'overnight':n['status'],'planning':p['status'],'failedChecks':[x for x in v['checks']if x['status']=='fail'],'gate':gate,'stands':stand,'overlay':o,'route':sorted([l for l in c['legs']if l['route']==175],key=lambda l:l['sequenceWithinRoute'])}
 if valid:(out/(name+'_canonical.json')).write_text(json.dumps(c,indent=2)+'\n')
 print(name,valid,[(x['id'],len(x['findings']))for x in results[name]['failedChecks']],gate,stand,flush=True)
p=out/'native.json';previous=json.loads(p.read_text())if len(sys.argv)>1 and p.exists() else {};previous.update(results);p.write_text(json.dumps(previous,indent=2)+'\n')
