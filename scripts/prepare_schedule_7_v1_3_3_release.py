"""Package approved v1.3.3 draft and set web default, never merge directly to main."""
from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_release import build_optimization_release
src=ROOT/"data/schedules/schedule_7_v1_3_3_draft/canonical_schedule.json"
draft=json.loads(src.read_text())
assert draft["schedule"]["id"]=="schedule_7_v1_3_3_draft"
assert (len(draft["legs"]),len({x["route"] for x in draft["legs"]}),len({x["line"] for x in draft["legs"]}))==(1253,188,17)
assert {(x["route"],x["line"],x["day"]) for x in draft["legs"] if x["route"] in (529,530,357,358)}=={(529,"AG",11),(530,"AG",9),(357,"AK",10),(358,"AA",8)}
assert max(x["day"] for x in draft["legs"])<=13
previous=json.loads((ROOT/"data/schedules/schedule_7_v1_3_2/canonical_schedule.json").read_text())
assert draft["cities"]==previous["cities"] and draft["hubBanks"]==previous["hubBanks"]
assert draft["schedule"]["fleetCounts"]==previous["schedule"]["fleetCounts"]
report=json.loads((ROOT/"data/schedules/schedule_7_v1_3_3_draft/operating_validation_report.json").read_text())
assert report["summary"]["effectiveErrorFindings"]==0
sha=hashlib.sha256(src.read_bytes()).hexdigest()
cfg={
"schemaVersion":"1.0.0","id":"schedule-7-v1.3.3-release","sourceScheduleId":"schedule_7_v1_3_2",
"baseCanonical":"data/schedules/schedule_7_v1_3_3_draft/canonical_schedule.json",
"baseCanonicalSha256":sha,"overlays":[],"overlaySha256":{},
"outputDirectory":"data/schedules/schedule_7_v1_3_3","rejoinAvoidableTows":True,
"dropWorkingDraftProvenance":True,"demandDataVersion":"bts-db1c-6mo-jul2025-apr2026-v7",
"schedule":{"id":"schedule_7_v1_3_3","number":7,"version":"1.3.3","label":"Schedule 7, Version 1.3.3","status":"released"},
"patchScope":{"kind":"r514_pie_mci_and_bhm_north_south_mini_banks","timetableChanged":True,"routingChanged":True,"description":"Approved R514 PIE–MCI turn plus 24 BHM mini-bank flights on R529/R530/R357/R358, spliced into AG, AK and AA lines."},
"connectionAudit":{"hub":"BHM","groups":{"north":["ISP","HVN","ALB","CAK"],"south":["MYR","SRQ","CHS","PGD"]}},
"connectionScopeDecision":{"status":"approved","approvedBy":"user","date":"2026-10-18","userInstruction":"Commit these to the draft, and push 1.3.3 to main.","acceptedDraftSha256":sha,
"review":"Prior network audit documented 60 geographically reasonable coverage gains and no losses compared with the R514-only draft; positioning-leg replacements require separate review."},
"expectedRelease":{"legs":1253,"routes":188,"lines":17,"effectiveOperatingErrors":0,"hardStopFailures":0,"overnightTurnFailures":0}}
cfgpath=ROOT/"config/optimizations/schedule_7_v1_3_3_release.json"
cfgpath.write_text(json.dumps(cfg,indent=2)+"\n")
release=build_optimization_release(cfgpath,ROOT)
out=ROOT/"data/schedules/schedule_7_v1_3_3"
published=json.loads((out/"canonical_schedule.json").read_text())
assert published["legs"]==draft["legs"]
assert published["schedule"]["status"]=="released"
assert "workingDraft" not in published.get("provenance",{})
manifestpath=ROOT/"web/schedules.json"
manifest=json.loads(manifestpath.read_text())
newid="schedule_7_v1_3_3"
assert manifest["defaultScheduleId"]=="schedule_7_v1_3_2"
assert not any(e["id"]==newid for e in manifest["schedules"])
manifest["schedules"].append({"id":newid,"label":"Schedule 7 · v1.3.3","files":{
"canonical":f"data/schedules/{newid}/canonical_schedule.json",
"structuralValidation":f"data/schedules/{newid}/validation_report.json",
"operatingValidation":f"data/schedules/{newid}/operating_validation_report.json",
"planning":f"data/schedules/{newid}/planning_snapshot.json",
"planningValidation":f"data/schedules/{newid}/planning_validation_report.json",
"timetable":f"data/schedules/{newid}/timetable.json",
"gates":f"data/schedules/{newid}/gates.json",
"connectionAudit":f"data/schedules/{newid}/connection_audit.json",
"optimizationRelease":f"data/schedules/{newid}/release_report.json",
"overnightValidation":f"data/schedules/{newid}/overnight_turn_validation.json"}})
manifest["defaultScheduleId"]=newid
manifestpath.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
readme=ROOT/"README.md"
old=readme.read_text()
assert old.startswith("# CAA Scheduler\n")
head=("# CAA Scheduler\n\n## Latest published release\n\n"
"**Schedule 7 v1.3.3** (October 18, 2026) is the application default: "
"**1,253 flights, 188 routes, 17 routing lines**, with zero effective operating errors. "
"Adds approved R514 PIE–MCI and the BHM north–south mini-banks on R529, R530, R357 and R358. "
"The four mini-bank routes are integrated into longer aircraft lines (maximum 13 days). "
"See [v1.3.3 release notes](docs/schedule_7_v1_3_3_release.md) and "
"[canonical schedule](data/schedules/schedule_7_v1_3_3/canonical_schedule.json).\n\n"
"## Historical v1.3.2 and older releases\n\n")
readme.write_text(head+old[len("# CAA Scheduler\n"):])
print(json.dumps({"status":"prepared for main merge","release":release["summary"],"manifestDefault":manifest["defaultScheduleId"]},indent=2))
