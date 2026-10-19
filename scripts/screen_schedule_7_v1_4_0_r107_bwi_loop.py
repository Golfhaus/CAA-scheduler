"""Evaluate R107 SYR-BWI-BDL-SYR A-B loop replacing current SYR-BDL-SYR."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_0_draft/canonical_schedule.json").read_text())
old={l["flight"]:l for l in base["legs"]}
assert old[1792]["route"]==old[1791]["route"]==107
ov={"schemaVersion":"1.0.0","id":"v140-r107-syr-bwi-bdl-syr",
"baseSchedule":{"scheduleId":base["schedule"]["id"]},"schedule":base["schedule"],
"removeLegs":[{"legId":old[n]["id"],"expectedRoute":107} for n in (1792,1791)],
"insertLegs":[
 {"id":"V140-R107-SYR-BWI","route":107,"origin":"SYR","destination":"BWI","departureMinute":845,"arrivalMinute":910},
 {"id":"V140-R107-BWI-BDL","route":107,"origin":"BWI","destination":"BDL","departureMinute":950,"arrivalMinute":1020},
 {"id":"V140-R107-BDL-SYR","route":107,"origin":"BDL","destination":"SYR","departureMinute":1071,"arrivalMinute":1125}],
"bankAssignmentsToAdd":[
 {"legId":"V140-R107-SYR-BWI","operation":"departure","bankId":"SYR-B4"},
 {"legId":"V140-R107-BDL-SYR","operation":"arrival","bankId":"SYR-B6"}]}
c=apply_optimization_overlay(base,ov)
s=validate_schedule(c);o=validate_operating_rules(c);n=validate_overnight_turns(c);p=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
try:export_gate_schedule(c);g="pass"
except Exception as e:g=f"{type(e).__name__}: {str(e)[:400]}"
report={"scope":"READ-ONLY, NOT in draft","description":"Keep BDL-SYR direct return; use SYR-BWI-BDL A-B outbound routing",
"flights":len(c["legs"]),"gate":g,"structural":s["status"],"overnight":n["status"],"planning":p["status"],
"operating":o["summary"],"failed":[{"check":x["id"],"findings":x.get("findings",[])[:6]} for x in o["checks"] if x["status"]=="fail"]}
report["pass"]=s["status"]==n["status"]==p["status"]=="pass" and g=="pass" and o["summary"]["effectiveErrorFindings"]==0
root=ROOT/"outputs/schedule_7_v1_4_0_utilization"
(root/"r107_bwi_bdl_loop_native.json").write_text(json.dumps(report,indent=2)+"\n")
if report["pass"]:(root/"r107_bwi_bdl_loop_canonical.json").write_text(json.dumps(c)+"\n")
print(json.dumps(report,indent=2))
