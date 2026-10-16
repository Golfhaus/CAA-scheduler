"""Screen demand-conscious existing-line extensions on five CRJ200 routes.

Reads validated R144-staged canonical; never modifies released or accepted data.
Creates independent and cumulative proposals only if all native checks pass.
"""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.timetable import export_timetable
from caa_scheduler.bank_placement import _block_minutes,_local_arrival
base=json.loads((ROOT/"outputs/schedule_7_v1_3_2_r144_accepted/canonical_schedule.json").read_text())
out=ROOT/"outputs/schedule_7_v1_3_2_group_optimization"
out.mkdir(parents=True,exist_ok=True)
cities={c["code"]:c for c in base["cities"]}
profile=next(x for x in json.loads((ROOT/"config/policies/planning_rules_v7.json").read_text())["frequencyAllocation"]["fleetProfiles"] if x["fleet"]=="CRJ200")
old={x["flight"]:x for x in base["legs"]}
banks={x["id"]:x for x in base["hubBanks"]}
hubs=set(base["operatingPolicy"]["hubs"])
def proposal():
 return {"baseSchedule":{"scheduleId":base["schedule"]["id"]},"schedule":base["schedule"]}
def retime(o,flight,depart):
 leg=old[flight]; block=_block_minutes(leg["origin"],leg["destination"],profile,cities)
 arrival=_local_arrival(depart,block,leg["origin"],leg["destination"],cities)
 assert (leg["arrivalMinute"]-leg["departureMinute"])%1440 == (arrival-depart)%1440,(flight,leg,arrival)
 o.setdefault("retimeLegs",[]).append({"legId":leg["id"],"expectedDepartureMinute":leg["departureMinute"],"expectedArrivalMinute":leg["arrivalMinute"],"departureMinute":depart,"arrivalMinute":arrival})
 return arrival
def add(o,route,origin,dest,depart,identifier):
 arrival=_local_arrival(depart,_block_minutes(origin,dest,profile,cities),origin,dest,cities)
 o.setdefault("insertLegs",[]).append({"id":identifier,"route":route,"origin":origin,"destination":dest,"departureMinute":depart,"arrivalMinute":arrival})
 for city,op,t in ((origin,"departure",depart),(dest,"arrival",arrival)):
  if city not in hubs:continue
  matches=[bank for bank in banks.values() if bank["hub"]==city and bank["startMinute"]<=t<bank["endMinute"]]
  if not matches:raise ValueError(f"{identifier} {city} {op} {t} outside banks")
  o.setdefault("bankAssignmentsToAdd",[]).append({"legId":identifier,"operation":op,"bankId":matches[0]["id"]})
 return arrival
def change_bank(o,flight,op,bank_id):
 o.setdefault("bankAssignmentReplacements",[]).append({"legId":old[flight]["id"],"operation":op,"bankId":bank_id})
def extension146():
 o=proposal()
 retime(o,1677,1105) # MCI-FSD dep 18:25 CT, 30 min earlier
 a=add(o,146,"FSD","MCI",1216,"V132-R146-FSD-MCI-LATE")
 b=add(o,146,"MCI","FSD",1335,"V132-R146-MCI-FSD-LATE")
 return o
def extension107():
 o=proposal()
 retime(o,1674,1125) # SYR-CAK dep 18:45 ET instead of 19:35
 add(o,107,"CAK","SYR",1236,"V132-R107-CAK-SYR-LATE")
 add(o,107,"SYR","CAK",1347,"V132-R107-SYR-CAK-LATE")
 return o
def extension160():
 o=proposal()
 retime(o,1701,1125) # SYR-PWM dep 18:45 ET instead of 19:00
 add(o,160,"PWM","SYR",1233,"V132-R160-PWM-SYR-LATE")
 add(o,160,"SYR","PWM",1341,"V132-R160-SYR-PWM-LATE")
 return o
def extension158():
 o=proposal()
 retime(o,1752,990) # SYR-ALB dep 16:30 instead of 16:45
 retime(o,2053,1249) # ALB-SYR dep 20:49 instead of 20:46
 retime(o,2054,1333) # SYR-ALB dep 22:13 instead of 22:10
 add(o,158,"ALB","SYR",1081,"V132-R158-ALB-SYR-EVENING")
 add(o,158,"SYR","ALB",1165,"V132-R158-SYR-ALB-EVENING")
 return o
cases={"R146_MCI_FSD_late":extension146,"R107_SYR_CAK_late":extension107,"R160_SYR_PWM_late":extension160,"R158_ALB_SYR_hold":extension158}
def metrics(c):
 return {"flights":len(c["legs"]),"targetRoutes":{str(route):[{"flight":x["flight"],"origin":x["origin"],"destination":x["destination"],"departure":x["departure"],"arrival":x["arrival"]} for x in sorted((y for y in c["legs"] if y["route"]==route),key=lambda z:z["sequenceWithinRoute"])] for route in (107,125,146,158,160,176)}}
def check(o):
 try:
  c=apply_optimization_overlay(base,o)
  s=validate_schedule(c);v=validate_operating_rules(c);n=validate_overnight_turns(c)
  p=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
  try:
   g=export_gate_schedule(c);gate="pass"
  except Exception as e:gate=f"{type(e).__name__}: {e}"
  passes=(s["status"]==n["status"]==p["status"]=="pass" and v["summary"]["effectiveErrorFindings"]==0 and gate=="pass")
  return passes,c,{"pass":passes,"structure":s["status"],"overnight":n["status"],"planning":p["status"],"operating":v["summary"],"gate":gate,"failedChecks":[{"id":x["id"],"findings":x.get("findings",[])[:5]} for x in v["checks"] if x["status"]=="fail"],"metrics":metrics(c)}
 except Exception as e:
  return False,None,{"pass":False,"exception":repr(e),"traceback":traceback.format_exc()[-2000:]}
results={}
for name,fn in cases.items():
 try:
  o=fn();ok,c,r=check(o);r["overlay"]=o;results[name]=r
  print(name,ok,r.get("gate"),r.get("exception"),[(x["id"],len(x["findings"])) for x in r.get("failedChecks",[])],flush=True)
  if ok:
   (out/(name+"_overlay.json")).write_text(json.dumps(o,indent=2)+"\n")
 except Exception as e:
  results[name]={"pass":False,"exception":repr(e)}
  print(name,"exception",repr(e),flush=True)
# Attempt a jointly compliant package only from independently compliant overlays.
successes=[(name,results[name]["overlay"]) for name in cases if results[name]["pass"]]
combined=proposal()
for name,o in successes:
 for k in ("retimeLegs","insertLegs","bankAssignmentReplacements","bankAssignmentsToAdd"):
  combined.setdefault(k,[]).extend(o.get(k,[]))
if successes:
 ok,c,r=check(combined)
 results["combined"]={**r,"included":[name for name,_ in successes],"overlay":combined}
 if ok:
  (out/"combined_overlay.json").write_text(json.dumps(combined,indent=2)+"\n")
  (out/"combined_canonical.json").write_text(json.dumps(c,indent=2)+"\n")
 print("combined",ok,"included",list(map(lambda x:x[0],successes)),"gate",r.get("gate"),flush=True)
(out/"candidate_results.json").write_text(json.dumps(results,indent=2)+"\n")
