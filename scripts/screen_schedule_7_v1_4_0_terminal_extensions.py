"""Screen terminal round-trip CRJ200 extensions without disturbing existing bank flights."""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads((ROOT/"data/schedules/schedule_7_v1_3_3/canonical_schedule.json").read_text())
cases=[
 (110,"LEX",("DAY","LEX",1235,1281),("LEX","DAY",1321,1367)),
 (110,"CRW",("DAY","CRW",1235,1287),("CRW","DAY",1327,1379)),
 (110,"FWA",("DAY","FWA",1235,1275),("FWA","DAY",1315,1355)),
 (110,"TOL",("DAY","TOL",1235,1279),("TOL","DAY",1319,1363)),
 (107,"DAY",("CAK","DAY",1286,1336),("DAY","CAK",1376,1426)),
 (107,"SYR",("CAK","SYR",1286,1357),("SYR","CAK",1397,1468)),
 (106,"SYR",("BTV","SYR",1267,1319),("SYR","BTV",1359,1411)),
 (160,"SYR",("PWM","SYR",1248,1316),("SYR","PWM",1376,1444)),
 (160,"BWI",("PWM","BWI",1248,1338),("BWI","PWM",1378,1468)),
 (160,"PHF",("PWM","PHF",1248,1349),("PHF","PWM",1389,1490))
]
results=[]
for route,market,one,two in cases:
    report={"route":route,"destination":market,"flights":[one,two],"kind":"late-terminator-two-leg-turn"}
    try:
        overlay={"id":f"v140-terminal-{route}-{market}",
            "baseSchedule":{"scheduleId":base["schedule"]["id"]},
            "schedule":base["schedule"],
            "insertLegs":[{"id":f"V140-R{route}-{market}-{i}","route":route,
                "origin":s,"destination":t,"departureMinute":d,"arrivalMinute":a}
                for i,(s,t,d,a) in enumerate((one,two),1)]}
        candidate=apply_optimization_overlay(base,overlay)
        structure=validate_schedule(candidate)
        overnight=validate_overnight_turns(candidate)
        operation=validate_operating_rules(candidate)
        planning=validate_planning_snapshot(reconstruct_planning_snapshot(candidate),candidate)
        try:export_gate_schedule(candidate);gate="pass"
        except Exception as e:gate=f"{type(e).__name__}: {str(e)[:350]}"
        report.update(structure=structure["status"],overnight=overnight["status"],
            planning=planning["status"],gate=gate,operating=operation["summary"],
            failed=[{"check":x["id"],"findings":x.get("findings",[])[:4]} for x in operation["checks"] if x["status"]=="fail"])
        report["pass"]=structure["status"]==overnight["status"]==planning["status"]=="pass" and operation["summary"]["effectiveErrorFindings"]==0 and gate=="pass"
    except Exception as e:report.update(pass_=False,error=repr(e),trace=traceback.format_exc()[-650:])
    results.append(report)
out=ROOT/"outputs/schedule_7_v1_4_0_utilization"
out.mkdir(parents=True,exist_ok=True)
(out/"terminal_extensions.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps([{"route":x["route"],"market":x["destination"],"pass":x.get("pass",False),"error":x.get("error"),"gate":x.get("gate"),"checks":[v["check"] for v in x.get("failed",[])]} for x in results],indent=2))
