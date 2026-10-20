"""Further v1.4.1 read-only utilization screens on latest provisional 1264-flight draft."""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_1_draft/canonical_schedule.json").read_text())
assert len(base["legs"])==1264
cases=[
 {"name":"R108 late SYR-BDL-SYR following ROC return","route":108,
  "legs":[("SYR","BDL",1334,1388),("BDL","SYR",1428,1482)],"bank":"SYR-B7"},
 {"name":"R108 late SYR-BTV-SYR following ROC return","route":108,
  "legs":[("SYR","BTV",1334,1386),("BTV","SYR",1426,1478)],"bank":"SYR-B7"},
 {"name":"R108 late SYR-ALB-SYR following ROC return","route":108,
  "legs":[("SYR","ALB",1334,1378),("ALB","SYR",1418,1462)],"bank":"SYR-B7"},
 {"name":"R107 CAK-PIT-CAK late extension","route":107,
  "legs":[("CAK","PIT",1286,1331),("PIT","CAK",1371,1416)]},
 {"name":"R167 ERI-BUF-ERI late extension","route":167,
  "legs":[("ERI","BUF",1328,1368),("BUF","ERI",1408,1448)]},
]
out=ROOT/"outputs/schedule_7_v1_4_1_utilization";out.mkdir(exist_ok=True,parents=True)
result=[]
for i,c in enumerate(cases):
 r={"name":c["name"],"route":c["route"],"scope":"READ ONLY; draft unchanged"}
 try:
  ov={"schemaVersion":"1.0.0","id":f"v141-followup-{i}",
    "baseSchedule":{"scheduleId":base["schedule"]["id"]},"schedule":base["schedule"],
    "insertLegs":[],"bankAssignmentsToAdd":[]}
  for n,(u,v,d,a) in enumerate(c["legs"],1):
   ov["insertLegs"].append({"id":f"V141-FOLLOWUP-R{c['route']}-{i}-{n}",
     "route":c["route"],"origin":u,"destination":v,"departureMinute":d,"arrivalMinute":a})
  if c.get("bank"):
   ov["bankAssignmentsToAdd"].append({"legId":ov["insertLegs"][0]["id"],"operation":"departure","bankId":c["bank"]})
  cand=apply_optimization_overlay(base,ov)
  s=validate_schedule(cand);n=validate_overnight_turns(cand)
  o=validate_operating_rules(cand);p=validate_planning_snapshot(reconstruct_planning_snapshot(cand),cand)
  try:export_gate_schedule(cand);gate="pass"
  except Exception as e:gate=f"{type(e).__name__}: {str(e)[:450]}"
  r.update(structural=s["status"],overnight=n["status"],planning=p["status"],gate=gate,
   operating=o["summary"],failed=[{"check":x["id"],"findings":x.get("findings",[])[:5]} for x in o["checks"] if x["status"]=="fail"])
  r["pass"]=s["status"]==n["status"]==p["status"]=="pass" and gate=="pass" and o["summary"]["effectiveErrorFindings"]==0
  if r["pass"]:(out/f"followup_{i}_canonical.json").write_text(json.dumps(cand)+"\n")
 except Exception as e:r.update(pass_=False,error=repr(e),trace=traceback.format_exc()[-600:])
 result.append(r)
(out/"followup_screen.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps([{"name":x["name"],"pass":x.get("pass",False),"gate":x.get("gate"),
 "errors":x.get("operating",{}).get("effectiveErrorFindings"),
 "failed":[y["check"] for y in x.get("failed",[])],"error":x.get("error")} for x in result],indent=2))
