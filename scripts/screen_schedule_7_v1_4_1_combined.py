"""Co-validate promising v1.4.1 productive route changes, unpublished."""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
folder=ROOT/"outputs/schedule_7_v1_4_1_utilization"
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_0/canonical_schedule.json").read_text())
initial=json.loads((folder/"initial_screen.json").read_text())
extra=json.loads((folder/"supplemental_screen.json").read_text())
byname={}
for x in initial+extra:
 if x.get("pass"):byname[x["name"]]=x["overlay"]
names={
 "R162_BGR":"R162 early BDL, SYR-BGR-SYR productive turn",
 "R105_BGR":"R105 MHT earlier plus late BGR-SYR-BGR",
 "R107_PHF":"R107 ISP-PHF-SYR via PHF B3/B4 and SYR M15"
}
scenarios=[
 ["R162_BGR"],["R105_BGR"],["R107_PHF"],
 ["R162_BGR","R105_BGR"],
 ["R162_BGR","R107_PHF"],
 ["R105_BGR","R107_PHF"],
 ["R162_BGR","R105_BGR","R107_PHF"]]
out=[]
for keys in scenarios:
 name="_".join(keys)
 entry={"name":name,"scope":"unaccepted v1.4.1 feasibility","included":keys}
 try:
  ov={"schemaVersion":"1.0.0","id":f"v141-combined-{name}",
    "baseSchedule":{"scheduleId":base["schedule"]["id"]},
    "schedule":{**base["schedule"],"id":"schedule_7_v1_4_1_draft",
      "version":"1.4.1-draft","label":"Schedule 7 v1.4.1 draft","status":"draft"},
    "removeLegs":[],"retimeLegs":[],"insertLegs":[],
    "bankAssignmentsToAdd":[],"bankAssignmentReplacements":[],"hubBanksToAdd":[]}
  banks=set()
  for k in keys:
   piece=byname[names[k]]
   for fld in ("removeLegs","retimeLegs","insertLegs","bankAssignmentsToAdd","bankAssignmentReplacements"):
    ov[fld].extend(piece.get(fld,[]))
   for b in piece.get("hubBanksToAdd",[]):
    if b["id"] not in banks:
     banks.add(b["id"]);ov["hubBanksToAdd"].append(b)
  if banks:ov["hubBankCountOverrides"]={"SYR":base["operatingPolicy"]["hubBankCounts"]["SYR"]+len(banks)}
  assert len({l["legId"] for l in ov["retimeLegs"]})==len(ov["retimeLegs"])
  assert len({l["id"] for l in ov["insertLegs"]})==len(ov["insertLegs"])
  candidate=apply_optimization_overlay(base,ov)
  s=validate_schedule(candidate);n=validate_overnight_turns(candidate)
  o=validate_operating_rules(candidate);p=validate_planning_snapshot(reconstruct_planning_snapshot(candidate),candidate)
  try:export_gate_schedule(candidate);gate="pass"
  except Exception as e:gate=f"{type(e).__name__}: {str(e)[:300]}"
  entry.update(flights=len(candidate["legs"]),addedFlights=len(candidate["legs"])-len(base["legs"]),
   routes=len({l["route"] for l in candidate["legs"]}),lines=len({l["line"] for l in candidate["legs"]}),
   structural=s["status"],overnight=n["status"],planning=p["status"],gate=gate,
   operating=o["summary"],
   failures=[{"check":x["id"],"findings":x.get("findings",[])[:6]} for x in o["checks"] if x["status"]=="fail"])
  entry["pass"]=s["status"]==n["status"]==p["status"]=="pass" and gate=="pass" and o["summary"]["effectiveErrorFindings"]==0
  if entry["pass"]:
   (folder/f"combined_{name}_canonical.json").write_text(json.dumps(candidate)+"\n")
   entry["overlay"]=ov
 except Exception as e:entry.update(pass_=False,error=repr(e),trace=traceback.format_exc()[-500:])
 out.append(entry)
(folder/"combined_screen.json").write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps([{"name":x["name"],"pass":x.get("pass",False),
 "addedFlights":x.get("addedFlights"),"errors":x.get("operating",{}).get("effectiveErrorFindings"),
 "gate":x.get("gate"),"failures":[y["check"] for y in x.get("failures",[])],
 "error":x.get("error")} for x in out],indent=2))
