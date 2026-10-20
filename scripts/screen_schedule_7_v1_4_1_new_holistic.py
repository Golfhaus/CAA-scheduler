"""Screen holistic R108 and R167 morning A-B-C paths against provisional v1.4.1."""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_1_draft/canonical_schedule.json").read_text())
assert base["schedule"]["id"]=="schedule_7_v1_4_1_draft"
old={x["flight"]:x for x in base["legs"]}
cases=[
 {"name":"R108 ORH-PHF-SYR morning connector","route":108,"remove":[1884],
  "insert":[("ORH","PHF",613,703),("PHF","SYR",743,828)],
  "retime":[(1826,885,937)],
  "assign":[(1,"arrival","PHF-B3"),(2,"departure","PHF-M12-V141"),(2,"arrival","SYR-B4")],
  "replace":[(1826,"departure","SYR-M15")]},
 {"name":"R167 ALB-BWI-SYR morning connector","route":167,"remove":[1754],
  "insert":[("ALB","BWI",434,504),("BWI","SYR",544,609)],
  "banks":[{"id":"SYR-M10-V141","hub":"SYR","startMinute":585,"endMinute":645}],
  "assign":[(2,"arrival","SYR-M10-V141")]},
 {"name":"R167 ALB-BWI-SYR later morning connector","route":167,"remove":[1754],
  "insert":[("ALB","BWI",445,515),("BWI","SYR",555,620)],
  "banks":[{"id":"SYR-M10-V141","hub":"SYR","startMinute":585,"endMinute":645}],
  "assign":[(2,"arrival","SYR-M10-V141")]}
]
out=ROOT/"outputs/schedule_7_v1_4_1_utilization";out.mkdir(parents=True,exist_ok=True)
result=[]
for i,case in enumerate(cases):
 r={"name":case["name"],"route":case["route"],"status":"read-only"}
 try:
  ov={"schemaVersion":"1.0.0","id":f"v141-holistic-morning-{i}","baseSchedule":{"scheduleId":base["schedule"]["id"]},
   "schedule":base["schedule"],
   "removeLegs":[{"legId":old[f]["id"],"expectedRoute":case["route"]} for f in case["remove"]],
   "insertLegs":[],"bankAssignmentsToAdd":[],"retimeLegs":[],"bankAssignmentReplacements":[]}
  for k,(u,v,d,a) in enumerate(case["insert"],1):
   ov["insertLegs"].append({"id":f"V141-R{case['route']}-HOLISTIC-{i}-{k}",
    "route":case["route"],"origin":u,"destination":v,"departureMinute":d,"arrivalMinute":a})
  for k,op,bank in case.get("assign",[]):
   ov["bankAssignmentsToAdd"].append({"legId":ov["insertLegs"][k-1]["id"],"operation":op,"bankId":bank})
  for f,d,a in case.get("retime",[]):
   leg=old[f]
   assert (leg["arrivalMinute"]-leg["departureMinute"])%1440==(a-d)%1440
   ov["retimeLegs"].append({"legId":leg["id"],"expectedDepartureMinute":leg["departureMinute"],
      "expectedArrivalMinute":leg["arrivalMinute"],"departureMinute":d,"arrivalMinute":a})
  for f,op,bank in case.get("replace",[]):
   ov["bankAssignmentReplacements"].append({"legId":old[f]["id"],"operation":op,"bankId":bank})
  if "banks" in case:
   ov["hubBanksToAdd"]=case["banks"]
   ov["hubBankCountOverrides"]={"SYR":base["operatingPolicy"]["hubBankCounts"]["SYR"]+len(case["banks"])}
  c=apply_optimization_overlay(base,ov)
  structure=validate_schedule(c);overnight=validate_overnight_turns(c)
  operating=validate_operating_rules(c)
  planning=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
  try:export_gate_schedule(c);gate="pass"
  except Exception as e:gate=f"{type(e).__name__}: {str(e)[:350]}"
  r.update(structure=structure["status"],overnight=overnight["status"],planning=planning["status"],
    gate=gate,operating=operating["summary"],deltaFlights=len(c["legs"])-len(base["legs"]),
    failures=[{"check":v["id"],"findings":v.get("findings",[])[:5]} for v in operating["checks"] if v["status"]=="fail"])
  r["pass"]=structure["status"]==overnight["status"]==planning["status"]=="pass" and gate=="pass" and operating["summary"]["effectiveErrorFindings"]==0
  r["overlay"]=ov
  if r["pass"]:(out/f"new_holistic_{i}_canonical.json").write_text(json.dumps(c)+"\n")
 except Exception as e:r.update(pass_=False,error=repr(e),trace=traceback.format_exc()[-500:])
 result.append(r)
(out/"new_holistic_screen.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps([{"name":x["name"],"pass":x.get("pass"),"gate":x.get("gate"),
 "errors":x.get("operating",{}).get("effectiveErrorFindings"),
 "failed":[z["check"] for z in x.get("failures",[])],"error":x.get("error")} for x in result],indent=2))
