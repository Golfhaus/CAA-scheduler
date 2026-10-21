"""Screen an earlier gate-feasible SYR-RDU round trip with coordinated HVN arrival retime."""
import json,sys
from pathlib import Path
sys.path.insert(0,"src")
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads(Path("data/schedules/schedule_7_v1_4_1/canonical_schedule.json").read_text())
base["schedule"].update(id="schedule_7_v1_4_2_draft",status="draft")
leg=next(l for l in base["legs"] if l["flight"]==1879)
print("HVN original",leg["departure"],leg["arrival"],flush=True)
for shift in [-21,-25,-30,-35]:
 ov={"baseSchedule":{"scheduleId":"schedule_7_v1_4_2_draft"},"schedule":{"id":"schedule_7_v1_4_2_draft","status":"draft"},
 "retimeLegs":[{"legId":leg["id"],"departureMinute":leg["departureMinute"]+shift,"arrivalMinute":leg["arrivalMinute"]+shift}],
 "addRoutes":[{"route":802,"line":"V142-SYR","day":1,"fleet":"CRJ700","legs":[{"id":"V142-SYR-RDU","origin":"SYR","destination":"RDU","departureMinute":650,"arrivalMinute":740},{"id":"V142-RDU-SYR","origin":"RDU","destination":"SYR","departureMinute":780,"arrivalMinute":870}]}]}
 c=apply_optimization_overlay(base,ov)
 try:export_gate_schedule(c);gate="pass"
 except Exception as e:gate=str(e)
 v=validate_operating_rules(c)
 print(json.dumps({"hvnShift":shift,"hvnArrival":leg["arrivalMinute"]+shift,"connectionMinutes":650-(leg["arrivalMinute"]+shift),"gate":gate,"nativeErrors":v["summary"]["effectiveErrorFindings"],"failures":[{"check":x["id"],"findings":[f["id"] for f in x["findings"][:5]]} for x in v["checks"] if x["status"]=="fail"]}),flush=True)
