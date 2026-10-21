"""Construct the validated tactical-only v1.4.2 working draft (not a release)."""
from pathlib import Path
import json,sys,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.timetable import export_timetable
src=ROOT/"data/schedules/schedule_7_v1_4_1/canonical_schedule.json"
overlay_path=ROOT/"config/optimizations/schedule_7_v1_4_2_mci_tactical_candidate.json"
base=json.loads(src.read_text());overlay=json.loads(overlay_path.read_text())
new=apply_optimization_overlay(base,overlay)
assert new["schedule"]["id"]=="schedule_7_v1_4_2_draft"
assert len(new["legs"])==1266
for flight,dep in [(1357,631),(1077,884)]:
 assert next(l for l in new["legs"] if l["flight"]==flight)["departureMinute"]==dep
struct=validate_schedule(new);overnight=validate_overnight_turns(new);operating=validate_operating_rules(new)
planning=reconstruct_planning_snapshot(new,demand_data_version="bts-db1c-6mo-jul2025-apr2026-v7")
plan_val=validate_planning_snapshot(planning,new)
gates=export_gate_schedule(new);table=export_timetable(new)
assert struct["status"]==overnight["status"]==plan_val["status"]=="pass"
assert operating["summary"]["effectiveErrorFindings"]==0
new.setdefault("provenance",{})["workingDraft"]={"baseline":"schedule_7_v1_4_1","baselineSha256":hashlib.sha256(src.read_bytes()).hexdigest(),"overlays":[{"path":str(overlay_path.relative_to(ROOT)),"sha256":hashlib.sha256(overlay_path.read_bytes()).hexdigest()}],"status":"UNPUBLISHED: tactical retimings only, three-aircraft allocation not integrated"}
out=ROOT/"data/schedules/schedule_7_v1_4_2_draft";out.mkdir(parents=True,exist_ok=True)
for name,obj in {"canonical_schedule.json":new,"validation_report.json":struct,"overnight_turn_validation.json":overnight,"operating_validation_report.json":operating,"planning_snapshot.json":planning,"planning_validation_report.json":plan_val,"gates.json":gates,"timetable.json":table}.items():
 (out/name).write_text(json.dumps(obj,indent=2)+"\n")
print(json.dumps({"draft":new["schedule"]["id"],"flights":len(new["legs"]),"effectiveErrors":0,"sparesReleased":0}))
