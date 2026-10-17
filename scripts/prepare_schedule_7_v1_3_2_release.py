"""Package approved Schedule 7 v1.3.2 from its pinned, validated draft.

Does not touch main: this is run on the candidate PR branch, with checks
required before merge. User authorized publication 2026-10-16.
"""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_release import build_optimization_release

draft_file=ROOT/"data/schedules/schedule_7_v1_3_2_draft/canonical_schedule.json"
draft=json.loads(draft_file.read_text())
assert draft["schedule"]["id"]=="schedule_7_v1_3_2_draft"
assert len(draft["legs"])==1229
assert len({l["route"] for l in draft["legs"]})==184
assert len({l["line"] for l in draft["legs"]})==17
review=json.loads((ROOT/"outputs/schedule_7_v1_3_2_release_readiness/network_vs_v131.json").read_text())
assert review["flightsBefore"]==1214 and review["flightsAfter"]==1229
expected_losses={"OMA-PHF","ATW-OKC","DSM-SHV","ATW-FSD","ATW-SHV"}
assert {x["market"] for x in review["geographic"]["lost"]}==expected_losses, "Unexpected geographic coverage loss"
assert len(review["geographic"]["gained"])==60
assert len(review["geographic"]["faster"])==154
assert len(review["geographic"]["slower"])==155
prior=json.loads((ROOT/"data/schedules/schedule_7_v1_3_1/canonical_schedule.json").read_text())
assert draft["schedule"]["fleetCounts"]==prior["schedule"]["fleetCounts"]
assert draft["cities"]==prior["cities"] and draft["hubBanks"]==prior["hubBanks"]
assert draft["schedule"]["connectionWindowMinutes"]==prior["schedule"]["connectionWindowMinutes"]

relative="data/schedules/schedule_7_v1_3_2_draft/canonical_schedule.json"
sha=hashlib.sha256(draft_file.read_bytes()).hexdigest()
cfg={
 "schemaVersion":"1.0.0",
 "id":"schedule-7-v1.3.2-release",
 "sourceScheduleId":"schedule_7_v1_3_1",
 "baseCanonical":relative,
 "baseCanonicalSha256":sha,
 "overlays":[],
 "overlaySha256":{},
 "outputDirectory":"data/schedules/schedule_7_v1_3_2",
 "rejoinAvoidableTows":True,
 "dropWorkingDraftProvenance":True,
 "demandDataVersion":"bts-db1c-6mo-jul2025-apr2026-v7",
 "schedule":{"id":"schedule_7_v1_3_2","number":7,"version":"1.3.2","label":"Schedule 7, Version 1.3.2","status":"released"},
 "patchScope":{"kind":"maintenance_repair_and_productive_crj200_flying",
   "timetableChanged":True,"routingChanged":True,
   "description":"Correct cyclic maintenance/RON validation, preserve approved R501/R175/R125/R111/R312 improvements, and adopt R144/R146/R158/R176 route optimization."},
 "connectionAudit":{"hub":"SYR","groups":{"northeast":["HPN","HVN","ISP","BTV","ORH"],"priorityFlorida":["PGD","DAB"]}},
 "connectionScopeDecision":{
   "status":"approved","approvedBy":"user","date":"2026-10-16",
   "userInstruction":"Complete any remaining audits, and publish v1.3.2 to main if there are no issues.",
   "acceptedDraftSha256":sha,
   "networkItineraryAuditSummary":{
      "geographicallyReasonableGains":60,"geographicallyReasonableLosses":5,
      "fasterFastestJourneys":154,"slowerFastestJourneys":155,
      "lostMarkets":sorted(expected_losses),
      "auditedComparedTo":"schedule_7_v1_3_1"},
   "releaseInterpretation":"Five documented, previously reviewed geographic one-stop coverage tradeoffs; none are new operating validation failures."},
 "expectedRelease":{"legs":1229,"routes":184,"lines":17,
   "effectiveOperatingErrors":0,"hardStopFailures":0,
   "overnightTurnFailures":0,"standClaims":15,"standMinutes":3061}
}
config_path=ROOT/"config/optimizations/schedule_7_v1_3_2_release.json"
config_path.write_text(json.dumps(cfg,indent=2)+"\n")
release=build_optimization_release(config_path,ROOT)
package=ROOT/"data/schedules/schedule_7_v1_3_2"
released=json.loads((package/"canonical_schedule.json").read_text())
assert released["legs"]==draft["legs"]
assert released["schedule"]["status"]=="released"
assert "workingDraft" not in released["provenance"]
assert release["summary"]["effectiveOperatingErrors"]==0
manifest_file=ROOT/"web/schedules.json"
manifest=json.loads(manifest_file.read_text())
new_id="schedule_7_v1_3_2"
entry={"id":new_id,"label":"Schedule 7 · v1.3.2",
 "files":{"canonical":f"data/schedules/{new_id}/canonical_schedule.json",
 "structuralValidation":f"data/schedules/{new_id}/validation_report.json",
 "operatingValidation":f"data/schedules/{new_id}/operating_validation_report.json",
 "planning":f"data/schedules/{new_id}/planning_snapshot.json",
 "planningValidation":f"data/schedules/{new_id}/planning_validation_report.json",
 "timetable":f"data/schedules/{new_id}/timetable.json",
 "gates":f"data/schedules/{new_id}/gates.json",
 "connectionAudit":f"data/schedules/{new_id}/connection_audit.json",
 "optimizationRelease":f"data/schedules/{new_id}/release_report.json",
 "overnightValidation":f"data/schedules/{new_id}/overnight_turn_validation.json"}}
assert not any(s["id"]==new_id for s in manifest["schedules"]),"Already published; refuse duplicate"
assert manifest["defaultScheduleId"]=="schedule_7_v1_3_1"
manifest["schedules"].append(entry)
manifest["defaultScheduleId"]=new_id
manifest_file.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
print(json.dumps({"status":"release assets prepared for PR validation, not merged",
"flightCount":len(released["legs"]),"routes":184,"lines":17,
"newDefault":manifest["defaultScheduleId"],"draftSha256":sha,
"release":release["summary"]},indent=2))
