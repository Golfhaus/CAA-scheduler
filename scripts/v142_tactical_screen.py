"""Read-only native feasibility screen for v1.4.2 tactical connection retimings."""
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.validation import validate_schedule
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_1/canonical_schedule.json").read_text())
def screen(changes):
 s=json.loads(json.dumps(base))
 for number,minute in changes:
  leg=next(l for l in s["legs"] if l["flight"]==number)
  shift=minute-leg["departureMinute"]
  for key in ("departureMinute","arrivalMinute"):
   leg[key]=(leg[key]+shift)%1440
  for key,min_key in (("departure","departureMinute"),("arrival","arrivalMinute")):
   n=leg[min_key];leg[key]=f"{n//60:02d}:{n%60:02d}"
 o=validate_operating_rules(s);n=validate_overnight_turns(s);v=validate_schedule(s)
 try:g=export_gate_schedule(s);gate="built"
 except Exception as e:gate=str(e)
 p=validate_planning_snapshot(reconstruct_planning_snapshot(s),s)
 return {"changes":changes,"structure":v["status"],"overnight":n["status"],"planning":p["status"],"gateExport":gate,"errors":o["summary"]["effectiveErrorFindings"],"failedChecks":[{"check":c["id"],"findings":c.get("findings",[])[:3]} for c in o["checks"] if c["status"]=="fail"],"overnightFailures":n.get("summary",{}),"planningFailures":p.get("summary",{})}
for c in [[(1357,631)],[(1077,884)],[(1357,631),(1077,884)]]:
 print(json.dumps(screen(c),indent=2))
