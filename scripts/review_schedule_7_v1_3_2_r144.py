"""Screen holistic R144 rebuilds against the accepted five-overlay draft; do not adopt."""
from pathlib import Path
import json,sys,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.bank_placement import _block_minutes,_local_arrival
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
source=ROOT/'data/schedules/schedule_7_v1_3_2_draft/canonical_schedule.json';base=json.loads(source.read_text());out=ROOT/'outputs/schedule_7_v1_3_2_r144';out.mkdir(parents=True,exist_ok=True)
assert hashlib.sha256(source.read_bytes()).hexdigest()=='4de8042da82c48f67a991551476e620f01b17cade91d75b5189e9a53ecbb48b0'
cities={c['code']:c for c in base['cities']};profile=next(p for p in json.loads((ROOT/'config/policies/planning_rules_v7.json').read_text())['frequencyAllocation']['fleetProfiles']if p['fleet']=='CRJ200');by={l['flight']:l for l in base['legs']}
def overlay():return {'baseSchedule':{'scheduleId':base['schedule']['id'],'sha256':hashlib.sha256(source.read_bytes()).hexdigest()},'schedule':base['schedule'].copy()}
def bank(o,identifier,city,op,t):
 if city not in base['operatingPolicy']['hubs']:return
 b=next((b for b in base['hubBanks']if b['hub']==city and b['startMinute']<=t%1440<b['endMinute']),None)
 if b is None:raise ValueError(f'No bank for {city} {op} {t}')
 o.setdefault('bankAssignmentReplacements'if identifier in {l['id']for l in base['legs']}else'bankAssignmentsToAdd',[]).append({'legId':identifier,'operation':op,'bankId':b['id']})
def retime(o,f,d):
 l=by[f];ar=l['arrivalMinute']+d-l['departureMinute'];o.setdefault('retimeLegs',[]).append({'legId':l['id'],'expectedDepartureMinute':l['departureMinute'],'expectedArrivalMinute':l['arrivalMinute'],'departureMinute':d,'arrivalMinute':ar});bank(o,l['id'],l['origin'],'departure',d);bank(o,l['id'],l['destination'],'arrival',ar)
def leg(o,a,b,d):
 ar=_local_arrival(d,_block_minutes(a,b,profile,cities),a,b,cities);identifier=f'REVIEW-R144-{a}-{b}'
 o.setdefault('insertLegs',[]).append({'id':identifier,'route':144,'origin':a,'destination':b,'departureMinute':d,'arrivalMinute':ar});bank(o,identifier,a,'departure',d);bank(o,identifier,b,'arrival',ar);return ar
def turn(o,a,b,d,back=None):
 ar=leg(o,a,b,d);return leg(o,b,a,ar+40 if back is None else back)
candidates={}
# Retain all four sectors; put the morning MCI arrival into B2, shorten OKC's hold,
# and use MCI's late banks for the second turn and SHV termination.
for end,back,last in [('DAL',1156,1287),('RFD',1196,1335),('AUS',1182,1339),('SAT',1210,1375)]:
 o=overlay();retime(o,1500,300);retime(o,1553,785);retime(o,1554,914);retime(o,1596,last);turn(o,'MCI','HOU',443);turn(o,'MCI',end,1025,back);candidates['retain_hou_'+end.lower()]=o
# Start via JAX and retain OKC out-and-back and MCI-SHV; two other JAN-MCI nonstops remain.
o=overlay();o['removeLegs']=[{'legId':by[1500]['id'],'expectedRoute':144}];leg(o,'JAN','JAX',270);leg(o,'JAX','MCI',486);retime(o,1553,625);retime(o,1554,736);turn(o,'MCI','HOU',884,1064);retime(o,1596,1224);candidates['jax_rebuild']=o
# Morning BNA and evening HOU offers the reverse market emphasis with all originals retained.
o=overlay();retime(o,1500,300);turn(o,'MCI','BNA',443,590);retime(o,1553,725);retime(o,1554,836);turn(o,'MCI','HOU',985);retime(o,1596,1335);candidates['retain_bna_hou']=o
# A less extensive six-flight alternative, retaining original OKC clocks.
o=overlay();retime(o,1500,300);turn(o,'MCI','BNA',443,590);candidates['six_bna_morning']=o
for start in [282,288,294]:
 o=overlay();retime(o,1500,start);retime(o,1553,785);retime(o,1554,914);retime(o,1596,1287);turn(o,'MCI','HOU',start+143);turn(o,'MCI','DAL',1025,1156);candidates['early_hou_dal_'+str(start)]=o
