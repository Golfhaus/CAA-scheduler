"""Cross-day AH line pair exchange test: R317 afternoon RFD vs R319 PHF.
Both aircraft days stay anchored at SYR around exchange and retain original route endpoints.
"""
import json,copy
from pathlib import Path
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads(Path("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json").read_text())
def clk(n):return f"{n//60%24:02d}:{n%60:02d}"
# Source pairs: R317 #2103 #2104, R319 #1951 #1952.
for phfout in (990,1000,1010):
 for rfdout in (720,730,740):
  s=copy.deepcopy(base)
  specs=[(2103,319,rfdout,54),(2104,319,rfdout+114,174),(1951,317,phfout,85),(1952,317,phfout+125,85)]
  for number,route,dep,block in specs:
   l=next(x for x in s["legs"] if x["flight"]==number)
   l["route"]=route;l["day"]=7 if route==317 else 9
   l["departureMinute"]=dep;l["arrivalMinute"]=dep+block
   l["departure"]=clk(dep);l["arrival"]=clk(dep+block)
   for a in s["bankAssignments"]:
    if a["legId"]!=l["id"]:continue
    t=dep if a["operation"]=="departure" else dep+block
    airport=l["origin"] if a["operation"]=="departure" else l["destination"]
    candidates=[b for b in s["hubBanks"] if b["hub"]==airport and b["startMinute"]<=t<=b["endMinute"]]
    if len(candidates)==1:a["bankId"]=candidates[0]["id"]
  for route in (317,319):
   for idx,l in enumerate(sorted([x for x in s["legs"] if x["route"]==route],key=lambda x:x["departureMinute"]),1):l["sequenceWithinRoute"]=idx
  validation=validate_operating_rules(s)
  try:export_gate_schedule(s);gate="pass"
  except Exception as e:gate=str(e)
  print(json.dumps({"PHFstart":clk(phfout),"RFDstart":clk(rfdout),"gate":gate,"structure":validate_schedule(s)["status"],"overnight":validate_overnight_turns(s)["status"],"errors":validation["summary"]["effectiveErrorFindings"],"failed":[{"id":c["id"],"sample":[f["id"] for f in c["findings"] if "override" not in f][:6]} for c in validation["checks"] if c["status"]=="fail"]]}),flush=True)
