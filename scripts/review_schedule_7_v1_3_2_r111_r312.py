"""Screen R111 BHM and R312 DAB hold alternatives against the cumulative draft; never adopt them."""
from pathlib import Path
import json,sys,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.bank_placement import _block_minutes,_local_arrival
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
source=ROOT/'outputs/schedule_7_v1_3_2_r111_r312/base_round_4_canonical.json';base=json.loads(source.read_text());out=ROOT/'outputs/schedule_7_v1_3_2_r111_r312';out.mkdir(parents=True,exist_ok=True)
assert hashlib.sha256(source.read_bytes()).hexdigest()=='ecf5306874c274135e8d6b3bbfbd33bfb5ef6e7ed8b2dc2a1bd731bc435e733f'
cities={c['code']:c for c in base['cities']};profiles={p['fleet']:p for p in json.loads((ROOT/'config/policies/planning_rules_v7.json').read_text())['frequencyAllocation']['fleetProfiles']};by={l['flight']:l for l in base['legs']}
def overlay():return {'baseSchedule':{'scheduleId':base['schedule']['id'],'sha256':hashlib.sha256(source.read_bytes()).hexdigest()},'schedule':base['schedule'].copy()}
def bank(o,identifier,city,op,t):
 if city not in base['operatingPolicy']['hubs']:return
 b=next((b for b in base['hubBanks']if b['hub']==city and b['startMinute']<=t<b['endMinute']),None)
 if b is None:raise ValueError(f'No bank for {city} {op} {t}')
 o.setdefault('bankAssignmentReplacements'if identifier in {l['id']for l in base['legs']}else'bankAssignmentsToAdd',[]).append({'legId':identifier,'operation':op,'bankId':b['id']})
def retime(o,f,d):
 l=by[f];ar=l['arrivalMinute']+d-l['departureMinute'];o.setdefault('retimeLegs',[]).append({'legId':l['id'],'expectedDepartureMinute':l['departureMinute'],'expectedArrivalMinute':l['arrivalMinute'],'departureMinute':d,'arrivalMinute':ar})
 bank(o,l['id'],l['origin'],'departure',d);bank(o,l['id'],l['destination'],'arrival',ar)
def leg(o,r,a,b,d):
 profile=profiles[next(l['fleet']for l in base['legs']if l['route']==r)]
 ar=_local_arrival(d,_block_minutes(a,b,profile,cities),a,b,cities);identifier=f'REVIEW-R{r}-{a}-{b}'
 o.setdefault('insertLegs',[]).append({'id':identifier,'route':r,'origin':a,'destination':b,'departureMinute':d,'arrivalMinute':ar})
 bank(o,identifier,a,'departure',d);bank(o,identifier,b,'arrival',ar);return ar
def turn(o,r,a,b,d,back=None):
 ar=leg(o,r,a,b,d);return leg(o,r,b,a,ar+40 if back is None else back)
candidates={}
o=overlay();turn(o,111,'BHM','CLT',834);candidates['111_clt']=o
o=overlay();turn(o,111,'BHM','JAX',834);candidates['111_jax_no_retime']=o
o=overlay();retime(o,1991,657);turn(o,111,'BHM','JAX',825);candidates['111_jax']=o
o=overlay();retime(o,1991,624);turn(o,111,'BHM','DAY',792);candidates['111_day']=o
o=overlay();retime(o,1991,638);turn(o,111,'BHM','SFB',806);candidates['111_sfb']=o
o=overlay();retime(o,1991,640);turn(o,111,'BHM','PIE',808);candidates['111_pie']=o
for last in [1181,1220,1230,1245]:
 o=overlay();o['removeLegs']=[{'legId':by[1360]['id'],'expectedRoute':312}];leg(o,312,'DAB','PHF',1033);leg(o,312,'PHF','BDL',last);candidates['312_phf_tail_'+str(last)]=o
o=overlay();turn(o,312,'DAB','JAX',1033,1115);candidates['312_jax']=o
o=overlay();retime(o,1921,746);retime(o,1922,866);turn(o,312,'DAB','CLT',1014);candidates['312_clt']=o
for advance in [15,30,42]:
 o=overlay();retime(o,1991,666-advance);turn(o,111,"BHM","CLT",834-advance);candidates["111_clt_advance_"+str(advance)]=o
for arrival,last in [(1170,1220),(1180,1220),(1190,1230)]:
 o=overlay();o["removeLegs"]=[{"legId":by[1360]["id"],"expectedRoute":312}];leg(o,312,"DAB","PHF",arrival-108);leg(o,312,"PHF","BDL",last);candidates["312_bank_arrival_"+str(arrival)]=o
results={}
for name,o in candidates.items():
 if len(sys.argv)>1 and name not in sys.argv[1:]:continue
 c=apply_optimization_overlay(base,o);s=validate_schedule(c);v=validate_operating_rules(c);n=validate_overnight_turns(c);p=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
 try:
  g=export_gate_schedule(c);gate='pass';stands=[x for city in g['cities']for x in city['claims']if x['rowType']=='stand'];stand={'claims':len(stands),'minutes':sum(x['end']-x['start']for x in stands)}
 except Exception as e:gate=str(e);stand=None
 valid=s['status']==n['status']==p['status']=='pass'and v['summary']['effectiveErrorFindings']==0 and gate=='pass'
 results[name]={'valid':valid,'operating':v['summary'],'structural':s['status'],'overnight':n['status'],'planning':p['status'],'failedChecks':[x for x in v['checks']if x['status']=='fail'],'gate':gate,'stands':stand,'overlay':o,'route':sorted([l for l in c['legs']if l['route']in{111,312}],key=lambda l:l['sequenceWithinRoute'])}
 if valid:(out/(name+'_canonical.json')).write_text(json.dumps(c,indent=2)+'\n')
 print(name,valid,[(x['id'],len(x['findings']))for x in results[name]['failedChecks']],gate,stand,flush=True)
p=out/'native.json';previous=json.loads(p.read_text())if len(sys.argv)>1 and p.exists() else {};previous.update(results);p.write_text(json.dumps(previous,indent=2)+'\n')
