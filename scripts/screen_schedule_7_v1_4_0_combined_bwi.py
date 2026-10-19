"""Combined read-only v1.4 R160 PHF and R107 BWI-BDL loop native validation."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
folder=ROOT/"outputs/schedule_7_v1_4_0_utilization"
base=json.loads((folder/"r107_bwi_bdl_loop_canonical.json").read_text())
r160=next(x for x in json.loads((folder/"tactical_p2p_screen.json").read_text()) if x["name"].startswith("BTV-PHF"))
assert r160["pass"]
c=apply_optimization_overlay(base,r160["changes"])
assert len(c["legs"])==1259
s=validate_schedule(c);o=validate_operating_rules(c);n=validate_overnight_turns(c);p=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
try:export_gate_schedule(c);g="pass"
except Exception as e:g=f"{type(e).__name__}: {str(e)[:400]}"
report={"scope":"READ ONLY, NOT IN DRAFT","flights":len(c["legs"]),"routes":len({x["route"] for x in c["legs"]}),"lines":len({x["line"] for x in c["legs"]}),
"structural":s["status"],"overnight":n["status"],"planning":p["status"],"gate":g,
"operating":o["summary"],"failed":[{"check":x["id"],"findings":x.get("findings",[])[:6]} for x in o["checks"] if x["status"]=="fail"]}
report["pass"]=s["status"]==n["status"]==p["status"]=="pass" and g=="pass" and o["summary"]["effectiveErrorFindings"]==0
(folder/"r160_r107_bwi_combined_native.json").write_text(json.dumps(report,indent=2)+"\n")
if report["pass"]:(folder/"r160_r107_bwi_combined_canonical.json").write_text(json.dumps(c)+"\n")
print(json.dumps(report,indent=2))
