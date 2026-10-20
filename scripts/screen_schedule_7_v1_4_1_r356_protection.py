"""Read-only compensation for R162 earlier BDL return using CRJ700 R356."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
root=ROOT/"outputs/schedule_7_v1_4_1_utilization";root.mkdir(exist_ok=True,parents=True)
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_1_draft/canonical_schedule.json").read_text())
leg=next(x for x in base["legs"] if x["flight"]==2209)
assert (leg["route"],leg["departureMinute"],leg["arrivalMinute"])==(356,635,689)
overlay={"schemaVersion":"1.0.0","id":"v141-R356-BDL-PIE-connection-protection",
"baseSchedule":{"scheduleId":base["schedule"]["id"]},"schedule":base["schedule"],
"retimeLegs":[{"legId":leg["id"],"expectedDepartureMinute":635,"expectedArrivalMinute":689,
"departureMinute":605,"arrivalMinute":659}]}
c=apply_optimization_overlay(base,overlay)
s=validate_schedule(c);n=validate_overnight_turns(c)
o=validate_operating_rules(c);p=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
try:export_gate_schedule(c);gate="pass"
except Exception as e:gate=f"{type(e).__name__}: {str(e)[:400]}"
res={"scope":"read only, unreleased R356 compensation proposal","structure":s["status"],
"overnight":n["status"],"planning":p["status"],"gate":gate,"operating":o["summary"],
"failed":[{"check":x["id"],"findings":x.get("findings",[])[:7]} for x in o["checks"] if x["status"]=="fail"]}
res["pass"]=s["status"]==n["status"]==p["status"]=="pass" and gate=="pass" and o["summary"]["effectiveErrorFindings"]==0
res["overlay"]=overlay
(root/"r356_connection_protection.json").write_text(json.dumps(res,indent=2)+"\n")
if res["pass"]:(root/"r356_connection_protection_canonical.json").write_text(json.dumps(c)+"\n")
print(json.dumps({"pass":res["pass"],"gate":gate,"errors":o["summary"]["effectiveErrorFindings"],
"failed":[x["check"] for x in res["failed"]]},indent=2))
