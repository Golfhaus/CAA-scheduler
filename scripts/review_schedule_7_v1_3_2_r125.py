"""Screen R125 PVD hold alternatives against the cumulative draft; never adopt them."""
from pathlib import Path
import json,sys,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.bank_placement import _block_minutes,_local_arrival
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
source=ROOT/'data/schedules/schedule_7_v1_3_2_draft/canonical_schedule.json';base=json.loads(source.read_text());out=ROOT/'outputs/schedule_7_v1_3_2_r125';out.mkdir(parents=True,exist_ok=True)
assert hashlib.sha256(source.read_bytes()).hexdigest()=='bd8aa5abd219ade2186d63a3cd01b61b3c66162a9f97d5be25712e91199d1cbf'
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
 ar=_local_arrival(d,_block_minutes(a,b,profile,cities),a,b,cities);identifier=f'R125-REVIEW-{a}-{b}'
 o.setdefault('insertLegs',[]).append({'id':identifier,'route':125,'origin':a,'destination':b,'departureMinute':d,'arrivalMinute':ar})
 bank(o,identifier,a,'departure',d);bank(o,identifier,b,'arrival',ar);return ar
def turn(o,a,b,d,r=None):
 ar=leg(o,a,b,d);return leg(o,b,a,ar+40 if r is None else r)
candidates={}
for d in [469,480,495,510]:
 o=overlay();turn(o,'PVD','BWI',d);candidates['bwi_'+str(d)]=o
for d in [469,475,490]:
 o=overlay();turn(o,'PVD','PHF',d);candidates['phf_'+str(d)]=o
for d in [469,475,476]:
 o=overlay();turn(o,'PVD','PIT',d);candidates['pit_'+str(d)]=o
o=overlay();retime(o,1418,557);turn(o,'PVD','BWI',510,625);candidates['bwi_two_minute_fix']=o
results={}
for name,o in candidates.items():
 if len(sys.argv)>1 and name not in sys.argv[1:]:continue
 c=apply_optimization_overlay(base,o);s=validate_schedule(c);v=validate_operating_rules(c);n=validate_overnight_turns(c);p=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
 try:
  g=export_gate_schedule(c);gate='pass';stands=[x for city in g['cities']for x in city['claims']if x['rowType']=='stand'];stand={'claims':len(stands),'minutes':sum(x['end']-x['start']for x in stands)}
 except Exception as e:gate=str(e);stand=None
 valid=s['status']==n['status']==p['status']=='pass'and v['summary']['effectiveErrorFindings']==0 and gate=='pass'
 results[name]={'valid':valid,'operating':v['summary'],'structural':s['status'],'overnight':n['status'],'planning':p['status'],'failedChecks':[x for x in v['checks']if x['status']=='fail'],'gate':gate,'stands':stand,'overlay':o,'route':sorted([l for l in c['legs']if l['route']==125],key=lambda l:l['sequenceWithinRoute'])}
 if valid:(out/(name+'_canonical.json')).write_text(json.dumps(c,indent=2)+'\n')
 print(name,valid,[(x['id'],len(x['findings']))for x in results[name]['failedChecks']],gate,stand,flush=True)
p=out/'native.json';previous=json.loads(p.read_text())if len(sys.argv)>1 and p.exists() else {};previous.update(results);p.write_text(json.dumps(previous,indent=2)+'\n')
