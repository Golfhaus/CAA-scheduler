"""Read-only R108 holistic SYR midday-bank route rebuilds retaining evening BTV-RFD."""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_1_draft/canonical_schedule.json").read_text())
old={l["flight"]:l for l in base["legs"]}
cases=[
 {"name":"R108 ORH-SYR then SYR-ROC-SYR before BTV",
  "retime":[(1884,613,671),(1826,885,937)],
  "add":[("SYR","ROC",715,754),("ROC","SYR",794,833)],
  "assign":[(1,"departure","SYR-M12"),(2,"arrival","SYR-B4")],
  "replace":[(1884,"arrival","SYR-B3"),(1826,"departure","SYR-M15")]},
 {"name":"R108 ORH-SYR then SYR-PHF-SYR before BTV",
  "retime":[(1884,613,671),(1826,965,1017)],
  "add":[("SYR","PHF",715,800),("PHF","SYR",840,925)],
  "assign":[(1,"departure","SYR-M12"),(1,"arrival","PHF-B4"),
    (2,"departure","PHF-B4"),(2,"arrival","SYR-M15")],
  "replace":[(1884,"arrival","SYR-B3"),(1826,"departure","SYR-B5")]}
]
folder=ROOT/"outputs/schedule_7_v1_4_1_utilization";folder.mkdir(exist_ok=True,parents=True)
results=[]
for i,case in enumerate(cases):
 rec={"name":case["name"],"scope":"read-only v1.4.1 experiment"}
 try:
  ov={"schemaVersion":"1.0.0","id":f"v141-r108-bank-rebuild-{i}",
      "baseSchedule":{"scheduleId":base["schedule"]["id"]},"schedule":base["schedule"],
      "retimeLegs":[],"insertLegs":[],"bankAssignmentsToAdd":[],"bankAssignmentReplacements":[]}
  for number,dep,arr in case["retime"]:
   leg=old[number]
   assert (leg["arrivalMinute"]-leg["departureMinute"])%1440==(arr-dep)%1440
   ov["retimeLegs"].append({"legId":leg["id"],"expectedDepartureMinute":leg["departureMinute"],
    "expectedArrivalMinute":leg["arrivalMinute"],"departureMinute":dep,"arrivalMinute":arr})
  for seq,(u,v,d,a) in enumerate(case["add"],1):
   ov["insertLegs"].append({"id":f"V141-R108-BANK-{i}-{seq}","route":108,"origin":u,"destination":v,
     "departureMinute":d,"arrivalMinute":a})
  for seq,operation,bank in case["assign"]:
   ov["bankAssignmentsToAdd"].append({"legId":ov["insertLegs"][seq-1]["id"],"operation":operation,"bankId":bank})
  for number,operation,bank in case["replace"]:
   ov["bankAssignmentReplacements"].append({"legId":old[number]["id"],"operation":operation,"bankId":bank})
  c=apply_optimization_overlay(base,ov)
  s=validate_schedule(c);n=validate_overnight_turns(c);o=validate_operating_rules(c)
  p=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
  try:export_gate_schedule(c);g="pass"
  except Exception as e:g=f"{type(e).__name__}: {str(e)[:440]}"
  rec.update(structure=s["status"],overnight=n["status"],planning=p["status"],gate=g,
   operating=o["summary"],addedFlights=len(c["legs"])-len(base["legs"]),
   errors=[{"check":x["id"],"findings":x.get("findings",[])[:5]} for x in o["checks"] if x["status"]=="fail"])
  rec["pass"]=s["status"]==n["status"]==p["status"]=="pass" and g=="pass" and o["summary"]["effectiveErrorFindings"]==0
  rec["overlay"]=ov
  if rec["pass"]:(folder/f"r108_bank_{i}_canonical.json").write_text(json.dumps(c)+"\n")
 except Exception as e:rec.update(pass_=False,exception=repr(e),trace=traceback.format_exc()[-800:])
 results.append(rec)
(folder/"r108_bank_rebuild_screen.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps([{"name":x["name"],"pass":x.get("pass"),"gate":x.get("gate"),
 "errors":x.get("operating",{}).get("effectiveErrorFindings"),
 "checks":[v["check"] for v in x.get("errors",[])],"exception":x.get("exception")} for x in results],indent=2))
