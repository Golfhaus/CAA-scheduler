"""R338 PHF/SAV hold concentration without breaking originator or terminator."""
import copy,json
from pathlib import Path
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
s0=json.loads(Path("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json").read_text())
def clk(x):return f"{x//60%24:02d}:{x%60:02d}"
for dep in (840,870,900,930,960,990,1020,1050):
 s=copy.deepcopy(s0);leg=next(l for l in s["legs"] if l["flight"]==1493)
 sh=dep-leg["departureMinute"];leg["departureMinute"]=dep;leg["arrivalMinute"]+=sh;leg["departure"]=clk(dep);leg["arrival"]=clk(leg["arrivalMinute"])
 for b in s["bankAssignments"]:
  if b["legId"]==leg["id"] and b["operation"]=="departure":
   m=[z for z in s["hubBanks"] if z["hub"]=="PHF" and z["startMinute"]<=dep<=z["endMinute"]]
   if len(m)==1:b["bankId"]=m[0]["id"]
 op=validate_operating_rules(s)
 try:export_gate_schedule(s);gate=True
 except Exception:gate=False
 print(json.dumps({"dep":clk(dep),"PHFhold":dep-793,"SAVhold":1200-(dep+86),"gate":gate,"errors":op["summary"]["effectiveErrorFindings"],"structure":validate_schedule(s)["status"],"overnight":validate_overnight_turns(s)["status"],"failed":[(c["id"],[f["id"] for f in c["findings"] if "override" not in f][:3]) for c in op["checks"] if c["status"]=="fail"]]}),flush=True)
