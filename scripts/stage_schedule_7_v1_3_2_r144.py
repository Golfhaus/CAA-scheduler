"""Materialize approved R144 on top of the five-round v1.3.2 draft.

Run from repository root: python scripts/stage_schedule_7_v1_3_2_r144.py
Does not publish or overwrite the cumulative five-round canonical.
"""
from pathlib import Path
import hashlib, json, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules, validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot, validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.timetable import export_timetable

subprocess.run([sys.executable,str(ROOT/"scripts/build_schedule_7_v1_3_2_draft.py")],check=True)
source=ROOT/"data/schedules/schedule_7_v1_3_2_draft/canonical_schedule.json"
proposal=ROOT/"config/proposals/schedule_7_v1_3_2_r144_jax_bna.json"
overlay=json.loads(proposal.read_text())
sha=hashlib.sha256(source.read_bytes()).hexdigest()
assert sha==overlay["baseSchedule"]["sha256"],"R144 base checksum changed; review required"
base=json.loads(source.read_text())
updated=apply_optimization_overlay(base,overlay)
assert len(updated["legs"])==len(base["legs"])+4==1225
old={x["id"]:x for x in base["legs"]}
new={x["id"]:x for x in updated["legs"]}
added=[x for k,x in new.items() if k not in old]
assert {(x["origin"],x["destination"]) for x in added}=={
("JAN","JAX"),("JAX","JAN"),("MCI","BNA"),("BNA","MCI")}
assert {old[k]["flight"] for k in old if old[k]["departureMinute"]!=new[k]["departureMinute"]}=={1500,1553,1596}
assert len({(x["line"],x["day"]) for x in updated["legs"]})==len({(x["line"],x["day"]) for x in base["legs"]})
struct=validate_schedule(updated)
oper=validate_operating_rules(updated)
overnight=validate_overnight_turns(updated)
plan=reconstruct_planning_snapshot(updated,demand_data_version="bts-db1c-6mo-jul2025-apr2026-v7")
planning=validate_planning_snapshot(plan,updated)
gates=export_gate_schedule(updated)
assert struct["status"]==overnight["status"]==planning["status"]=="pass"
assert oper["summary"]["effectiveErrorFindings"]==0
stands=[x for city in gates["cities"] for x in city["claims"] if x["rowType"]=="stand"]
assert (len(stands),sum(x["end"]-x["start"] for x in stands))==(15,3061)
updated["provenance"]["workingDraft"]["draftOverlays"].append({
"path":proposal.relative_to(ROOT).as_posix(),
"sha256":hashlib.sha256(proposal.read_bytes()).hexdigest()})
updated["provenance"]["workingDraft"]["publication"]="Unpublished: R144 accepted for v1.3.2 review"
out=ROOT/"outputs/schedule_7_v1_3_2_r144_accepted"
out.mkdir(parents=True,exist_ok=True)
for name,obj in {
"canonical_schedule.json":updated,
"validation_report.json":struct,
"operating_validation_report.json":oper,
"overnight_turn_validation.json":overnight,
"planning_snapshot.json":plan,
"planning_validation_report.json":planning,
"gates.json":gates,
"timetable.json":export_timetable(updated),
}.items():
 (out/name).write_text(json.dumps(obj,indent=2)+"\n")
print(json.dumps({"status":"validated unpublished R144 candidate","flights":len(updated["legs"]),"addedFlights":[x["flight"] for x in added],"output":str(out)},indent=2))
