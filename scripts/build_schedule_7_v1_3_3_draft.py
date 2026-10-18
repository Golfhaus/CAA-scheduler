"""Reproduce unpublished v1.3.3 with R514 PIE-MCI and four BHM mini-bank aircraft."""
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
# The pre-BHM state remains permanently available at the protected checkpoint.
pre_bhm=new
bhm_path=ROOT/"config/optimizations/schedule_7_v1_3_3_bhm_minibanks.json"
bhm=json.loads(bhm_path.read_text())
new=apply_optimization_overlay(pre_bhm,bhm)
pinned=ROOT/"outputs/schedule_7_v1_3_3_bhm_minibanks_mx5/day_day_canonical.json"
accepted=json.loads(pinned.read_text())
assert new["legs"]==accepted["legs"],"BHM candidate legs changed from accepted feasibility screen"
assert new["bankAssignments"]==accepted["bankAssignments"],"BHM bank assignments changed"
assert new["operatingPolicy"]==accepted["operatingPolicy"],"BHM operating policy differs from accepted screen"
assert len(new["legs"])==1253
assert len({l["route"] for l in new["legs"]})==188
assert len({l["line"] for l in new["legs"]})==21
# Approved line splice: R530 occupies AG day 9; former R519 becomes AG day 10.
splice_path=ROOT/"config/optimizations/schedule_7_v1_3_3_r530_ag_insertion.json"
splice=json.loads(splice_path.read_text())
new=apply_optimization_overlay(new,splice)
assert len({l["line"] for l in new["legs"]})==20
assert len(new["legs"])==1253
# Approved R529 splice: close at CMH, join AG after R519 on day 11.
# Preserve all six flight numbers; replace only the DAY positioning markets.
r529=[l for l in new["legs"] if l["route"]==529]
assert len(r529)==6 and {(l["line"],l["day"]) for l in r529}=={("BA",1)}
r529.sort(key=lambda l:l["sequenceWithinRoute"])
first,last=r529[0],r529[-1]
assert (first["id"],first["origin"],first["destination"],first["departureMinute"],first["arrivalMinute"])==("V133-BHM-529-1-DAY-ALB","DAY","ALB",360,460)
assert (last["id"],last["origin"],last["destination"],last["departureMinute"],last["arrivalMinute"])==("V133-BHM-529-6-ALB-DAY","ALB","DAY",1165,1265)
old_ids={first["id"],last["id"]}
first["id"]="V133-BHM-529-1-CMH-ALB";first["origin"]="CMH"
last["id"]="V133-BHM-529-6-ALB-CMH";last["destination"]="CMH"
pairings={(l["origin"],l["destination"]):l["pairing"] for l in new["legs"] if l["route"]!=529}
next_pairing=max(l["pairing"] for l in new["legs"])+1
for leg in (first,last):
    market=(leg["origin"],leg["destination"])
    if market not in pairings:
        pairings[market]=next_pairing
        next_pairing+=1
    leg["pairing"]=pairings[market]
for leg in r529:
    leg["line"]="AG";leg["day"]=11
new["bankAssignments"]=[a for a in new["bankAssignments"] if a["legId"] not in old_ids]
assert len({l["line"] for l in new["legs"]})==19
assert len({l["route"] for l in new["legs"]})==188
assert new["schedule"]["fleetCounts"]==base["schedule"]["fleetCounts"]
structure=validate_schedule(new)
operating=validate_operating_rules(new)
overnight=validate_overnight_turns(new)
plan=reconstruct_planning_snapshot(new,demand_data_version="bts-db1c-6mo-jul2025-apr2026-v7")
planning=validate_planning_snapshot(plan,new)
gates=export_gate_schedule(new)
assert structure["status"]==overnight["status"]==planning["status"]=="pass"
assert operating["summary"]["effectiveErrorFindings"]==0
stands=[x for city in gates["cities"] for x in city["claims"] if x["rowType"]=="stand"]
assert all(c["nGates"]>=0 and c["nStands"]>=0 for c in gates["cities"])
new.setdefault("provenance",{})["workingDraft"]={
"source":"schedule_7_v1_3_2","sourceSha256":hashlib.sha256(base_path.read_bytes()).hexdigest(),
"overlay":config_path.relative_to(ROOT).as_posix(),"overlaySha256":hashlib.sha256(config_path.read_bytes()).hexdigest(),
"additionalOverlays":[{"path":bhm_path.relative_to(ROOT).as_posix(),"sha256":hashlib.sha256(bhm_path.read_bytes()).hexdigest()},{"path":splice_path.relative_to(ROOT).as_posix(),"sha256":hashlib.sha256(splice_path.read_bytes()).hexdigest()}],
"r529Integration":{"route":529,"line":"AG","day":11,"positioning":"CMH-ALB-CMH","screen":"outputs/schedule_7_v1_3_3_bhm_line_insertion/remaining_three_screen.json"},
"revertPoint":{"branch":"checkpoint/schedule-7-v1.3.3-pre-bhm-minibanks","commit":"6965d28175b4089c269f543a1d6b24b423fbdcb3"},
"publication":"NOT AUTHORIZED; v1.3.2 remains app default"}
out=ROOT/"data/schedules/schedule_7_v1_3_3_draft";out.mkdir(parents=True,exist_ok=True)
for name,content in {"canonical_schedule.json":new,"validation_report.json":structure,
"operating_validation_report.json":operating,"overnight_turn_validation.json":overnight,
"planning_snapshot.json":plan,"planning_validation_report.json":planning,
"gates.json":gates,"timetable.json":export_timetable(new)}.items():
 (out/name).write_text(json.dumps(content,indent=2)+"\n")
fleet_check=next(x for x in operating["checks"] if x["id"]=="fleet_capacity")
assert fleet_check["metrics"]["CRJ900"]["used"]==30 and fleet_check["metrics"]["CRJ700"]["used"]==58
print(json.dumps({"draft":new["schedule"]["id"],"flights":len(new["legs"]),"routes":len(set(l["route"] for l in new["legs"])),"lines":len(set(l["line"] for l in new["legs"])),"effectiveErrors":operating["summary"]["effectiveErrorFindings"],"standClaims":len(stands),"standMinutes":sum(x["end"]-x["start"] for x in stands),"aircraftUsed":{"CRJ900":30,"CRJ700":58},"publication":"none"},indent=2))
