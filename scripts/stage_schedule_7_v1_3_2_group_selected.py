"""Rebuild selected, unpublished v1.3.2 R144/R146/R176/R158 working schedule."""
from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.timetable import export_timetable
src=ROOT/"outputs/schedule_7_v1_3_2_selected/canonical_schedule.json"
c=json.loads(src.read_text())
assert len(c["legs"])==1227,"R144+R146 baseline unexpectedly changed"
prior={x["id"]:x for x in c["legs"]}
for path in ["config/optimizations/schedule_7_v1_3_2_r176_selected.json","config/optimizations/schedule_7_v1_3_2_r158_selected.json"]:
 p=ROOT/path;overlay=json.loads(p.read_text())
 c=apply_optimization_overlay(c,overlay)
 c["provenance"]["workingDraft"]["draftOverlays"].append({"path":path,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
now={x["id"]:x for x in c["legs"]}
assert len(now)==1229
assert {prior[i]["flight"] for i in set(prior)-set(now)}=={2053,2054}
inserted={i for i in set(now)-set(prior)}
assert len(inserted)==4
assert {(now[i]["origin"],now[i]["destination"]) for i in inserted}=={("PHF","GSO"),("GSO","PHF"),("ALB","RDU"),("RDU","ALB")}
assert len({(x["line"],x["day"]) for x in c["legs"]})==len({(x["line"],x["day"]) for x in prior.values()})
structure=validate_schedule(c);oper=validate_operating_rules(c);overnight=validate_overnight_turns(c)
plan=reconstruct_planning_snapshot(c,demand_data_version="bts-db1c-6mo-jul2025-apr2026-v7");planning=validate_planning_snapshot(plan,c)
gates=export_gate_schedule(c)
assert structure["status"]==planning["status"]==overnight["status"]=="pass"
assert oper["summary"]["effectiveErrorFindings"]==0
stands=[x for city in gates["cities"] for x in city["claims"] if x["rowType"]=="stand"]
assert (len(stands),sum(x["end"]-x["start"] for x in stands))==(15,3061)
out=ROOT/"outputs/schedule_7_v1_3_2_group_selected";out.mkdir(parents=True,exist_ok=True)
for name,item in {"canonical_schedule.json":c,"validation_report.json":structure,
 "operating_validation_report.json":oper,"overnight_turn_validation.json":overnight,
 "planning_snapshot.json":plan,"planning_validation_report.json":planning,
 "gates.json":gates,"timetable.json":export_timetable(c)}.items():
 (out/name).write_text(json.dumps(item,indent=2)+"\n")
print(json.dumps({"status":"validated working draft only; publication not authorized",
 "flights":len(now),"newFlightIds":sorted(now[i]["flight"] for i in inserted),
 "removedFlights":[2053,2054],"structural":structure["status"],
 "overnight":overnight["status"],"planning":planning["status"],
 "effectiveOperatingErrors":oper["summary"]["effectiveErrorFindings"],
 "standClaims":len(stands),"lines":len({x["line"] for x in c["legs"]})}))
