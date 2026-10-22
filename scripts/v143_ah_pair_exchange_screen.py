"""Cross-day AH reassignment feasibility: exchange PHF/SYR flight pairs, preserving endpoints."""
import json,copy
from pathlib import Path
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
s0=json.loads(Path("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json").read_text())
# Move a complete SYR-PHF-SYR turn from R319 to R316's SYR hold, while testing
# how R319 can retain its SYR origin and onward BWI/ABE service.
for first in (675,690,705):
 s=copy.deepcopy(s0)
 moved=[l for l in s["legs"] if l["flight"] in (1951,1952)]
 for l in moved:
  l["route"]=316;l["day"]=5;l["line"]="AH"
  shift=first-795
  l["departureMinute"]+=shift;l["arrivalMinute"]+=shift
  l["departure"]=f"{l['departureMinute']//60:02d}:{l['departureMinute']%60:02d}"
  l["arrival"]=f"{l['arrivalMinute']//60:02d}:{l['arrivalMinute']%60:02d}"
 for route in (316,319):
  for i,l in enumerate(sorted((x for x in s["legs"] if x["route"]==route),key=lambda x:x["departureMinute"]),1):l["sequenceWithinRoute"]=i
 o=validate_operating_rules(s)
 try:export_gate_schedule(s);gate=True
 except Exception as e:gate=str(e)
 v=validate_schedule(s)
 print(json.dumps({"first":first,"structural":v["status"],"gates":gate,"operatingErrors":o["summary"]["effectiveErrorFindings"],"failed":[{"id":c["id"],"findings":[f["id"] for f in c["findings"] if "override" not in f][:5]} for c in o["checks"] if c["status"]=="fail"]]}),flush=True)