o=overlay();o['removeLegs']=[{'legId':by[1500]['id'],'expectedRoute':144}];leg(o,'JAN','JAX',270);leg(o,'JAX','MCI',505);turn(o,'MCI','HOU',644);retime(o,1553,985);retime(o,1554,1113);retime(o,1596,1224);candidates['jax_hou_rebuild']=o
# Use B3 instead of the physically full early B2 bank.
o=overlay();retime(o,1500,384);turn(o,'MCI','BNA',527,690);retime(o,1553,825);retime(o,1554,936);turn(o,'MCI','RFD',1085,1202);retime(o,1596,1335);candidates['bna_rfd_late']=o
o=overlay();retime(o,1500,384);turn(o,'MCI','HOU',527);retime(o,1553,884);retime(o,1554,1014);turn(o,'MCI','DSM',1125,1215);retime(o,1596,1335);candidates['hou_dsm_late']=o
# Arrive after B2's main departures and depart at B3's start to avoid a full bank.
o=overlay();retime(o,1500,341);turn(o,'MCI','HOU',487,665);retime(o,1553,825);retime(o,1554,936);turn(o,'MCI','RFD',1085,1202);retime(o,1596,1335);candidates['edge_hou_rfd']=o
o=overlay();retime(o,1500,341);turn(o,'MCI','BNA',487,643);retime(o,1553,785);retime(o,1554,914);turn(o,'MCI','DAL',1025,1156);retime(o,1596,1287);candidates['edge_bna_dal']=o
for end,back,last in [('DSM',1175,1265),('OMA',1174,1263),('BNA',1240,1375),('LIT',1200,1335)]:
 o=overlay();retime(o,1500,341);turn(o,'MCI','HOU',487,665);retime(o,1553,825);retime(o,1554,936);turn(o,'MCI',end,1085,back);retime(o,1596,last);candidates['edge_hou_'+end.lower()]=o
o=overlay();o['removeLegs']=[{'legId':by[1500]['id'],'expectedRoute':144}];leg(o,'JAN','JAX',270);leg(o,'JAX','MCI',505);turn(o,'MCI','HOU',644,865);retime(o,1553,1044);retime(o,1554,1174);retime(o,1596,1285);candidates['jax_hou_late_bank']=o
# Retain all four sectors and original OKC-MCI clock, using an early JAN-JAX turn.
o=overlay();turn(o,'JAN','JAX',270,468);retime(o,1500,582);retime(o,1553,785);turn(o,'MCI','BNA',1036,1171);retime(o,1596,1335);candidates['jan_jax_bna_preserve_okc_return']=o
for start in [290,300]:
 o=overlay();turn(o,'JAN','JAX',start,start+198);retime(o,1500,582);retime(o,1553,785);turn(o,'MCI','BNA',1036,1171);retime(o,1596,1335);candidates['jan_jax_bna_'+str(start)]=o
# A second early hub choice: retain OKC and SHV flying, replace JAN-MCI with JAN-DAY-MCI.
o=overlay();o['removeLegs']=[{'legId':by[1500]['id'],'expectedRoute':144}];leg(o,'JAN','DAY',270);leg(o,'DAY','MCI',483);turn(o,'MCI','HOU',585,764);retime(o,1553,924);retime(o,1554,1035);retime(o,1596,1184);candidates['day_hou_rebuild']=o
# Six-flight rebuild: retain all four sectors and add only the strongest new turn.
o=overlay();retime(o,1500,425);turn(o,'MCI','HOU',585,764);retime(o,1553,924);retime(o,1554,1035);retime(o,1596,1184);candidates['six_hou_rebuild']=o
# Concentrate on a second MCI-BWI pair, retaining every original sector and a useful JAN clock.
for back in [1145,1155,1164]:
 o=overlay();retime(o,1500,425);retime(o,1553,635);retime(o,1554,746);turn(o,'MCI','BWI',884,back);retime(o,1596,back+140);candidates['six_bwi_'+str(back)]=o
results={}
for name,o in candidates.items():
 if len(sys.argv)>1 and name not in sys.argv[1:]:continue
 try:
  c=apply_optimization_overlay(base,o);s=validate_schedule(c);v=validate_operating_rules(c);n=validate_overnight_turns(c);p=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
  try:
   g=export_gate_schedule(c);gate='pass';stands=[x for city in g['cities']for x in city['claims']if x['rowType']=='stand'];stand={'claims':len(stands),'minutes':sum(x['end']-x['start']for x in stands)}
  except Exception as e:gate=str(e);stand=None
  valid=s['status']==n['status']==p['status']=='pass'and v['summary']['effectiveErrorFindings']==0 and gate=='pass'
  results[name]={'valid':valid,'operating':v['summary'],'structural':s['status'],'overnight':n['status'],'planning':p['status'],'failedChecks':[x for x in v['checks']if x['status']=='fail'],'gate':gate,'stands':stand,'overlay':o,'route':sorted([l for l in c['legs']if l['route']==144],key=lambda l:l['sequenceWithinRoute'])}
  if valid:(out/(name+'_canonical.json')).write_text(json.dumps(c,indent=2)+'\n')
  print(name,valid,[(x['id'],len(x['findings']))for x in results[name]['failedChecks']],gate,stand,flush=True)
 except Exception as e:results[name]={'valid':False,'exception':str(e),'overlay':o};print(name,str(e),flush=True)
 p=out/'native.json';previous=json.loads(p.read_text())if p.exists() else {};previous.update(results);p.write_text(json.dumps(previous,indent=2)+'\n')
