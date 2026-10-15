"""Screen R501 options without modifying the accepted maintenance draft.

Run from any directory. New flying uses the pinned CRJ900 block-time profile;
existing block times remain unchanged. Optional arguments select scenario names.
"""
from pathlib import Path
import json,sys,copy,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.bank_placement import _block_minutes,_local_arrival
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
source=ROOT/'outputs/schedule_7_v1_3_2_maintenance/base_maintenance_canonical.json';base=json.loads(source.read_text());out=ROOT/'outputs/schedule_7_v1_3_2_r501';out.mkdir(parents=True,exist_ok=True)
assert hashlib.sha256(source.read_bytes()).hexdigest()=='c4d61a0e5ac75354774e7462e360c523ed795de7de61d9e750c28ed960c6817c'
cities={c['code']:c for c in base['cities']};profile=next(p for p in json.loads((ROOT/'config/policies/planning_rules_v7.json').read_text())['frequencyAllocation']['fleetProfiles']if p['fleet']=='CRJ900');by={l['flight']:l for l in base['legs']}
def overlay():return {'baseSchedule':{'scheduleId':base['schedule']['id']},'schedule':base['schedule'].copy()}
def retime(o,f,d):
 l=by[f];delta=d-l['departureMinute'];o.setdefault('retimeLegs',[]).append({'legId':l['id'],'expectedDepartureMinute':l['departureMinute'],'expectedArrivalMinute':l['arrivalMinute'],'departureMinute':d,'arrivalMinute':l['arrivalMinute']+delta})
def remove(o,flights):o.setdefault('removeLegs',[]).extend({'legId':by[f]['id'],'expectedRoute':501}for f in flights)
def leg(o,a,b,d):
 ar=_local_arrival(d,_block_minutes(a,b,profile,cities),a,b,cities);identifier=f'R501-REVIEW-{a}-{b}'
 o.setdefault('insertLegs',[]).append({'id':identifier,'route':501,'origin':a,'destination':b,'departureMinute':d,'arrivalMinute':ar})
 for city,op,t in [(a,'departure',d),(b,'arrival',ar)]:
  if city not in base['operatingPolicy']['hubs']:continue
  bank=next((b for b in base['hubBanks']if b['hub']==city and b['startMinute']<=t<b['endMinute']),None)
  if bank is None:raise ValueError(f'No bank for {city} {op} {t}')
  o.setdefault('bankAssignmentsToAdd',[]).append({'legId':identifier,'operation':op,'bankId':bank['id']})
 return ar
def turn(o,a,b,d,r=None):
 ar=leg(o,a,b,d);return leg(o,b,a,ar+40 if r is None else r)
candidates={}
for hub,d,r in [('PHF',440,545),('JAX',403,507),('BHM',403,468),('FLL',403,None),('BWI',403,None),('PIT',403,None),('BNA',403,None)]:
 o=overlay()
 try:ar=turn(o,'MYR',hub,d,r)
 except ValueError:continue
 if ar>635:continue
 candidates['hold_'+hub.lower()]=o
for dest in ['RDU','CLT','BHM']:
 o=overlay();remove(o,[1257,1258]);turn(o,'SFB',dest,990);candidates['replace_chs_'+dest.lower()]=o
for dest in ['RDU','CLT','BNA','BWI','PIT','RFD']:
 o=overlay();retime(o,1256,403);retime(o,1219,536)
 if dest=='RFD':remove(o,[1257,1258])
 ar=turn(o,'SFB',dest,713)
 if dest in ['BWI','PIT']: # Preserve CHS while testing the necessary minimum-turn suffix.
  retime(o,1258,ar+40);retime(o,1257,max(1140,ar+40+67+40))
 elif ar+40>990 and dest!='RFD':retime(o,1258,ar+40)
 candidates['early_return_'+dest.lower()]=o
o=copy.deepcopy(candidates['hold_phf']);q=candidates['replace_chs_rdu']
for k in ['insertLegs','removeLegs','bankAssignmentsToAdd']:o.setdefault(k,[]).extend(q.get(k,[]))
candidates['phf_plus_rdu']=o
o=overlay();retime(o,1256,450);retime(o,1219,585);retime(o,1258,1030);turn(o,'SFB','RDU',765);candidates['balanced_rdu_keep_chs']=o
o=overlay();retime(o,1256,540);retime(o,1219,675);remove(o,[1257,1258]);turn(o,'SFB','RFD',855);candidates['balanced_rfd_replace_chs']=o
for name,myr,abe,sfb in [('rfd_short_holds',480,615,795),('rfd_later_turn',510,645,855)]:
 o=overlay();retime(o,1256,myr);retime(o,1219,abe);remove(o,[1257,1258]);turn(o,'SFB','RFD',sfb);candidates[name]=o
for dest in ['jax','fll','bwi','pit']:
 o=copy.deepcopy(candidates['hold_'+dest]);q=candidates['replace_chs_rdu']
 for k in ['insertLegs','removeLegs','bankAssignmentsToAdd']:o.setdefault(k,[]).extend(q.get(k,[]))
 candidates[dest+'_plus_rdu']=o
results={}
for name,o in candidates.items():
 if len(sys.argv)>1 and name not in sys.argv[1:]:continue
 c=apply_optimization_overlay(base,o);s=validate_schedule(c);v=validate_operating_rules(c);n=validate_overnight_turns(c)
 try:
  g=export_gate_schedule(c);gate='pass';stands=[x for city in g['cities']for x in city['claims']if x['rowType']=='stand'];stand={'claims':len(stands),'minutes':sum(x['end']-x['start']for x in stands)}
 except Exception as e:gate=str(e);stand=None
 planning=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
 valid=s['status']==n['status']==planning['status']=='pass'and v['summary']['effectiveErrorFindings']==0 and gate=='pass'
 result={'valid':valid,'operating':v['summary'],'structural':s['status'],'overnight':n['status'],'planningStatus':planning['status'],'failedChecks':[x for x in v['checks']if x['status']=='fail'],'gate':gate,'stands':stand,'overlay':o,'route':sorted([l for l in c['legs']if l['route']==501],key=lambda l:l['sequenceWithinRoute'])}
 results[name]=result
 if valid:(out/(name+'_canonical.json')).write_text(json.dumps(c,indent=2)+'\n')
 print(name,valid,[(x['id'],len(x['findings']))for x in result['failedChecks']],gate,stand,flush=True)
p=out/'native.json';previous=json.loads(p.read_text())if len(sys.argv)>1 and p.exists() else {};previous.update(results);p.write_text(json.dumps(previous,indent=2)+'\n')
