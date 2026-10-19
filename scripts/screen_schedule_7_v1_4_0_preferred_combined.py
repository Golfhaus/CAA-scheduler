"""Combined native validation of preferred R160 and R107 P2P A-B-C candidates.
Read-only against accepted v1.4.0 draft. Candidate stays in outputs, not canonical.
"""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_0_draft/canonical_schedule.json").read_text())
assert len(base["legs"])==1257
screens=json.loads((ROOT/"outputs/schedule_7_v1_4_0_utilization/tactical_p2p_screen.json").read_text())
selected=["BTV-PHF-SYR tactical bank retiming","BDL-BUF-SYR A-B-C triangle"]
c=base
for name in selected:
 result=next(x for x in screens if x["name"]==name)
 assert result["pass"] is True
 c=apply_optimization_overlay(c,result["changes"])
assert len(c["legs"])==1259
assert len({x["route"] for x in c["legs"]})==188
assert len({x["line"] for x in c["legs"]})==17
s=validate_schedule(c);o=validate_operating_rules(c);n=validate_overnight_turns(c)
p=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
try:
 export_gate_schedule(c)
 gate="pass"
except Exception as exc:gate=repr(exc)
report={"scope":"READ-ONLY combined alternative, NOT IN ACCEPTED DRAFT",
"candidates":selected,"flights":len(c["legs"]),"routes":188,"lines":17,
"structural":s["status"],"overnight":n["status"],"planning":p["status"],
"gate":gate,"operating":o["summary"],
"failed":[{"id":x["id"],"findings":x.get("findings",[])[:8]} for x in o["checks"] if x["status"]=="fail"]}
report["pass"]=s["status"]==n["status"]==p["status"]=="pass" and gate=="pass" and o["summary"]["effectiveErrorFindings"]==0
out=ROOT/"outputs/schedule_7_v1_4_0_utilization"
(out/"preferred_combined_native.json").write_text(json.dumps(report,indent=2)+"\n")
if report["pass"]:
 (out/"preferred_combined_canonical.json").write_text(json.dumps(c,indent=2)+"\n")
print(json.dumps(report,indent=2))
