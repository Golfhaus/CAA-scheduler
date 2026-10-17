"""Screen bank-aware replacement of late R160 and R107 sectors, no extra route days."""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.bank_placement import _block_minutes,_local_arrival
base=json.loads((ROOT/"outputs/schedule_7_v1_3_2_group_selected/canonical_schedule.json").read_text())
out=ROOT/"outputs/schedule_7_v1_3_2_terminal_rebuild";out.mkdir(parents=True,exist_ok=True)
cities={x["code"]:x for x in base["cities"]}
profile=next(x for x in json.loads((ROOT/"config/policies/planning_rules_v7.json").read_text())["frequencyAllocation"]["fleetProfiles"] if x["fleet"]=="CRJ200")
old={x["flight"]:x for x in base["legs"]};hubset=set(base["operatingPolicy"]["hubs"])
def block(a,b):return _block_minutes(a,b,profile,cities)
def bank(code,t):
 return next((b["id"] for b in base["hubBanks"] if b["hub"]==code and b["startMinute"]<=t<b["endMinute"]),None)
def build(route,original,origin,mid,dest,d):
 o={"baseSchedule":{"scheduleId":base["schedule"]["id"]},"schedule":base["schedule"],
 "removeLegs":[{"legId":old[flight]["id"],"expectedRoute":route} for flight in original]}
 for a,b in ((origin,mid),(mid,dest)):
  arrival=_local_arrival(d,block(a,b),a,b,cities)
  ident=f"V132-FINAL-{route}-{mid}-{a}-{b}"
  o.setdefault("insertLegs",[]).append({"id":ident,"route":route,"origin":a,"destination":b,"departureMinute":d,"arrivalMinute":arrival})
  for airport,op,t in [(a,"departure",d),(b,"arrival",arrival)]:
   if airport not in hubset:continue
   target=bank(airport,t)
   if not target:raise ValueError(f"{route} {mid} {airport} {op} off bank at {t}")
   o.setdefault("bankAssignmentsToAdd",[]).append({"legId":ident,"operation":op,"bankId":target})
  d=arrival+40
  if d>=1440:raise ValueError("next departure after midnight")
 return o
def make160(mid):
 return build(160,[1701],"SYR",mid,"PWM",1125)
def make107(mid):
 # Original BDL-SYR and SYR-CAK are reassigned into new two-sector route.
 # Reach PHF B7 at 20:05 or DAY B8 at 19:35.
 dest_arr=1205 if mid=="PHF" else 1175
 depart=dest_arr-block("BDL",mid)
 return build(107,[1791,1674],"BDL",mid,"CAK",depart)
cases={**{f"R160_SYR_{m}_PWM":lambda m=m:make160(m) for m in ["PHF","PIT","BDL"]},
 **{f"R107_BDL_{m}_CAK":lambda m=m:make107(m) for m in ["PHF","DAY"]}}
results={}
for key,fn in cases.items():
 try:
  overlay=fn();c=apply_optimization_overlay(base,overlay)
  structure=validate_schedule(c);op=validate_operating_rules(c);overnight=validate_overnight_turns(c)
  plan=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
  try:export_gate_schedule(c);gate="pass"
  except Exception as e:gate=repr(e)
  ok=structure["status"]==overnight["status"]==plan["status"]=="pass" and op["summary"]["effectiveErrorFindings"]==0 and gate=="pass"
  results[key]={"pass":ok,"operating":op["summary"],"structure":structure["status"],"overnight":overnight["status"],"planning":plan["status"],"gate":gate,"failChecks":[{"id":x["id"],"findings":x.get("findings",[])[:4]} for x in op["checks"] if x["status"]=="fail"],"overlay":overlay}
  if ok:
   (out/(key+"_canonical.json")).write_text(json.dumps(c,indent=2)+"\n")
   (out/(key+"_overlay.json")).write_text(json.dumps(overlay,indent=2)+"\n")
  print(key,ok,gate,[(x["id"],len(x["findings"])) for x in results[key]["failChecks"]],flush=True)
 except Exception as e:
  results[key]={"pass":False,"exception":repr(e),"traceback":traceback.format_exc()[-1500:]}
  print(key,"ERROR",repr(e),flush=True)
 (out/"physical_screen.json").write_text(json.dumps(results,indent=2)+"\n")
