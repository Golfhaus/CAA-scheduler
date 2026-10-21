"""Screen hold consolidation retimings of CRJ700 routes on v1.4.3 draft."""
import json,copy,sys
from pathlib import Path
sys.path.insert(0,"src")
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads(Path("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json").read_text())
def clock(n):return f"{n//60%24:02d}:{n%60:02d}"
candidates=[(303,1346,[800,810,840,870,900]),(313,1379,[425,440,455,480,510]),(316,1294,[900,930,960,990]),(339,2068,[350,375,400,420]),(319,1951,[690,705,720,735])]
for route,num,minutes in candidates:
 for t in minutes:
  s=copy.deepcopy(base)
  leg=next(l for l in s["legs"] if l["flight"]==num)
  delta=t-leg["departureMinute"];leg["departureMinute"]=t;leg["arrivalMinute"]+=delta;leg["departure"]=clock(t);leg["arrival"]=clock(leg["arrivalMinute"])
  o=validate_operating_rules(s)
  try:export_gate_schedule(s);gate="pass"
  except Exception as e:gate=str(e)
  failed=[{"check":x["id"],"findings":[f["id"] for f in x["findings"] if "override" not in f][:3]} for x in o["checks"] if x["status"]=="fail"]
  print(json.dumps({"route":route,"flight":num,"newDeparture":clock(t),"gate":gate,"errorCount":o["summary"]["effectiveErrorFindings"],"structure":validate_schedule(s)["status"],"overnight":validate_overnight_turns(s)["status"],"failed":failed}),flush=True)
