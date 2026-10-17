"""Materialize selected R146 extension atop verified R144-augmented v1.3.2 draft."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.timetable import export_timetable
input_path=ROOT/"outputs/schedule_7_v1_3_2_r144_accepted/canonical_schedule.json"
base=json.loads(input_path.read_text())
overlay_path=ROOT/"config/optimizations/schedule_7_v1_3_2_r146_selected.json"
overlay=json.loads(overlay_path.read_text())
updated=apply_optimization_overlay(base,overlay)
assert len(updated["legs"])==1227
old={x["id"]:x for x in base["legs"]};new={x["id"]:x for x in updated["legs"]}
assert len(set(new)-set(old))==2
assert {new[i]["origin"]+"-"+new[i]["destination"] for i in set(new)-set(old)}=={"FSD-MCI","MCI-FSD"}
assert {old[i]["flight"] for i in old if old[i]["departureMinute"]!=new[i]["departureMinute"]}=={1677}
assert len({(l["line"],l["day"]) for l in updated["legs"]})==len({(l["line"],l["day"]) for l in base["legs"]})
s=validate_schedule(updated)
v=validate_operating_rules(updated)
n=validate_overnight_turns(updated)
plan=reconstruct_planning_snapshot(updated,demand_data_version="bts-db1c-6mo-jul2025-apr2026-v7")
p=validate_planning_snapshot(plan,updated)
g=export_gate_schedule(updated)
assert s["status"]==n["status"]==p["status"]=="pass" and v["summary"]["effectiveErrorFindings"]==0
stands=[x for city in g["cities"] for x in city["claims"] if x["rowType"]=="stand"]
assert (len(stands),sum(x["end"]-x["start"] for x in stands))==(15,3061)
updated["provenance"]["workingDraft"]["draftOverlays"].append({
"path":overlay_path.relative_to(ROOT).as_posix(),
"sha256":hashlib.sha256(overlay_path.read_bytes()).hexdigest()})
out=ROOT/"outputs/schedule_7_v1_3_2_selected"
out.mkdir(exist_ok=True,parents=True)
for name,obj in {"canonical_schedule.json":updated,"validation_report.json":s,
"operating_validation_report.json":v,"overnight_turn_validation.json":n,
"planning_snapshot.json":plan,"planning_validation_report.json":p,
"gates.json":g,"timetable.json":export_timetable(updated)}.items():
 (out/name).write_text(json.dumps(obj,indent=2)+"\n")
print(json.dumps({"selected":"R144 and R146","draftFlights":len(updated["legs"]),
"addedR146":sorted(new[i]["flight"] for i in set(new)-set(old)),
"operating":v["summary"],"standClaims":len(stands)}))
