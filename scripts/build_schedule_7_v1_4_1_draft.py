"""Build provisional Schedule 7 v1.4.1 from released v1.4.0 with R105/R162/R107.

Scope is R105 and R162 morning/evening BGR productive flying.
No web manifest or main branch changes. Approval remains pending.
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
source=ROOT/"data/schedules/schedule_7_v1_4_0/canonical_schedule.json"
base=json.loads(source.read_text())
assert base["schedule"]["id"]=="schedule_7_v1_4_0"
assert len(base["legs"])==1259
overlay_file=ROOT/"config/optimizations/schedule_7_v1_4_1_r105_r162_provisional.json"
overlay=json.loads(overlay_file.read_text())
new=apply_optimization_overlay(base,overlay)
r107_file=ROOT/"config/optimizations/schedule_7_v1_4_1_r107_isp_phf_provisional.json"
r107=json.loads(r107_file.read_text())
new=apply_optimization_overlay(new,r107)
assert new["schedule"]["id"]=="schedule_7_v1_4_1_draft"
assert new["schedule"]["status"]=="draft"
assert (len(new["legs"]),len({x["route"] for x in new["legs"]}),len({x["line"] for x in new["legs"]}))==(1264,188,17)
assert len([x for x in new["legs"] if x["route"]==105])==8
assert len([x for x in new["legs"] if x["route"]==162])==9
assert len([x for x in new["legs"] if x["route"]==107])==7
assert any(x["origin"]=="ISP" and x["destination"]=="PHF" and x["route"]==107 for x in new["legs"])
assert new["schedule"]["fleetCounts"]==base["schedule"]["fleetCounts"]
assert new["cities"]==base["cities"]
assert new["operatingPolicy"]["hubBankCounts"]["SYR"]==11
assert new["operatingPolicy"]["hubBankCounts"]["PHF"]==base["operatingPolicy"]["hubBankCounts"]["PHF"]+1
assert any(x["id"]=="PHF-M12-V141" for x in new["hubBanks"])
assert {b["id"] for b in new["hubBanks"] if b["hub"]=="SYR"}>={"SYR-M09","SYR-M12"}
assert max(l["day"] for l in new["legs"])<=13
assert {x["flight"] for x in base["legs"]}-{x["flight"] for x in new["legs"]}=={1893}  # ISP-SYR replaced by ISP-PHF-SYR
s=validate_schedule(new);n=validate_overnight_turns(new);o=validate_operating_rules(new)
p=reconstruct_planning_snapshot(new,demand_data_version="bts-db1c-6mo-jul2025-apr2026-v7")
pv=validate_planning_snapshot(p,new)
g=export_gate_schedule(new);t=export_timetable(new)
assert s["status"]==n["status"]==pv["status"]=="pass"
assert o["summary"]["effectiveErrorFindings"]==0,o["summary"]
new.setdefault("provenance",{})["workingDraft"]={
 "baseline":"schedule_7_v1_4_0","baselineSha256":hashlib.sha256(source.read_bytes()).hexdigest(),
 "overlays":[{"path":str(overlay_file.relative_to(ROOT)),
 "sha256":hashlib.sha256(overlay_file.read_bytes()).hexdigest()},
 {"path":str(r107_file.relative_to(ROOT)),
 "sha256":hashlib.sha256(r107_file.read_bytes()).hexdigest()}],
 "status":"PROVISIONAL, UNPUBLISHED; released web default stays v1.4.0"}
out=ROOT/"data/schedules/schedule_7_v1_4_1_draft"
out.mkdir(parents=True,exist_ok=True)
for name,val in {
 "canonical_schedule.json":new,"validation_report.json":s,
 "overnight_turn_validation.json":n,"operating_validation_report.json":o,
 "planning_snapshot.json":p,"planning_validation_report.json":pv,
 "gates.json":g,"timetable.json":t
}.items():(out/name).write_text(json.dumps(val,indent=2)+"\n")
def duration(l):return (l["arrivalMinute"]-l["departureMinute"]+1440)%1440
print(json.dumps({"draft":new["schedule"]["id"],"flights":len(new["legs"]),"routes":188,"lines":17,
 "effectiveErrors":o["summary"]["effectiveErrorFindings"],
 "routeMinutes":{str(n):sum(duration(l) for l in new["legs"] if l["route"]==n) for n in (105,106,107,108,162,167)},
 "status":"unpublished provisional draft"},indent=2))
