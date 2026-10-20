"""Screen CRJ200 v1.4.1 mid-day A-B-C and SYR bank-utilization alternatives.

Read-only. No accepted draft publication. Each candidate preserves route origin,
terminator and adjacent route-day handoffs, and uses native physical/operating checks.
"""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_0/canonical_schedule.json").read_text())
assert base["schedule"]["status"]=="released" and len(base["legs"])==1259
ids={l["flight"]:l for l in base["legs"]}
bankSpecs={"M09":{"id":"SYR-M09","hub":"SYR","startMinute":535,"endMinute":595},"M12":{"id":"SYR-M12","hub":"SYR","startMinute":715,"endMinute":775}}
cases=[
 {"name":"R105 MHT-BGR-SYR triangular return","route":105,"remove":[1839],
 "insert":[("MHT","BGR",615,675),("BGR","SYR",715,795)],
 "assign":[(2,"arrival","SYR-B4")]},
 {"name":"R107 ISP-ROC-SYR triangular return","route":107,"remove":[1893],
 "insert":[("ISP","ROC",613,678),("ROC","SYR",718,757)],"banks":["M12"],
 "assign":[(2,"arrival","SYR-M12")]},
 {"name":"R107 ISP-PIT-SYR triangular return","route":107,"remove":[1893],
 "insert":[("ISP","PIT",613,698),("PIT","SYR",738,804)],
 "assign":[(2,"arrival","SYR-B4")]},
 {"name":"R108 ORH-BTV-SYR triangular return","route":108,"remove":[1884],
 "insert":[("ORH","BTV",613,658),("BTV","SYR",698,750)],"banks":["M12"],
 "assign":[(2,"arrival","SYR-M12")]},
 {"name":"R167 ALB-BTV-SYR morning triangle","route":167,"remove":[1754],
 "insert":[("ALB","BTV",434,474),("BTV","SYR",514,566)],"banks":["M09"],
 "assign":[(2,"arrival","SYR-M09")]},
 {"name":"R162 early BDL, SYR-ROC-SYR productive turn","route":162,
 "retime":[(2102,501,555)],
 "insert":[("SYR","ROC",600,639),("ROC","SYR",679,718)],"banks":["M09","M12"],
 "replace":[(2102,"arrival","SYR-M09")],
 "assign":[(2,"arrival","SYR-M12")]},
 {"name":"R162 early BDL, SYR-BGR-SYR productive turn","route":162,
 "retime":[(2102,501,555)],
 "insert":[("SYR","BGR",600,680),("BGR","SYR",720,800)],"banks":["M09"],
 "replace":[(2102,"arrival","SYR-M09")],
 "assign":[(2,"arrival","SYR-B4")]},
 {"name":"R106 HPN-BWI-SYR morning triangle","route":106,"remove":[1854],
 "insert":[("HPN","BWI",609,679),("BWI","SYR",719,784)],"banks":["M12"],
 "assign":[(2,"arrival","SYR-M12")]},
]
out=ROOT/"outputs/schedule_7_v1_4_1_utilization";out.mkdir(parents=True,exist_ok=True)
results=[]
for num,case in enumerate(cases):
 report={"name":case["name"],"route":case["route"],"scope":"read-only screening"}
 try:
  ov={"schemaVersion":"1.0.0","id":f"v141-screen-{num}",
     "baseSchedule":{"scheduleId":base["schedule"]["id"]},
     "schedule":{**base["schedule"],"id":"schedule_7_v1_4_1_draft","version":"1.4.1-draft",
       "label":"Schedule 7, Version 1.4.1 draft","status":"draft"},
     "removeLegs":[{"legId":ids[f]["id"],"expectedRoute":case["route"]} for f in case.get("remove",[])],
     "retimeLegs":[],"insertLegs":[],"bankAssignmentsToAdd":[],
     "bankAssignmentReplacements":[]}
  for flight,d,a in case.get("retime",[]):
   leg=ids[flight];assert leg["route"]==case["route"]
   assert (leg["arrivalMinute"]-leg["departureMinute"])%1440==(a-d)%1440
   ov["retimeLegs"].append({"legId":leg["id"],
     "expectedDepartureMinute":leg["departureMinute"],"expectedArrivalMinute":leg["arrivalMinute"],
     "departureMinute":d,"arrivalMinute":a})
  for i,(u,v,d,a) in enumerate(case["insert"],1):
   ov["insertLegs"].append({"id":f"V141-R{case['route']}-SCREEN-{num}-{i}",
    "route":case["route"],"origin":u,"destination":v,"departureMinute":d,"arrivalMinute":a})
  for i,op,bank in case.get("assign",[]):
   ov["bankAssignmentsToAdd"].append({"legId":ov["insertLegs"][i-1]["id"],"operation":op,"bankId":bank})
  for f,op,bank in case.get("replace",[]):
   ov["bankAssignmentReplacements"].append({"legId":ids[f]["id"],"operation":op,"bankId":bank})
  if case.get("banks"):
   ov["hubBanksToAdd"]=[bankSpecs[n] for n in case["banks"]]
   ov["hubBankCountOverrides"]={"SYR":9+len(case["banks"])}
  schedule=apply_optimization_overlay(base,ov)
  structure=validate_schedule(schedule);overnight=validate_overnight_turns(schedule)
  operating=validate_operating_rules(schedule)
  planning=validate_planning_snapshot(reconstruct_planning_snapshot(schedule),schedule)
  try:export_gate_schedule(schedule);gate="pass"
  except Exception as exc:gate=f"{type(exc).__name__}: {str(exc)[:450]}"
  report.update(structural=structure["status"],overnight=overnight["status"],
    planning=planning["status"],gate=gate,
    operating=operating["summary"],changedFlights=len(schedule["legs"])-len(base["legs"]),
    failed=[{"check":x["id"],"findings":x.get("findings",[])[:5]} for x in operating["checks"] if x["status"]=="fail"])
  report["pass"]=structure["status"]==overnight["status"]==planning["status"]=="pass" and gate=="pass" and operating["summary"]["effectiveErrorFindings"]==0
  report["overlay"]=ov
  if report["pass"]:
   (out/f"screen_{num}_canonical.json").write_text(json.dumps(schedule)+"\n")
 except Exception as exc:report.update(pass_=False,error=repr(exc),trace=traceback.format_exc()[-550:])
 results.append(report)
(out/"initial_screen.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps([{"name":r["name"],"pass":r.get("pass",False),
 "errors":r.get("operating",{}).get("effectiveErrorFindings"),
 "gate":r.get("gate"),"failed":[x["check"] for x in r.get("failed",[])],
 "exception":r.get("error")} for r in results],indent=2))
