"""R345 coordinated early inbound retime opens high-demand CLT-BWI round trip.
Does not disturb CLT-PHF or PHF-GSP, protects existing endpoint & line handoff.
"""
import json,copy
from pathlib import Path
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads(Path("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json").read_text())
def clk(m):return f"{m//60%24:02d}:{m%60:02d}"
for shift in (18,20,22,25):
 for dest,block in (("BWI",70),("PIT",70),("JAX",71)):
  s=copy.deepcopy(base)
  for n in (1408,1306):
   l=next(x for x in s["legs"] if x["flight"]==n)
   l["departureMinute"]-=shift;l["arrivalMinute"]-=shift;l["departure"]=clk(l["departureMinute"]);l["arrival"]=clk(l["arrivalMinute"])
   for a in s["bankAssignments"]:
    if a["legId"]!=l["id"]:continue
    t=l["departureMinute"] if a["operation"]=="departure" else l["arrivalMinute"]
    station=l["origin"] if a["operation"]=="departure" else l["destination"]
    bs=[b for b in s["hubBanks"] if b["hub"]==station and b["startMinute"]<=t<=b["endMinute"]]
    if len(bs)==1:a["bankId"]=bs[0]["id"]
  arrival=next(x for x in s["legs"] if x["flight"]==1306)["arrivalMinute"]
  dep=arrival+40;arr=dep+block;rev=arr+40;back=rev+block
  if back>990:continue
  for i,(orig,target,t,u) in enumerate([("CLT",dest,dep,arr),(dest,"CLT",rev,back)]):
   ident=f"V143-R345-{dest}-{i}"
   s["legs"].append(dict(id=ident,route=345,line="AS",day=6,fleet="CRJ700",sequenceWithinRoute=0,pairing=5600+i,flight=5600+i,origin=orig,destination=target,departureMinute=t,arrivalMinute=u,departure=clk(t),arrival=clk(u)))
  for i,x in enumerate(sorted([x for x in s["legs"] if x["route"]==345],key=lambda x:x["departureMinute"]),1):x["sequenceWithinRoute"]=i
  op=validate_operating_rules(s)
  try:export_gate_schedule(s);gate=True
  except Exception:gate=False
  structure=validate_schedule(s)["status"]
  if gate and structure=="pass" and op["summary"]["effectiveErrorFindings"]==0 and validate_overnight_turns(s)["status"]=="pass":
   print(json.dumps({"destination":dest,"advance":shift,"CLTdep":clk(dep),"CLTback":clk(back),"blockMinutes":block*2,"status":"PASS"}),flush=True)
  else:
   print(json.dumps({"destination":dest,"advance":shift,"gate":gate,"structure":structure,"errors":op["summary"]["effectiveErrorFindings"],"checks":[c["id"] for c in op["checks"] if c["status"]=="fail"]}),flush=True)
