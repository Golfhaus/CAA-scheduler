"""Late-bank aligned recovery candidates preserving fixed curfews and pairing times."""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
b=json.loads((ROOT/"data/schedules/schedule_7_v1_3_3/canonical_schedule.json").read_text())
byflight={l["flight"]:l for l in b["legs"]}
cases=[
 {"name":"106 BTV-SYR-BTV late, earlier terminator","route":106,"retime":[(1856,1071,1125),(1827,1165,1217)],
  "extra":[("BTV","SYR",1257,1309),("SYR","BTV",1349,1401)],
  "banks":[(1,"arrival","SYR-B7"),(2,"departure","SYR-B7")]},
 {"name":"110 DAY-BHM-DAY late focus turn","route":110,"retime":[],
  "extra":[("DAY","BHM",1222,1253),("BHM","DAY",1293,1444)],
  "banks":[(1,"departure","DAY-B8")]},
 {"name":"110 DAY-SYR-DAY late hub turn","route":110,"retime":[(1794,1119,1176)],
  "extra":[("DAY","SYR",1216,1309),("SYR","DAY",1349,1442)],
  "banks":[(1,"departure","DAY-B8"),(1,"arrival","SYR-B7"),(2,"departure","SYR-B7")]},
]
results=[]
for case in cases:
 report={"name":case["name"],"route":case["route"],"scope":"read-only"}
 try:
    n=case["route"]
    overlay={"id":f"v140-banked-{n}-{len(results)}","baseSchedule":{"scheduleId":b["schedule"]["id"]},"schedule":b["schedule"],
      "retimeLegs":[],"insertLegs":[],"bankAssignmentsToAdd":[]}
    for f,d,a in case["retime"]:
      l=byflight[f]
      assert l["route"]==n
      assert (l["arrivalMinute"]-l["departureMinute"])%1440==(a-d)%1440
      overlay["retimeLegs"].append({"legId":l["id"],"expectedDepartureMinute":l["departureMinute"],"expectedArrivalMinute":l["arrivalMinute"],"departureMinute":d,"arrivalMinute":a})
    for i,(u,v,d,a) in enumerate(case["extra"],1):
      overlay["insertLegs"].append({"id":f"V140-R{n}-LATE-{len(results)}-{i}","route":n,"origin":u,"destination":v,"departureMinute":d,"arrivalMinute":a})
    for i,op,bank in case["banks"]:
      overlay["bankAssignmentsToAdd"].append({"legId":overlay["insertLegs"][i-1]["id"],"operation":op,"bankId":bank})
    c=apply_optimization_overlay(b,overlay)
    s=validate_schedule(c);o=validate_operating_rules(c);n=validate_overnight_turns(c)
    p=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
    try:export_gate_schedule(c);g="pass"
    except Exception as e:g=f"{type(e).__name__}: {str(e)[:400]}"
    report.update(structure=s["status"],overnight=n["status"],planning=p["status"],gate=g,operating=o["summary"],
      failed=[{"check":x["id"],"findings":x.get("findings",[])[:8]} for x in o["checks"] if x["status"]=="fail"])
    report["pass"]=s["status"]==n["status"]==p["status"]=="pass" and o["summary"]["effectiveErrorFindings"]==0 and g=="pass"
    report["overlay"]=overlay
 except Exception as e:report.update(pass_=False,error=repr(e),trace=traceback.format_exc()[-800:])
 results.append(report)
out=ROOT/"outputs/schedule_7_v1_4_0_utilization"
out.mkdir(parents=True,exist_ok=True)
(out/"late_bank_alignment.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps([{"name":x["name"],"pass":x.get("pass",False),"errors":x.get("operating",{}).get("effectiveErrorFindings"),"gate":x.get("gate"),"failedChecks":[z["check"] for z in x.get("failed",[])],"exception":x.get("error")} for x in results],indent=2))
