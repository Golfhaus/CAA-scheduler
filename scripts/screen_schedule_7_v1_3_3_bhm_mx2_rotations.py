"""Screen four spare aircraft on MX-base closed days (no new BHM RON).

The four routes are 529/530 CRJ900, 357/358 CRJ700, each one aircraft-day:
MX hub -> northern city -> BHM -> southern city -> BHM -> northern city -> MX hub.
The morning mini-bank feeds N-to-S; the afternoon split preserves two simultaneous
BHM gates for existing traffic. Only native-passing variants are staged.
"""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.bank_placement import _block_minutes
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads((ROOT/"data/schedules/schedule_7_v1_3_3_draft/canonical_schedule.json").read_text())
rules=json.loads((ROOT/"config/policies/planning_rules_v7.json").read_text())
cities={x["code"]:x for x in base["cities"]}
profiles={x["fleet"]:x for x in rules["frequencyAllocation"]["fleetProfiles"]}
out=ROOT/"outputs/schedule_7_v1_3_3_bhm_minibanks_mx2";out.mkdir(parents=True,exist_ok=True)
hub_banks={h:[b for b in base["hubBanks"] if b["hub"]==h] for h in base["operatingPolicy"]["hubs"]}
def block(a,b,fleet):return _block_minutes(a,b,profiles[fleet],cities)
def local(city,ct):return ct+(60 if cities[city]["timezone"]=="Eastern" else 0)
def bank(city,t):
 return next((b["id"] for b in hub_banks.get(city,[]) if b["startMinute"]<=t<b["endMinute"]),None)
def last_legal_depart(hub,latest):
 possible=[t for x in hub_banks[hub]for t in range(x["startMinute"],x["endMinute"]) if t<=latest and t>=270]
 return max(possible) if possible else None
def first_legal_arrive(hub,earliest,latest):
 possible=[t for x in hub_banks[hub] for t in range(x["startMinute"],x["endMinute"]) if earliest<=t<=latest]
 return min(possible) if possible else None
def newroute(route,line,fleet,hub,north,south,morning_bhm,south_dep,south_back,north_dep):
 bn=block(north,"BHM",fleet);bs=block("BHM",south,fleet);bh=block(hub,north,fleet)
 n_depart_ct=morning_bhm-bn
 hub_latest=local(north,n_depart_ct)-40-bh
 first=last_legal_depart(hub,hub_latest)
 if first is None:raise ValueError(f"{route} no morning {hub} bank allows north arrival and 40 min turn")
 first_ct=first-(60 if cities[hub]["timezone"]=="Eastern" else 0)
 # first flight origin hub, north arrival
 first_n_arr_ct=first_ct+bh
 if n_depart_ct-first_n_arr_ct<40:raise ValueError(f"{route} short north morning")
 s_arr_ct=south_dep+bs
 s_depart_ct=south_back-bs
 if south_dep-morning_bhm<40 or s_depart_ct-s_arr_ct<40 or north_dep-south_back<40:
  raise ValueError(f"{route} short BHM/south turn: {morning_bhm,south_dep,south_back,north_dep,bs}")
 last_n_arr_ct=north_dep+bn
 north_final_ct=last_n_arr_ct+40
 last_h_first_ct=north_final_ct+bh
 # Hub terminator bank is desirable but not necessary if the turn is outside
 # the formal bank; however, only retain banked arrival candidates.
 arrival_h=first_legal_arrive(hub,local(hub,last_h_first_ct),local(hub,last_h_first_ct)+90)
 if arrival_h is None:raise ValueError(f"{route} no {hub} terminal bank near {last_h_first_ct}")
 north_final_ct += arrival_h-local(hub,last_h_first_ct)
 if local(north,north_final_ct)>1260:raise ValueError(f"{route} northern final dep after 21:00 local")
 last_arr_ct=north_final_ct+bh
 sequence=[(hub,north,first_ct,first_n_arr_ct),
           (north,"BHM",n_depart_ct,morning_bhm),
           ("BHM",south,south_dep,s_arr_ct),
           (south,"BHM",s_depart_ct,south_back),
           ("BHM",north,north_dep,last_n_arr_ct),
           (north,hub,north_final_ct,last_arr_ct)]
 legs=[]
 for idx,(a,d,dep,arr) in enumerate(sequence,1):
  ld=local(a,dep);la=local(d,arr)
  if not (270 <= ld <= (1410 if a in (base["operatingPolicy"]["hubs"] + base["operatingPolicy"]["focusCities"]) else 1260)):
   raise ValueError(f"curfew departure {route}/{idx} {a} {ld}")
  legs.append({"id":f"V133-BHM-{route}-{idx}-{a}-{d}","origin":a,"destination":d,
               "departureMinute":ld,"arrivalMinute":la})
 assignments=[]
 for idx,leg in enumerate(legs):
  for code,op,t in [(leg["origin"],"departure",leg["departureMinute"]),(leg["destination"],"arrival",leg["arrivalMinute"])]:
   if code not in hub_banks:continue
   bid=bank(code,t)
   if not bid:raise ValueError(f"{route} {code} {op} {t} off bank")
   assignments.append({"legId":leg["id"],"operation":op,"bankId":bid})
 return {"route":route,"line":line,"fleet":fleet,"day":1,"legs":legs},assignments
