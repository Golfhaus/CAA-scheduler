"""Package user-approved Schedule 7 v1.4.2 without analysis artifacts."""
from pathlib import Path
import json, hashlib, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_release import build_optimization_release
draft_path=ROOT/"data/schedules/schedule_7_v1_4_2_draft/canonical_schedule.json"
draft=json.loads(draft_path.read_text())
assert draft["schedule"]["id"]=="schedule_7_v1_4_2_draft"
assert draft["schedule"]["status"]=="draft"
assert (len(draft["legs"]),len({x["route"] for x in draft["legs"]}),len({x["line"] for x in draft["legs"]}))==(1272,191,17)
assert json.loads((ROOT/"data/schedules/schedule_7_v1_4_2_draft/operating_validation_report.json").read_text())["summary"]["effectiveErrorFindings"]==0
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_1/canonical_schedule.json").read_text())
assert draft["schedule"]["fleetCounts"]==base["schedule"]["fleetCounts"]
sha=hashlib.sha256(draft_path.read_bytes()).hexdigest()
name="schedule_7_v1_4_2"
cfg={
"schemaVersion":"1.0.0","id":"schedule-7-v1.4.2-release",
"sourceScheduleId":"schedule_7_v1_4_1",
"baseCanonical":str(draft_path.relative_to(ROOT)),"baseCanonicalSha256":sha,
"overlays":[],"overlaySha256":{},"outputDirectory":f"data/schedules/{name}",
"rejoinAvoidableTows":True,"dropWorkingDraftProvenance":True,
"demandDataVersion":"bts-db1c-6mo-jul2025-apr2026-v7",
"schedule":{"id":name,"number":7,"version":"1.4.2","label":"Schedule 7, Version 1.4.2","status":"released"},
"patchScope":{"kind":"connection_improvements_five_markets","timetableChanged":True,"routingChanged":True,
"description":"Approved v1.4.2 tactical BLV-HOU and OMA-BNA MCI retimings; R177 DAY-SRQ, R178 SYR-RDU, R359 BNA-BHM, R512 BLV-BNA retime and R705 BNA-MCI B9 bank correction; schedule 7 only hub ceiling disabled."},
"connectionAudit":{"hub":"SYR","groups":{"northeast":["BTV","HPN","MHT","PWM","ALB","ISP","BDL"],"other":["PIT","CAK","BUF","ORH","PHF","BGR","ROC"]}},
"connectionScopeDecision":{"status":"approved","approvedBy":"user","date":"2026-10-20",
"userInstruction":"Add all suggested route changes and additions to the 1.4.2 draft. Remove the ceiling on number of hubs a destination can serve for the remainder of schedule 7. Validate and publish 1.4.2 to main.",
"acceptedDraftSha256":sha,"review":"R105, R107, R108 and R162 accepted with R356 supporting retiming; R106/R167 unchanged. BTV-RFD preserved. Discard rejected R167 alternatives. ISP-BNA and ORH-PGD commercial tradeoffs documented."},
"expectedRelease":{"legs":1272,"routes":191,"lines":17,"effectiveOperatingErrors":0,"hardStopFailures":0,"overnightTurnFailures":0}}
cfgpath=ROOT/"config/optimizations/schedule_7_v1_4_2_release.json"
cfgpath.write_text(json.dumps(cfg,indent=2)+"\n")
release=build_optimization_release(cfgpath,ROOT)
canonical=json.loads((ROOT/f"data/schedules/{name}/canonical_schedule.json").read_text())
assert canonical["legs"]==draft["legs"]
assert canonical["schedule"]["status"]=="released"
assert "workingDraft" not in canonical.get("provenance",{})
manifestpath=ROOT/"web/schedules.json"
manifest=json.loads(manifestpath.read_text())
assert manifest["defaultScheduleId"]=="schedule_7_v1_4_1"
assert not any(item["id"]==name for item in manifest["schedules"])
manifest["schedules"].append({"id":name,"label":"Schedule 7 · v1.4.2","files":{
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
"**Schedule 7 v1.4.2**, published October 21, 2026, is the application default: "
"**1,272 flights, 191 routes and 17 routing lines**, with zero effective operating errors. "
"New R177 DAY–SRQ, R178 SYR–RDU and R359 BNA–BHM, with MCI, BLV–BNA and hub-bank retimings. Hub-count ceiling disabled for Schedule 7 only. "
"See [v1.4.2 release notes](docs/schedule_7_v1_4_2_release.md) and "
"[canonical schedule](data/schedules/schedule_7_v1_4_2/canonical_schedule.json).\n\n"
"## Historical v1.4.1 and earlier releases\n\n")
assert old.startswith("# CAA Scheduler\n")
readme.write_text(intro+old[len("# CAA Scheduler\n"):])
# Update latest-only regression fixtures while preserving past versions.
for rel in ("tests/test_latest_schedule_release.py","tests/test_latest_service_gains.py"):
 path=ROOT/rel
 data=path.read_text()
 data=data.replace('"schedule_7_v1_4_1": 1266}', '"schedule_7_v1_4_1": 1266, "schedule_7_v1_4_2": 1272}')
 data=data.replace('"schedule_7_v1_4_1"}', '"schedule_7_v1_4_1", "schedule_7_v1_4_2"}')
 data=data.replace('"schedule_7_v1_4_1" else 9', '"schedule_7_v1_4_1", "schedule_7_v1_4_2"} else 9')
 if rel.endswith("test_latest_service_gains.py"):
  data=data.replace('(15, 3061)', '(18, 5875) if SCHEDULE_ID == "schedule_7_v1_4_2" else (15, 3061)')
 path.write_text(data)
path=ROOT/"tests/test_routing_details.mjs"
data=path.read_text().replace('entry.id === "schedule_7_v1_4_1" ||', 'entry.id === "schedule_7_v1_4_2" || entry.id === "schedule_7_v1_4_1" ||')
path.write_text(data)
path=ROOT/"tests/test_web_console.mjs"
data=path.read_text()
data=data.replace('flights: latest.id === "schedule_7_v1_4_1" ?', 'flights: latest.id === "schedule_7_v1_4_2" ? 1272 : latest.id === "schedule_7_v1_4_1" ?')
data=data.replace('routes: latest.id === "schedule_7_v1_4_1" ||', 'routes: latest.id === "schedule_7_v1_4_2" ? 191 : latest.id === "schedule_7_v1_4_1" ||')
data=data.replace('lines: latest.id === "schedule_7_v1_4_1" ||', 'lines: latest.id === "schedule_7_v1_4_2" || latest.id === "schedule_7_v1_4_1" ||')
data=data.replace('markets: latest.id === "schedule_7_v1_4_1" ?', 'markets: latest.id === "schedule_7_v1_4_2" ? 600 : latest.id === "schedule_7_v1_4_1" ?')
data=data.replace('CRJ700: latest.id === "schedule_7_v1_4_1" ||', 'CRJ700: latest.id === "schedule_7_v1_4_2" ? 59 : latest.id === "schedule_7_v1_4_1" ||')
data=data.replace('CRJ900: latest.id === "schedule_7_v1_4_1" ||', 'CRJ900: latest.id === "schedule_7_v1_4_2" || latest.id === "schedule_7_v1_4_1" ||')
data=data.replace('CRJ200: 76,', 'CRJ200: latest.id === "schedule_7_v1_4_2" ? 78 : 76,')
path.write_text(data)
# Historical v1.4.1 near-miss and tactical-preview assertions are not valid
# against the new published v1.4.2, which already includes the six-minute fix.
path=ROOT/"tests/test_opportunity_analysis.mjs"
data=path.read_text()
marker='const v131FrozenAudit = buildServiceAnalysis(v131Canonical, demand, buildItineraries);'
data=data.replace(marker,marker+'\nconst v141Canonical = JSON.parse(await readFile(new URL("../data/schedules/schedule_7_v1_4_1/canonical_schedule.json", import.meta.url), "utf8"));\nconst v141FrozenAudit = buildServiceAnalysis(v141Canonical, demand, buildItineraries);')
start=data.index('test("completed repairs disappear from near-misses')
end=data.index('test("R307 DAY service creates',start)
chunk=data[start:end]
chunk=chunk.replace('baseline.nearMisses','v141FrozenAudit.nearMisses').replace('baseline.records','v141FrozenAudit.records')
chunk=chunk.replace('const original = JSON.stringify(canonical);','const original = JSON.stringify(v141Canonical);')
chunk=chunk.replace('const after = buildServiceAnalysis(retime(1357, 6), demand, buildItineraries);','const candidate = structuredClone(v141Canonical); const changed = candidate.legs.find((l) => l.flight === 1357); changed.departureMinute += 6; changed.arrivalMinute += 6; changed.departure = "10:31"; changed.arrival = "11:35";\n  const after = buildServiceAnalysis(candidate, demand, buildItineraries);')
chunk=chunk.replace('compareServiceAnalyses(baseline, after)','compareServiceAnalyses(v141FrozenAudit, after)')
chunk=chunk.replace('JSON.stringify(canonical), original','JSON.stringify(v141Canonical), original')
data=data[:start]+chunk+data[end:]
path.write_text(data)

print(json.dumps({"release":name,"summary":release["summary"],"default":manifest["defaultScheduleId"]},indent=2))
