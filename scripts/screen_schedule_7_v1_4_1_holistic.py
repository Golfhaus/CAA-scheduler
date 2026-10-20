"""R167 demand-relevant ALB BWI/PHF round trip and R108 bank shift screens."""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_1_draft/canonical_schedule.json").read_text())
byflight={l["flight"]:l for l in base["legs"]}
cases=[
 {"name":"R167 ALB-BWI-ALB morning turn","route":167,
 "retime":[(1749,309,353),(1754,613,657),(1672,720,791)],
 "insert":[("ALB","BWI",393,463),("BWI","ALB",503,573)],
 "bankassign":[(1,"arrival",None),(2,"departure",None)],
 "replace":[(1672,"departure","SYR-M12")]},
 {"name":"R167 ALB-PHF-ALB with PHF B2","route":167,
 "retime":[(1749,309,353),(1754,672,716),(1672,756,827)],
 "insert":[("ALB","PHF",418,505),("PHF","ALB",545,632)],
 "bankassign":[(1,"arrival","PHF-B2"),(2,"departure","PHF-B2")],
 "replace":[(1754,"arrival","SYR-M12"),(1672,"departure","SYR-M12")]},
 {"name":"R108 SYR-BTV departure into M12 then BTV-PHF-SYR","route":108,
 "remove":[1830],
 "retime":[(1826,765,817)],
 "insert":[("BTV","PHF",857,957),("PHF","SYR",997,1082)],
 "bankassign":[(1,"arrival",None),(2,"departure",None),(2,"arrival","SYR-M17")],
 "replace":[(1826,"departure","SYR-M12")]}
]
out=ROOT/"outputs/schedule_7_v1_4_1_utilization";out.mkdir(exist_ok=True,parents=True)
results=[]
for i,case in enumerate(cases):
 r={"name":case["name"],"route":case["route"],"scope":"read-only"}
 try:
  ov={"schemaVersion":"1.0.0","id":f"v141-holistic-{i}","baseSchedule":{"scheduleId":base["schedule"]["id"]},
  "schedule":base["schedule"],"removeLegs":[{"legId":byflight[f]["id"],"expectedRoute":case["route"]} for f in case.get("remove",[])],
  "retimeLegs":[],"insertLegs":[],"bankAssignmentsToAdd":[],"bankAssignmentReplacements":[]}
  for f,d,a in case["retime"]:
   l=byflight[f];assert l["route"]==case["route"]
   assert (l["arrivalMinute"]-l["departureMinute"])%1440==(a-d)%1440
   ov["retimeLegs"].append({"legId":l["id"],"expectedDepartureMinute":l["departureMinute"],
    "expectedArrivalMinute":l["arrivalMinute"],"departureMinute":d,"arrivalMinute":a})
  for k,(u,v,d,a) in enumerate(case["insert"],1):
   ov["insertLegs"].append({"id":f"V141-HOLISTIC-{i}-{k}","route":case["route"],
    "origin":u,"destination":v,"departureMinute":d,"arrivalMinute":a})
  for k,op,b in case["bankassign"]:
   if b:ov["bankAssignmentsToAdd"].append({"legId":ov["insertLegs"][k-1]["id"],"operation":op,"bankId":b})
  for f,op,b in case["replace"]:
   ov["bankAssignmentReplacements"].append({"legId":byflight[f]["id"],"operation":op,"bankId":b})
  c=apply_optimization_overlay(base,ov)
  s=validate_schedule(c);n=validate_overnight_turns(c)
  o=validate_operating_rules(c);p=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
  try:export_gate_schedule(c);gate="pass"
  except Exception as e:gate=f"{type(e).__name__}: {str(e)[:400]}"
  r.update(structural=s["status"],overnight=n["status"],planning=p["status"],gate=gate,
   operating=o["summary"],addedFlights=len(c["legs"])-len(base["legs"]),
   failed=[{"check":z["id"],"findings":z.get("findings",[])[:5]} for z in o["checks"] if z["status"]=="fail"])
  r["pass"]=s["status"]==n["status"]==p["status"]=="pass" and gate=="pass" and o["summary"]["effectiveErrorFindings"]==0
  r["overlay"]=ov
  if r["pass"]:(out/f"holistic_{i}_canonical.json").write_text(json.dumps(c)+"\n")
 except Exception as e:r.update(pass_=False,error=repr(e),trace=traceback.format_exc()[-550:])
 results.append(r)
(out/"holistic_screen.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps([{"name":r["name"],"pass":r.get("pass",False),"added":r.get("addedFlights"),
 "errors":r.get("operating",{}).get("effectiveErrorFindings"),"gate":r.get("gate"),
 "failed":[x["check"] for x in r.get("failed",[])],"error":r.get("error")} for r in results],indent=2))