def make(label,adjust=0,swap=False):
 # Prefer PGD over SFB/FLL: CAK has zero geographically reasonable one-stop
 # to PGD, whereas the higher-demand SFB/FLL markets are already well covered.
 items=[
  (529,"BA","CRJ900","SYR","ALB","SRQ",604,651,903,943),
  (530,"BB","CRJ900","SYR","CAK","MYR",606,653,906,946),
  (357,"BC","CRJ700","SYR","ISP","PGD",610,655,960,1000),
  (358,"BD","CRJ700","SYR","HVN","CHS",612,657,954,994),
 ]
 if swap:
  items[2] = (357,"BC","CRJ700","PHF","ISP","PGD",610,655,960,1000)
  items[3] = (358,"BD","CRJ700","SYR","HVN","CHS",612,657,954,994)
 overlay={"schemaVersion":"1.0.0","id":"schedule-7-v1.3.3-bhm-mx-"+label,
  "baseSchedule":{"scheduleId":base["schedule"]["id"]},"schedule":base["schedule"],"addRoutes":[],"bankAssignmentsToAdd":[]}
 for route,line,fleet,hub,north,south,morning,sout,out_south,dep_n in items:
  route_spec,assign=newroute(route,line,fleet,hub,north,south,morning,sout+adjust,out_south+adjust,dep_n+adjust)
  overlay["addRoutes"].append(route_spec)
  overlay["bankAssignmentsToAdd"].extend(assign)
 return overlay
cases=[("base",0,False),("late",8,False),("swap",0,True)]
results={}
for label,adjust,swap in cases:
 try:
  overlay=make(label,adjust,swap)
  can=apply_optimization_overlay(base,overlay)
  s=validate_schedule(can);v=validate_operating_rules(can);n=validate_overnight_turns(can)
  p=validate_planning_snapshot(reconstruct_planning_snapshot(can),can)
  try:g=export_gate_schedule(can);gate="pass"
  except Exception as e:gate=repr(e);g=None
  passed=s["status"]==n["status"]==p["status"]=="pass" and v["summary"]["effectiveErrorFindings"]==0 and gate=="pass"
  results[label]={"pass":passed,"structure":s["status"],"overnight":n["status"],"planning":p["status"],"gate":gate,
   "operating":v["summary"],"failed":[{"id":x["id"],"count":len(x["findings"]),"examples":x["findings"][:4]}for x in v["checks"] if x["status"]=="fail"],
   "fleets":next(x for x in v["checks"] if x["id"]=="fleet_capacity")["metrics"],
   "routes":overlay["addRoutes"]}
  if passed:
   (out/(label+"_overlay.json")).write_text(json.dumps(overlay,indent=2)+"\n")
   (out/(label+"_canonical.json")).write_text(json.dumps(can,indent=2)+"\n")
  print(label,"PASS"if passed else"FAIL",gate,[(x["id"],x["count"])for x in results[label]["failed"]],flush=True)
 except Exception as e:
  results[label]={"pass":False,"error":repr(e),"trace":traceback.format_exc()[-1500:]}
  print(label,"ERROR",repr(e),flush=True)
 (out/"physical_screen.json").write_text(json.dumps(results,indent=2)+"\n")
