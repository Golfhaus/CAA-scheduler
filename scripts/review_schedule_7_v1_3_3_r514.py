"""Screen v1.3.3 R514 midday PIE-MCI-PIE substitute for PIE-SYR-PIE.

Base is the released v1.3.2 canonical. Does not publish or amend main.
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
base=json.loads((ROOT/"data/schedules/schedule_7_v1_3_2/canonical_schedule.json").read_text())
assert base["schedule"]["id"]=="schedule_7_v1_3_2" and len(base["legs"])==1229
out=ROOT/"outputs/schedule_7_v1_3_3_pie_review";out.mkdir(exist_ok=True,parents=True)
old={x["flight"]:x for x in base["legs"]}
cities={x["code"]:x for x in base["cities"]}
profile=next(x for x in json.loads((ROOT/"config/policies/planning_rules_v7.json").read_text())["frequencyAllocation"]["fleetProfiles"] if x["fleet"]=="CRJ900")
def bank(code,minute):
 return next((x["id"] for x in base["hubBanks"] if x["hub"]==code and x["startMinute"]<=minute<x["endMinute"]),None)
def overlay(pie_out,mci_back):
 result={"schemaVersion":"1.0.0","id":f"schedule-7-v1.3.3-r514-pie-mci-{pie_out}-{mci_back}",
 "baseSchedule":{"scheduleId":"schedule_7_v1_3_2"},"schedule":{**base["schedule"],"id":"schedule_7_v1_3_3_draft","version":"1.3.3-draft","label":"Schedule 7, Version 1.3.3 draft","status":"draft"},
 "removeLegs":[{"legId":old[1230]["id"],"expectedRoute":514},{"legId":old[1227]["id"],"expectedRoute":514}]}
 mci_arr=_local_arrival(pie_out,_block_minutes("PIE","MCI",profile,cities),"PIE","MCI",cities)
 pie_arr=_local_arrival(mci_back,_block_minutes("MCI","PIE",profile,cities),"MCI","PIE",cities)
 assert (mci_back-mci_arr)>=40 
 assert pie_out>=old[1172]["arrivalMinute"]+40
 assert old[2129]["departureMinute"]-pie_arr>=40
 for a,b,d,arr in [("PIE","MCI",pie_out,mci_arr),("MCI","PIE",mci_back,pie_arr)]:
  ident=f"V133-R514-{a}-{b}"
  result.setdefault("insertLegs",[]).append({"id":ident,"route":514,"origin":a,"destination":b,"departureMinute":d,"arrivalMinute":arr})
  for code,op,t in [(a,"departure",d),(b,"arrival",arr)]:
   if code in base["operatingPolicy"]["hubs"]:
    target=bank(code,t)
    if not target:raise ValueError(f"off bank {code} {op} {t}")
    result.setdefault("bankAssignmentsToAdd",[]).append({"legId":ident,"operation":op,"bankId":target})
 return result
results={}
for dep in [715,720,730]:
 for ret in [884,895,905]:
  name=f"r514_{dep}_{ret}"
  try:
   o=overlay(dep,ret);c=apply_optimization_overlay(base,o)
   s=validate_schedule(c);v=validate_operating_rules(c);n=validate_overnight_turns(c)
   p=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
   try:g=export_gate_schedule(c);gate="pass"
   except Exception as e:gate=repr(e)
   pass_all=s["status"]==n["status"]==p["status"]=="pass" and v["summary"]["effectiveErrorFindings"]==0 and gate=="pass"
   results[name]={"pass":pass_all,"structure":s["status"],"overnight":n["status"],"planning":p["status"],"operating":v["summary"],"gate":gate,"failed":[{"id":x["id"],"count":len(x["findings"]),"examples":x["findings"][:2]}for x in v["checks"]if x["status"]=="fail"],
    "overlay":o,"flights":[{"flight":l["flight"],"from":l["origin"],"to":l["destination"],"dep":l["departure"],"arr":l["arrival"]}for l in sorted([l for l in c["legs"] if l["route"]==514],key=lambda l:l["sequenceWithinRoute"])]}
   if pass_all:
    (out/(name+"_canonical.json")).write_text(json.dumps(c,indent=2)+"\n")
    (out/(name+"_overlay.json")).write_text(json.dumps(o,indent=2)+"\n")
   print(name,"PASS"if pass_all else"FAIL",gate,[(x["id"],x["count"]) for x in results[name]["failed"]],flush=True)
  except Exception as e:
   results[name]={"pass":False,"error":repr(e),"trace":traceback.format_exc()[-1000:]}
   print(name,"ERROR",repr(e),flush=True)
  (out/"r514_physical_screen.json").write_text(json.dumps(results,indent=2)+"\n")
