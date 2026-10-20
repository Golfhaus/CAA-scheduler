"""Read-only minor productive turns retaining key R167/R108 hub connections."""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_0/canonical_schedule.json").read_text())
old={x["flight"]:x for x in base["legs"]}
cases=[
 {"name":"R167 ALB-BTV-ALB inserted during morning ALB hold","route":167,
 "insert":[("ALB","BTV",434,474),("BTV","ALB",514,554)]},
 {"name":"R108 BTV-ROC-SYR instead of BTV-SYR","route":108,
 "remove":[1830],"insert":[("BTV","ROC",937,1002),("ROC","SYR",1042,1081)],
 "assign":[(2,"arrival","SYR-M17")]},
 {"name":"R108 BTV-BUF-SYR instead of BTV-SYR","route":108,
 "remove":[1830],"insert":[("BTV","BUF",937,1012),("BUF","SYR",1079,1125)],
 "assign":[(2,"arrival","SYR-B6")]},
 {"name":"R108 BTV-PWM-SYR instead of BTV-SYR","route":108,
 "remove":[1830],"insert":[("BTV","PWM",937,992),("PWM","SYR",1057,1125)],
 "assign":[(2,"arrival","SYR-B6")]}
]
out=ROOT/"outputs/schedule_7_v1_4_1_utilization";out.mkdir(parents=True,exist_ok=True)
results=[]
for i,case in enumerate(cases):
 r={"name":case["name"],"route":case["route"],"scope":"read-only"}
 try:
  ov={"schemaVersion":"1.0.0","id":f"v141-additional-{i}","baseSchedule":{"scheduleId":base["schedule"]["id"]},
   "schedule":{**base["schedule"],"id":"schedule_7_v1_4_1_draft","version":"1.4.1-draft","label":"Schedule 7 v1.4.1 draft","status":"draft"},
   "removeLegs":[{"legId":old[n]["id"],"expectedRoute":case["route"]} for n in case.get("remove",[])],
   "insertLegs":[],"bankAssignmentsToAdd":[]}
  for k,(u,v,d,a) in enumerate(case["insert"],1):
   ov["insertLegs"].append({"id":f"V141-R{case['route']}-ADDITIONAL-{i}-{k}",
    "route":case["route"],"origin":u,"destination":v,"departureMinute":d,"arrivalMinute":a})
  for k,op,bank in case.get("assign",[]):
   ov["bankAssignmentsToAdd"].append({"legId":ov["insertLegs"][k-1]["id"],"operation":op,"bankId":bank})
  c=apply_optimization_overlay(base,ov)
  s=validate_schedule(c);n=validate_overnight_turns(c)
  o=validate_operating_rules(c);p=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
  try:export_gate_schedule(c);g="pass"
  except Exception as e:g=f"{type(e).__name__}: {str(e)[:400]}"
  r.update(structural=s["status"],overnight=n["status"],planning=p["status"],
   gate=g,operating=o["summary"],flightsAdded=len(c["legs"])-len(base["legs"]),
   failed=[{"check":x["id"],"findings":x.get("findings",[])[:5]} for x in o["checks"] if x["status"]=="fail"])
  r["pass"]=s["status"]==n["status"]==p["status"]=="pass" and g=="pass" and o["summary"]["effectiveErrorFindings"]==0
  r["overlay"]=ov
  if r["pass"]:(out/f"additional_{i}_canonical.json").write_text(json.dumps(c)+"\n")
 except Exception as e:r.update(pass_=False,error=repr(e),trace=traceback.format_exc()[-550:])
 results.append(r)
(out/"additional_screen.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps([{"name":r["name"],"pass":r.get("pass",False),"added":r.get("flightsAdded"),
 "errors":r.get("operating",{}).get("effectiveErrorFindings"),"gate":r.get("gate"),
 "failed":[x["check"] for x in r.get("failed",[])],"error":r.get("error")} for r in results],indent=2))
