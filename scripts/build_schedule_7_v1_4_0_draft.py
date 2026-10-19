"""Build unpublished Schedule 7 v1.4.0 draft from published v1.3.3 plus accepted R106/R110.
Never update main or published manifest.
"""
from pathlib import Path
import json,sys,hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.timetable import export_timetable
basepath=ROOT/"data/schedules/schedule_7_v1_3_3/canonical_schedule.json"
base=json.loads(basepath.read_text())
assert base["schedule"]["id"]=="schedule_7_v1_3_3"
assert len(base["legs"])==1253
configs=[ROOT/f"config/optimizations/schedule_7_v1_4_0_r{route}.json" for route in (106,110)]
new=base
for path in configs:
    overlay=json.loads(path.read_text())
    new=apply_optimization_overlay(new,overlay)
assert (len(new["legs"]),len({x["route"] for x in new["legs"]}),len({x["line"] for x in new["legs"]}))==(1257,188,17)
assert new["schedule"]["id"]=="schedule_7_v1_4_0_draft"
assert new["schedule"]["status"]=="draft"
assert new["schedule"]["fleetCounts"]==base["schedule"]["fleetCounts"]
assert new["cities"]==base["cities"]
assert len(new["hubBanks"])==len(base["hubBanks"])+1
assert new["operatingPolicy"]["hubBankCounts"]["DAY"]==10
assert {l["flight"] for l in base["legs"]}.issubset({l["flight"] for l in new["legs"]})
assert all(len([l for l in new["legs"] if l["route"]==route])==count for route,count in [(106,8),(110,9)])
s=validate_schedule(new)
o=validate_operating_rules(new)
n=validate_overnight_turns(new)
p=reconstruct_planning_snapshot(new,demand_data_version="bts-db1c-6mo-jul2025-apr2026-v7")
pv=validate_planning_snapshot(p,new)
g=export_gate_schedule(new)
t=export_timetable(new)
assert s["status"]==n["status"]==pv["status"]=="pass"
assert o["summary"]["effectiveErrorFindings"]==0,o["summary"]
new.setdefault("provenance",{})["workingDraft"]={
    "baseline":"schedule_7_v1_3_3","baseSha256":hashlib.sha256(basepath.read_bytes()).hexdigest(),
    "overlays":[{"path":str(c.relative_to(ROOT)),"sha256":hashlib.sha256(c.read_bytes()).hexdigest()} for c in configs],
    "publication":"UNPUBLISHED v1.4.0 working draft; released default stays v1.3.3"}
out=ROOT/"data/schedules/schedule_7_v1_4_0_draft"
out.mkdir(parents=True,exist_ok=True)
for filename,value in {"canonical_schedule.json":new,"validation_report.json":s,
    "operating_validation_report.json":o,"overnight_turn_validation.json":n,
    "planning_snapshot.json":p,"planning_validation_report.json":pv,
    "gates.json":g,"timetable.json":t}.items():
    (out/filename).write_text(json.dumps(value,indent=2)+"\n")
print(json.dumps({"id":new["schedule"]["id"],"flights":len(new["legs"]),
    "routes":len({x["route"] for x in new["legs"]}),"lines":len({x["line"] for x in new["legs"]}),
    "effectiveErrors":o["summary"]["effectiveErrorFindings"],
    "physicalGateInventory":"pass","overnight":"pass",
    "publication":"none"},indent=2))
