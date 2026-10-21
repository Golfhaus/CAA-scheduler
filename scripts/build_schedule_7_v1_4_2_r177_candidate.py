"""Build tactical v1.4.2 + R177 AF day 7 candidate; keep unpublished."""
from pathlib import Path
import json,hashlib,sys,copy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.timetable import export_timetable
basepath=ROOT/"data/schedules/schedule_7_v1_4_1/canonical_schedule.json"
overlaypath=ROOT/"config/optimizations/schedule_7_v1_4_2_mci_tactical_candidate.json"
base=json.loads(basepath.read_text());s=apply_optimization_overlay(base,json.loads(overlaypath.read_text()))
for leg in s["legs"]:
 if leg["line"]=="AF" and leg["day"]>6:leg["day"]+=1
pair=max(leg["pairing"] for leg in s["legs"])+1
flight=max(leg["flight"] for leg in s["legs"])+1
pairs=[("DAY","SRQ",600,745),("SRQ","DAY",790,935)]
for i,(o,d,dep,arr) in enumerate(pairs):
 s["legs"].append({"id":f"V142-R177-{i+1}","route":177,"line":"AF","day":7,"fleet":"CRJ200","sequenceWithinRoute":i+1,"pairing":pair+i,"flight":flight+i,"origin":o,"destination":d,"departureMinute":dep,"arrivalMinute":arr,"departure":f"{dep//60:02d}:{dep%60:02d}","arrival":f"{arr//60:02d}:{arr%60:02d}"})
s["bankAssignments"] += [{"legId":"V142-R177-1","operation":"departure","bankId":"DAY-B3"},{"legId":"V142-R177-2","operation":"arrival","bankId":"DAY-B6"}]
reports={"validation_report.json":validate_schedule(s),"overnight_turn_validation.json":validate_overnight_turns(s),"operating_validation_report.json":validate_operating_rules(s)}
plan=reconstruct_planning_snapshot(s,demand_data_version="bts-db1c-6mo-jul2025-apr2026-v7")
reports["planning_snapshot.json"]=plan
reports["planning_validation_report.json"]=validate_planning_snapshot(plan,s)
reports["gates.json"]=export_gate_schedule(s)
reports["timetable.json"]=export_timetable(s)
assert reports["validation_report.json"]["status"]=="pass"
assert reports["overnight_turn_validation.json"]["status"]=="pass"
assert reports["planning_validation_report.json"]["status"]=="pass"
assert reports["operating_validation_report.json"]["summary"]["effectiveErrorFindings"]==0
assert (len(s["legs"]),len(set(x["route"] for x in s["legs"])))==(1268,189)
assert max(x["day"] for x in s["legs"] if x["line"]=="AF")==12
s.setdefault("provenance",{})["workingDraft"]={"status":"UNPUBLISHED v1.4.2 R177 provisional","baseline":"schedule_7_v1_4_1","baselineSha256":hashlib.sha256(basepath.read_bytes()).hexdigest(),"tacticalOverlay":str(overlaypath.relative_to(ROOT)),"addedRoute":177}
out=ROOT/"data/schedules/schedule_7_v1_4_2_r177_candidate"
out.mkdir(parents=True,exist_ok=True)
for filename,value in {"canonical_schedule.json":s,**reports}.items():(out/filename).write_text(json.dumps(value,indent=2)+"\n")
print(json.dumps({"candidate":str(out),"legs":1268,"routes":189,"lineAFDays":12,"effectiveErrors":0},indent=2))
