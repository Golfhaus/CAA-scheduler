"""Holistic R158 evening market replacement, against 1,227-flight selected draft.

Retains GRR-DAY-LEX-DAY-SYR-ALB; replaces low-demand ALB-SYR-ALB late
turn with demand-tested round trips from ALB, retaining ALB RON.
"""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.bank_placement import _block_minutes,_local_arrival
base=json.loads((ROOT/"outputs/schedule_7_v1_3_2_selected/canonical_schedule.json").read_text())
out=ROOT/"outputs/schedule_7_v1_3_2_r158_rebuild";out.mkdir(parents=True,exist_ok=True)
cities={c["code"]:c for c in base["cities"]}
profile=next(x for x in json.loads((ROOT/"config/policies/planning_rules_v7.json").read_text())["frequencyAllocation"]["fleetProfiles"] if x["fleet"]=="CRJ200")
old={x["flight"]:x for x in base["legs"]}
hubset=set(base["operatingPolicy"]["hubs"])
def bank(city,minute):
 return next((b["id"] for b in base["hubBanks"] if b["hub"]==city and b["startMinute"]<=minute<b["endMinute"]),None)
def scenario(dest,depart=1089):
 cfg={"baseSchedule":{"scheduleId":base["schedule"]["id"]},"schedule":base["schedule"],
 "removeLegs":[{"legId":old[f]["id"],"expectedRoute":158} for f in [2053,2054]]}
 t=depart
 for a,b in [("ALB",dest),(dest,"ALB")]:
  ar=_local_arrival(t,_block_minutes(a,b,profile,cities),a,b,cities)
  ident=f"V132-R158-{dest}-{a}-{b}"
  cfg.setdefault("insertLegs",[]).append({"id":ident,"route":158,"origin":a,"destination":b,"departureMinute":t,"arrivalMinute":ar})
  for city,op,minute in [(a,"departure",t),(b,"arrival",ar)]:
   if city not in hubset:continue
   target=bank(city,minute)
   if target is None:raise ValueError(f"{dest}: {city} {op} {minute} outside bank")
   cfg.setdefault("bankAssignmentsToAdd",[]).append({"legId":ident,"operation":op,"bankId":target})
  t=ar+40
 return cfg
cases={"ALB_BWI":("BWI",1089),"ALB_RDU":("RDU",1089),"ALB_PIT":("PIT",1089),"ALB_PHF":("PHF",1119)}
results={}
for key,params in cases.items():
 try:
  overlay=scenario(*params);candidate=apply_optimization_overlay(base,overlay)
  structure=validate_schedule(candidate);operating=validate_operating_rules(candidate)
  overnight=validate_overnight_turns(candidate)
  plan=validate_planning_snapshot(reconstruct_planning_snapshot(candidate),candidate)
  try:export_gate_schedule(candidate);gate="pass"
  except Exception as e:gate=repr(e)
  ok=structure["status"]==overnight["status"]==plan["status"]=="pass" and operating["summary"]["effectiveErrorFindings"]==0 and gate=="pass"
  results[key]={"pass":ok,"operating":operating["summary"],"structure":structure["status"],"overnight":overnight["status"],"planning":plan["status"],"gate":gate,
   "failChecks":[{"id":x["id"],"findings":x.get("findings",[])[:4]} for x in operating["checks"] if x["status"]=="fail"],"overlay":overlay}
  if ok:
   (out/(key+"_canonical.json")).write_text(json.dumps(candidate,indent=2)+"\n")
   (out/(key+"_overlay.json")).write_text(json.dumps(overlay,indent=2)+"\n")
  print(key,ok,gate,[(x["id"],len(x["findings"])) for x in results[key]["failChecks"]],flush=True)
 except Exception as e:
  results[key]={"pass":False,"exception":repr(e),"traceback":traceback.format_exc()[-1200:]}
  print(key,"ERROR",repr(e),flush=True)
 (out/"physical_screen.json").write_text(json.dumps(results,indent=2)+"\n")
