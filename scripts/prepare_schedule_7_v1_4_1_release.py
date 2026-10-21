"""Package user-approved Schedule 7 v1.4.1 without analysis artifacts."""
from pathlib import Path
import json, hashlib, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_release import build_optimization_release
draft_path=ROOT/"data/schedules/schedule_7_v1_4_1_draft/canonical_schedule.json"
draft=json.loads(draft_path.read_text())
assert draft["schedule"]["id"]=="schedule_7_v1_4_1_draft"
assert draft["schedule"]["status"]=="draft"
assert (len(draft["legs"]),len({x["route"] for x in draft["legs"]}),len({x["line"] for x in draft["legs"]}))==(1266,188,17)
assert json.loads((ROOT/"data/schedules/schedule_7_v1_4_1_draft/operating_validation_report.json").read_text())["summary"]["effectiveErrorFindings"]==0
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_0/canonical_schedule.json").read_text())
assert draft["schedule"]["fleetCounts"]==base["schedule"]["fleetCounts"]
sha=hashlib.sha256(draft_path.read_bytes()).hexdigest()
name="schedule_7_v1_4_1"
cfg={
"schemaVersion":"1.0.0","id":"schedule-7-v1.4.1-release",
"sourceScheduleId":"schedule_7_v1_4_0",
"baseCanonical":str(draft_path.relative_to(ROOT)),"baseCanonicalSha256":sha,
"overlays":[],"overlaySha256":{},"outputDirectory":f"data/schedules/{name}",
"rejoinAvoidableTows":True,"dropWorkingDraftProvenance":True,
"demandDataVersion":"bts-db1c-6mo-jul2025-apr2026-v7",
"schedule":{"id":name,"number":7,"version":"1.4.1","label":"Schedule 7, Version 1.4.1","status":"released"},
"patchScope":{"kind":"crj200_utilization_syr_reorganization","timetableChanged":True,"routingChanged":True,
"description":"Approved R105 BGR, R162 morning BGR, R107 ISP-PHF-SYR and R108 SYR-PIT-SYR optimization; supporting R356 BDL-SYR timing."},
"connectionAudit":{"hub":"SYR","groups":{"northeast":["BTV","HPN","MHT","PWM","ALB","ISP","BDL"],"other":["PIT","CAK","BUF","ORH","PHF","BGR","ROC"]}},
"connectionScopeDecision":{"status":"approved","approvedBy":"user","date":"2026-10-20",
"userInstruction":"Proceed as you understand the situation. Discard anything experimental or not tied to a published schedule.",
"acceptedDraftSha256":sha,"review":"R105, R107, R108 and R162 accepted with R356 supporting retiming; R106/R167 unchanged. BTV-RFD preserved. Discard rejected R167 alternatives. ISP-BNA and ORH-PGD commercial tradeoffs documented."},
"expectedRelease":{"legs":1266,"routes":188,"lines":17,"effectiveOperatingErrors":0,"hardStopFailures":0,"overnightTurnFailures":0}}
cfgpath=ROOT/"config/optimizations/schedule_7_v1_4_1_release.json"
cfgpath.write_text(json.dumps(cfg,indent=2)+"\n")
release=build_optimization_release(cfgpath,ROOT)
canonical=json.loads((ROOT/f"data/schedules/{name}/canonical_schedule.json").read_text())
assert canonical["legs"]==draft["legs"]
assert canonical["schedule"]["status"]=="released"
assert "workingDraft" not in canonical.get("provenance",{})
manifestpath=ROOT/"web/schedules.json"
manifest=json.loads(manifestpath.read_text())
assert manifest["defaultScheduleId"]=="schedule_7_v1_4_0"
assert not any(item["id"]==name for item in manifest["schedules"])
manifest["schedules"].append({"id":name,"label":"Schedule 7 · v1.4.1","files":{
"canonical":f"data/schedules/{name}/canonical_schedule.json",
"structuralValidation":f"data/schedules/{name}/validation_report.json",
"operatingValidation":f"data/schedules/{name}/operating_validation_report.json",
"planning":f"data/schedules/{name}/planning_snapshot.json",
"planningValidation":f"data/schedules/{name}/planning_validation_report.json",
"timetable":f"data/schedules/{name}/timetable.json",
"gates":f"data/schedules/{name}/gates.json",
"connectionAudit":f"data/schedules/{name}/connection_audit.json",
"optimizationRelease":f"data/schedules/{name}/release_report.json",
"overnightValidation":f"data/schedules/{name}/overnight_turn_validation.json"}})
manifest["defaultScheduleId"]=name
manifestpath.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
readme=ROOT/"README.md"
old=readme.read_text()
intro=("# CAA Scheduler\n\n## Latest published release\n\n"
"**Schedule 7 v1.4.1**, published October 20, 2026, is the application default: "
"**1,266 flights, 188 routes and 17 routing lines**, with zero effective operating errors. "
"Improvements to R105, R107, R108 and R162, with supporting R356 timing; R106 and R167 are unchanged. "
"See [v1.4.1 release notes](docs/schedule_7_v1_4_1_release.md) and "
"[canonical schedule](data/schedules/schedule_7_v1_4_1/canonical_schedule.json).\n\n"
"## Historical v1.4.0 and earlier releases\n\n")
assert old.startswith("# CAA Scheduler\n")
readme.write_text(intro+old[len("# CAA Scheduler\n"):])
# Keep the latest-only regression keyed to the new, current release.
for relative in ("tests/test_latest_schedule_release.py","tests/test_latest_service_gains.py"):
 path=ROOT/relative
 data=path.read_text().replace('"schedule_7_v1_4_0": 1259','"schedule_7_v1_4_0": 1259, "schedule_7_v1_4_1": 1266')
 if relative.endswith("test_latest_service_gains.py"):
  data=data.replace('"schedule_7_v1_4_0"}','"schedule_7_v1_4_0", "schedule_7_v1_4_1"}')
  data=data.replace('SCHEDULE_ID in {"schedule_7_v1_3_3", "schedule_7_v1_4_0"}','SCHEDULE_ID in {"schedule_7_v1_3_3", "schedule_7_v1_4_0", "schedule_7_v1_4_1"}')
 path.write_text(data)
print(json.dumps({"release":name,"summary":release["summary"],"default":manifest["defaultScheduleId"]},indent=2))
