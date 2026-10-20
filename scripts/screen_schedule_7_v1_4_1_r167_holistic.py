"""Holistic R167 morning triangle alternatives on the current 1266-flight v1.4.1 draft.
No schedule mutation or publication; native validation on each variant.
"""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_1_draft/canonical_schedule.json").read_text())
assert len(base["legs"])==1266
byflight={x["flight"]:x for x in base["legs"]}
cases=[
 {"name":"ALB-PHF-SYR preserves 11:20 CAK","remove":[1754],
  "insert":[("ALB","PHF",434,517),("PHF","SYR",557,642)],
  "bank":[(1,"arrival","PHF-B2"),(2,"departure","PHF-B2"),(2,"arrival","SYR-B3")]},
 {"name":"ALB-PIT-SYR preserves 11:20 CAK","remove":[1754],
  "insert":[("ALB","PIT",434,494),("PIT","SYR",534,600)],
  "bank":[(2,"arrival","SYR-B3")]},
 {"name":"ALB-BTV-SYR preserves 11:20 CAK","remove":[1754],
  "insert":[("ALB","BTV",434,474),("BTV","SYR",514,566)],
  "bank":[(2,"arrival","SYR-M09")]},
 {"name":"ALB-BTV-ALB hold filler (low O-D)","remove":[],
  "insert":[("ALB","BTV",434,474),("BTV","ALB",514,554)],"bank":[]}
]
out=ROOT/"outputs/schedule_7_v1_4_1_utilization";out.mkdir(exist_ok=True,parents=True)
results=[]
for i,case in enumerate(cases):
 rec={"name":case["name"],"scope":"read-only R167 holistic candidate"}
 try:
  ov={"schemaVersion":"1.0.0","id":f"v141-r167-holistic-{i}",
    "baseSchedule":{"scheduleId":base["schedule"]["id"]},"schedule":base["schedule"],
    "removeLegs":[{"legId":byflight[n]["id"],"expectedRoute":167} for n in case["remove"]],
    "insertLegs":[],"bankAssignmentsToAdd":[]}
  for k,(a,b,d,arr) in enumerate(case["insert"],1):
   ov["insertLegs"].append({"id":f"V141-R167-HOLISTIC-{i}-{k}",
    "route":167,"origin":a,"destination":b,"departureMinute":d,"arrivalMinute":arr})
  for k,op,bank in case["bank"]:
   ov["bankAssignmentsToAdd"].append({"legId":ov["insertLegs"][k-1]["id"],"operation":op,"bankId":bank})
  c=apply_optimization_overlay(base,ov)
  s=validate_schedule(c);n=validate_overnight_turns(c);o=validate_operating_rules(c)
  p=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
  try:export_gate_schedule(c);gate="pass"
  except Exception as e:gate=f"{type(e).__name__}: {str(e)[:400]}"
  rec.update(structural=s["status"],overnight=n["status"],planning=p["status"],gate=gate,
   operating=o["summary"],addedFlights=len(c["legs"])-len(base["legs"]),
   failed=[{"check":x["id"],"findings":x.get("findings",[])[:5]} for x in o["checks"] if x["status"]=="fail"])
  rec["pass"]=s["status"]==n["status"]==p["status"]=="pass" and gate=="pass" and o["summary"]["effectiveErrorFindings"]==0
  if rec["pass"]:(out/f"r167_holistic_{i}_canonical.json").write_text(json.dumps(c)+"\n")
 except Exception as e:rec.update(pass_=False,error=repr(e),trace=traceback.format_exc()[-600:])
 results.append(rec)
(out/"r167_holistic_native.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps([{"name":r["name"],"pass":r.get("pass",False),
 "added":r.get("addedFlights"),"gate":r.get("gate"),
 "errors":r.get("operating",{}).get("effectiveErrorFindings"),
 "checks":[x["check"] for x in r.get("failed",[])],"error":r.get("error")} for r in results],indent=2))
