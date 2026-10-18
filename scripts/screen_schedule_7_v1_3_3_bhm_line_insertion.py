"""Read-only physical test: insert BHM R530 into CRJ900 AG at SYR day-8/9 boundary."""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads((ROOT/"data/schedules/schedule_7_v1_3_3_draft/canonical_schedule.json").read_text())
out=ROOT/"outputs/schedule_7_v1_3_3_bhm_line_insertion";out.mkdir(parents=True,exist_ok=True)
original={l["id"]:l for l in base["legs"]}
assert len(base["legs"])==1253
assert len({l["line"] for l in base["legs"]})==21
# Treat R530 as AG route-day 9, and move former AG day 9 R519 to AG day 10.
o={"baseSchedule":{"scheduleId":base["schedule"]["id"]},"schedule":base["schedule"],
  "routeReassignments":[
   {"sourceRoute":519,"expectedLine":"AG","expectedDay":9,"expectedFleet":"CRJ900","line":"AG","day":10},
   {"sourceRoute":530,"expectedLine":"BB","expectedDay":1,"expectedFleet":"CRJ900","line":"AG","day":9}]}
report={"strategy":"Place SYR-to-SYR route R530 between AG R518 and R519","changes":o["routeReassignments"],"baseFlights":len(base["legs"])}
try:
 c=apply_optimization_overlay(base,o)
 s=validate_schedule(c);oper=validate_operating_rules(c);overnight=validate_overnight_turns(c)
 planning=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
 try:g=export_gate_schedule(c);gate="pass"
 except Exception as e:g=None;gate=repr(e)
 report.update({"structure":s["status"],"overnight":overnight["status"],"planning":planning["status"],
 "operating":oper["summary"],"gate":gate,
 "failed":[{"id":x["id"],"findings":x["findings"][:8]} for x in oper["checks"] if x["status"]=="fail"],
 "counts":{"legs":len(c["legs"]),"lines":len({l["line"] for l in c["legs"]}),
 "fleetUse":next(x["metrics"] for x in oper["checks"] if x["id"]=="fleet_capacity")}})
 report["pass"]=s["status"]=="pass" and overnight["status"]=="pass" and planning["status"]=="pass" and oper["summary"]["effectiveErrorFindings"]==0 and gate=="pass"
 if report["pass"]:
  (out/"ag_insert_overlay.json").write_text(json.dumps(o,indent=2)+"\n")
  (out/"ag_insert_canonical.json").write_text(json.dumps(c,indent=2)+"\n")
except Exception as e:report["pass"]=False;report["exception"]=repr(e);report["trace"]=traceback.format_exc()[-1500:]
(out/"ag_insertion_screen.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({k:v for k,v in report.items() if k not in ("failed","trace")},indent=2))
