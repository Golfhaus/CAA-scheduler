"""Materialize an unpublished v1.3.3 feasibility draft with R514 PIE-MCI turn."""
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
base_path=ROOT/"data/schedules/schedule_7_v1_3_2/canonical_schedule.json"
base=json.loads(base_path.read_text())
config_path=ROOT/"config/proposals/schedule_7_v1_3_3_r514_pie_mci.json"
config=json.loads(config_path.read_text())
assert base["schedule"]["id"]=="schedule_7_v1_3_2"
assert len(base["legs"])==1229
new=apply_optimization_overlay(base,config)
old={l["id"]:l for l in base["legs"]};now={l["id"]:l for l in new["legs"]}
assert len(new["legs"])==1229
assert {old[i]["flight"] for i in old.keys()-now.keys()}=={1230,1227}
assert {(now[i]["origin"],now[i]["destination"]) for i in now.keys()-old.keys()}=={("PIE","MCI"),("MCI","PIE")}
assert not any(l["route"]!=514 for l in new["legs"] if l["id"] in now.keys()-old.keys())
assert {l["line"] for l in new["legs"]}=={l["line"] for l in base["legs"]}
assert new["schedule"]["fleetCounts"]==base["schedule"]["fleetCounts"]
assert new["cities"]==base["cities"] and new["hubBanks"]==base["hubBanks"]
structure=validate_schedule(new)
operating=validate_operating_rules(new)
overnight=validate_overnight_turns(new)
plan=reconstruct_planning_snapshot(new,demand_data_version="bts-db1c-6mo-jul2025-apr2026-v7")
planning=validate_planning_snapshot(plan,new)
gates=export_gate_schedule(new)
assert structure["status"]==overnight["status"]==planning["status"]=="pass"
assert operating["summary"]["effectiveErrorFindings"]==0
stands=[x for city in gates["cities"] for x in city["claims"] if x["rowType"]=="stand"]
assert (len(stands),sum(x["end"]-x["start"] for x in stands))==(15,3061)
new.setdefault("provenance",{})["workingDraft"]={
"source":"schedule_7_v1_3_2","sourceSha256":hashlib.sha256(base_path.read_bytes()).hexdigest(),
"overlay":config_path.relative_to(ROOT).as_posix(),"overlaySha256":hashlib.sha256(config_path.read_bytes()).hexdigest(),
"publication":"NOT AUTHORIZED; v1.3.2 remains app default"}
out=ROOT/"data/schedules/schedule_7_v1_3_3_draft";out.mkdir(parents=True,exist_ok=True)
for name,content in {"canonical_schedule.json":new,"validation_report.json":structure,
"operating_validation_report.json":operating,"overnight_turn_validation.json":overnight,
"planning_snapshot.json":plan,"planning_validation_report.json":planning,
"gates.json":gates,"timetable.json":export_timetable(new)}.items():
 (out/name).write_text(json.dumps(content,indent=2)+"\n")
print(json.dumps({"draft":new["schedule"]["id"],"flights":len(new["legs"]),"routes":len(set(l["route"] for l in new["legs"])),"lines":len(set(l["line"] for l in new["legs"])),"effectiveErrors":operating["summary"]["effectiveErrorFindings"],"standClaims":len(stands),"publication":"none"},indent=2))
