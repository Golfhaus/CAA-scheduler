"""Prepare approved Schedule 7 v1.4.0 release from the validated cumulative draft.

Only operates on the release candidate branch. main is updated through PR merge
after latest-release tests and web-build verification pass.
"""
from pathlib import Path
import json,sys,hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_release import build_optimization_release
draftpath=ROOT/"data/schedules/schedule_7_v1_4_0_draft/canonical_schedule.json"
draft=json.loads(draftpath.read_text())
assert draft["schedule"]["id"]=="schedule_7_v1_4_0_draft"
assert draft["schedule"]["status"]=="draft"
assert (len(draft["legs"]),len({l["route"] for l in draft["legs"]}),len({l["line"] for l in draft["legs"]}))==(1259,188,17)
assert len(draft["hubBanks"])==len(json.loads((ROOT/"data/schedules/schedule_7_v1_3_3/canonical_schedule.json").read_text())["hubBanks"])+3
assert {b["id"] for b in draft["hubBanks"] if b["hub"]=="SYR"}>={"SYR-M15","SYR-M17"}
assert draft["operatingPolicy"]["hubBankCounts"]["SYR"]==9
assert draft["operatingPolicy"]["hubBankCounts"]["DAY"]==10
assert len([l for l in draft["legs"] if l["route"]==160])==8
assert len([l for l in draft["legs"] if l["route"]==107])==6
assert {l["flight"] for l in draft["legs"] if l["route"]==160 and l["origin"]=="PWM" and l["destination"]=="PHF"}
assert max(l["day"] for l in draft["legs"])<=13
previous=json.loads((ROOT/"data/schedules/schedule_7_v1_3_3/canonical_schedule.json").read_text())
assert draft["cities"]==previous["cities"]
assert draft["schedule"]["fleetCounts"]==previous["schedule"]["fleetCounts"]
assert json.loads((ROOT/"data/schedules/schedule_7_v1_4_0_draft/operating_validation_report.json").read_text())["summary"]["effectiveErrorFindings"]==0
sha=hashlib.sha256(draftpath.read_bytes()).hexdigest()
cfg={
"schemaVersion":"1.0.0","id":"schedule-7-v1.4.0-release",
"sourceScheduleId":"schedule_7_v1_3_3",
"baseCanonical":"data/schedules/schedule_7_v1_4_0_draft/canonical_schedule.json",
"baseCanonicalSha256":sha,
"overlays":[],"overlaySha256":{},
"outputDirectory":"data/schedules/schedule_7_v1_4_0",
"rejoinAvoidableTows":True,"dropWorkingDraftProvenance":True,
"demandDataVersion":"bts-db1c-6mo-jul2025-apr2026-v7",
"schedule":{"id":"schedule_7_v1_4_0","number":7,"version":"1.4.0",
"label":"Schedule 7, Version 1.4.0","status":"released"},
"patchScope":{"kind":"crj200_utilization_and_selective_syr_mini_banks",
"timetableChanged":True,"routingChanged":True,
"description":"R106 BTV-SYR-BTV and R110 DAY-SYR-DAY extensions; Syracuse M15/M17 paired mini-banks on R106/R110/R130/R131; R160 PWM-PHF-PWM productive extension; logical DAY midnight bank."},
"connectionAudit":{"hub":"SYR","groups":{"northeast":["BTV","HPN","MHT","PWM","ALB","ISP","BDL"],
"other":["PIT","CAK","BUF","ORH","PHF","BGR","ROC"]}},
"connectionScopeDecision":{"status":"approved","approvedBy":"user",
"date":"2026-10-19","userInstruction":"Very good. Publish 1.4.0 to main.",
"acceptedDraftSha256":sha,
"review":"Accepted the selective four-route SYR M15/M17 mini-bank proposal and R160 PWM-PHF-PWM extension. Previous directional itinerary audit records one geographic gain FWA-PWM and one loss MCI-PWM, plus 74 faster and 53 slower fastest itineraries vs the 1,257-flight interim draft. This tradeoff is documented and remains open; published by explicit user approval."},
"expectedRelease":{"legs":1259,"routes":188,"lines":17,"effectiveOperatingErrors":0,
"hardStopFailures":0,"overnightTurnFailures":0}}
configpath=ROOT/"config/optimizations/schedule_7_v1_4_0_release.json"
configpath.write_text(json.dumps(cfg,indent=2)+"\n")
release=build_optimization_release(configpath,ROOT)
package=ROOT/"data/schedules/schedule_7_v1_4_0"
canonical=json.loads((package/"canonical_schedule.json").read_text())
assert canonical["legs"]==draft["legs"]
assert canonical["schedule"]["status"]=="released"
assert "workingDraft" not in canonical["provenance"]
manifestpath=ROOT/"web/schedules.json"
manifest=json.loads(manifestpath.read_text())
name="schedule_7_v1_4_0"
assert manifest["defaultScheduleId"]=="schedule_7_v1_3_3"
assert not any(x["id"]==name for x in manifest["schedules"])
manifest["schedules"].append({"id":name,"label":"Schedule 7 · v1.4.0","files":{
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
assert old.startswith("# CAA Scheduler\n")
intro=("# CAA Scheduler\n\n## Latest published release\n\n"
"**Schedule 7 v1.4.0**, published October 19, 2026, is the application default: "
"**1,259 flights, 188 routes and 17 routing lines**, with zero effective operating errors. "
"New CRJ200 utilization includes R106, R110 and R160 extensions and two selective "
"SYR mini-banks (M15/M17). Logical DAY-M0 supports the approved R110 evening turn. "
"See [v1.4.0 release notes](docs/schedule_7_v1_4_0_release.md) and "
"[canonical schedule](data/schedules/schedule_7_v1_4_0/canonical_schedule.json).\n\n"
"## Historical v1.3.3 and earlier releases\n\n")
readme.write_text(intro+old[len("# CAA Scheduler\n"):])
print(json.dumps({"status":"candidate packaged; pending tests and main PR","schedule":name,
"manifestDefault":manifest["defaultScheduleId"],"summary":release["summary"]},indent=2))
