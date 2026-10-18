"""Read-only dry run: splice new R530 into CRJ900 AG between R518 and R519.

Never writes cumulative schedule or modifies accepted four-aircraft draft.
"""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
root=ROOT/"data/schedules/schedule_7_v1_3_3_draft/canonical_schedule.json"
before=json.loads(root.read_text())
changes={"schemaVersion":"1.0.0","id":"v133-r530-ag-splice-dry-run",
"baseSchedule":{"scheduleId":before["schedule"]["id"]},"schedule":before["schedule"],
"routeReassignments":[
 {"sourceRoute":530,"expectedLine":"BB","expectedDay":1,"expectedFleet":"CRJ900","line":"AG","day":9},
 {"sourceRoute":519,"expectedLine":"AG","expectedDay":9,"expectedFleet":"CRJ900","line":"AG","day":10}
]}
report={"scope":"DRY RUN only; no draft or release edited","changes":changes}
try:
 candidate=apply_optimization_overlay(before,changes)
 s=validate_schedule(candidate);v=validate_operating_rules(candidate)
 n=validate_overnight_turns(candidate)
 p=validate_planning_snapshot(reconstruct_planning_snapshot(candidate),candidate)
 try:g=export_gate_schedule(candidate);gate="pass"
 except Exception as e:g=None;gate=f"{type(e).__name__}: {e}"
 fail=[{"id":x["id"],"findings":x.get("findings",[])[:5]} for x in v["checks"] if x["status"]=="fail"]
 ok=s["status"]==n["status"]==p["status"]=="pass" and v["summary"]["effectiveErrorFindings"]==0 and gate=="pass"
 report.update({"pass":ok,"structural":s["status"],"overnight":n["status"],"planning":p["status"],"gate":gate,"operating":v["summary"],"failed":fail,"flightCount":len(candidate["legs"]),"routeCount":len(set(l["route"] for l in candidate["legs"])),"lineCount":len(set(l["line"] for l in candidate["legs"])),"fleetUse":next(x for x in v["checks"] if x["id"]=="fleet_capacity")["metrics"],"agRouteDays":sorted([{"day":l["day"],"route":l["route"]} for l in candidate["legs"] if l["line"]=="AG" and l["sequenceWithinRoute"]==1],key=lambda l:l["day"])})
 if ok:
  # Export only metadata, not a new canonical or an accepted overlay.
  report["firstFlightOnR530"]=next(l["flight"] for l in candidate["legs"] if l["route"]==530 and l["sequenceWithinRoute"]==1)
except Exception as e:
 report.update({"pass":False,"error":repr(e),"traceback":traceback.format_exc()[-2200:]})
out=ROOT/"outputs/schedule_7_v1_3_3_bhm_line_insertion"
out.mkdir(exist_ok=True,parents=True)
(out/"r530_ag_dry_run.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
