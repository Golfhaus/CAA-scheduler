"""Screen genuinely high-demand R345 CLT turns, retaining original CLT-PHF.
Previous short market screen missed RDU and large regional markets.
"""
import json,copy
from pathlib import Path
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.validation import validate_schedule
from caa_scheduler.gate_export import export_gate_schedule
c=json.loads(Path("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json").read_text())
def clk(n):return f"{n//60%24:02d}:{n%60:02d}"
for dst,block in [("RDU",55),("PIT",70),("BWI",70),("CHS",70),("JAX",71),("DAY",77),("BNA",85)]:
 for dep in (827,840,850):
  arr=dep+block+({"BNA":-60}.get(dst,0));rev=arr+40;back=rev+block+({"BNA":60}.get(dst,0))
  if back>990:continue
  s=copy.deepcopy(c)
  for i,(o,d,t,u) in enumerate([("CLT",dst,dep,arr),(dst,"CLT",rev,back)]):
   leg=dict(id=f"V143-R345-{dst}-{i}",route=345,line="AS",day=6,fleet="CRJ700",sequenceWithinRoute=0,pairing=5200+i,flight=5200+i,origin=o,destination=d,departureMinute=t,arrivalMinute=u,departure=clk(t),arrival=clk(u))
   s["legs"].append(leg)
   for airport,op,minute in [(o,"departure",t),(d,"arrival",u)]:
    if airport not in s["operatingPolicy"]["hubs"]:continue
    matches=[b for b in s["hubBanks"] if b["hub"]==airport and b["startMinute"]<=minute<=b["endMinute"]]
    if len(matches)==1:s["bankAssignments"].append(dict(legId=leg["id"],operation=op,bankId=matches[0]["id"]))
  for i,x in enumerate(sorted((l for l in s["legs"] if l["route"]==345),key=lambda x:x["departureMinute"]),1):x["sequenceWithinRoute"]=i
  op=validate_operating_rules(s)
  try:export_gate_schedule(s);gate=True
  except Exception:gate=False
  if gate and op["summary"]["effectiveErrorFindings"]==0 and validate_schedule(s)["status"]=="pass" and validate_overnight_turns(s)["status"]=="pass":
   print(json.dumps({"dst":dst,"out":clk(dep),"back":clk(back),"flightMinutes":block*2,"status":"PASS"}),flush=True)
  else:
   print(json.dumps({"dst":dst,"out":clk(dep),"back":clk(back),"gate":gate,"errors":op["summary"]["effectiveErrorFindings"],"failures":[x["id"] for x in op["checks"] if x["status"]=="fail"]]}),flush=True)
