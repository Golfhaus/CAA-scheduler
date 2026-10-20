"""Read-only R167 1.4.1 holistic morning ALB roundtrip alternatives, preserve evening ERI."""
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
byf={x["flight"]:x for x in base["legs"]}
cases=[
 {"name":"R167 ALB-BWI-ALB and SYR M12 CAK retime",
  "retime":[(1749,309,353),(1754,623,667),(1672,755,826)],
  "add":[("ALB","BWI",393,468),("BWI","ALB",508,583)],
  "bank":[(1672,"departure","SYR-M12")]},
 {"name":"R167 ALB-PIT-ALB and SYR M12 CAK retime",
  "retime":[(1749,309,353),(1754,605,649),(1672,755,826)],
  "add":[("ALB","PIT",393,459),("PIT","ALB",499,565)],
  "bank":[(1672,"departure","SYR-M12")]},
 {"name":"R167 ALB-PIT-SYR triangular return into B3",
  "remove":[1754],
  "add":[("ALB","PIT",434,500),("PIT","SYR",573,639)],
  "newbank":[(2,"arrival","SYR-B3")]},
 {"name":"R167 ALB-PWM-SYR triangular return into B3",
  "remove":[1754],
  "add":[("ALB","PWM",434,494),("PWM","SYR",571,639)],
  "newbank":[(2,"arrival","SYR-B3")]}
]
out=ROOT/"outputs/schedule_7_v1_4_1_utilization";out.mkdir(exist_ok=True,parents=True)
results=[]
for i,x in enumerate(cases):
 r={"name":x["name"],"route":167,"scope":"read-only"}
 try:
  ov={"schemaVersion":"1.0.0","id":f"v141-r167-holistic-followup-{i}",
  "baseSchedule":{"scheduleId":base["schedule"]["id"]},"schedule":base["schedule"],
  "retimeLegs":[],"insertLegs":[],"removeLegs":[{"legId":byf[n]["id"],"expectedRoute":167} for n in x.get("remove",[])],
  "bankAssignmentsToAdd":[],"bankAssignmentReplacements":[]}
  for flight,dep,arr in x.get("retime",[]):
   l=byf[flight]
   assert l["route"]==167 and (l["arrivalMinute"]-l["departureMinute"]+1440)%1440==(arr-dep+1440)%1440
   ov["retimeLegs"].append({"legId":l["id"],"expectedDepartureMinute":l["departureMinute"],"expectedArrivalMinute":l["arrivalMinute"],
    "departureMinute":dep,"arrivalMinute":arr})
  for n,(origin,destination,departure,arrival) in enumerate(x["add"],1):
   ov["insertLegs"].append({"id":f"V141-R167-ROUND-{i}-{n}","route":167,
   "origin":origin,"destination":destination,"departureMinute":departure,"arrivalMinute":arrival})
  for flight,operation,bank in x.get("bank",[]):
   ov["bankAssignmentReplacements"].append({"legId":byf[flight]["id"],"operation":operation,"bankId":bank})
  for n,op,bank in x.get("newbank",[]):
   ov["bankAssignmentsToAdd"].append({"legId":ov["insertLegs"][n-1]["id"],"operation":op,"bankId":bank})
  candidate=apply_optimization_overlay(base,ov)
  s=validate_schedule(candidate);n=validate_overnight_turns(candidate);o=validate_operating_rules(candidate)
  p=validate_planning_snapshot(reconstruct_planning_snapshot(candidate),candidate)
  try:export_gate_schedule(candidate);g="pass"
  except Exception as e:g=f"{type(e).__name__}: {str(e)[:450]}"
  r.update(structural=s["status"],overnight=n["status"],planning=p["status"],gate=g,operating=o["summary"],
   addedFlights=len(candidate["legs"])-len(base["legs"]),
   failed=[{"check":z["id"],"findings":z.get("findings",[])[:6]} for z in o["checks"] if z["status"]=="fail"])
  r["pass"]=s["status"]==n["status"]==p["status"]=="pass" and g=="pass" and o["summary"]["effectiveErrorFindings"]==0
  if r["pass"]:
   (out/f"r167_followup_{i}_canonical.json").write_text(json.dumps(candidate)+"\n")
   r["overlay"]=ov
 except Exception as e:r.update(pass_=False,error=repr(e),trace=traceback.format_exc()[-650:])
 results.append(r)
(out/"r167_followup_native.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps([{"name":x["name"],"pass":x.get("pass",False),"added":x.get("addedFlights"),
 "errors":x.get("operating",{}).get("effectiveErrorFindings"),"gate":x.get("gate"),
 "checks":[y["check"] for y in x.get("failed",[])],"exception":x.get("error")} for x in results],indent=2))
