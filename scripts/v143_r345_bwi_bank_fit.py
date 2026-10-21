"""Targeted R345 CLT-BWI 65-minute block with SYR bank-window-safe feeder retimes."""
import copy,json
from pathlib import Path
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
s0=json.loads(Path("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json").read_text())
def clock(t):return f"{t//60%24:02d}:{t%60:02d}"
for shiftJAX,shiftSYR in [(8,10),(6,8),(8,8)]:
 for block in (62,65,66):
  s=copy.deepcopy(s0)
  for n,shift in [(1408,shiftJAX),(1306,shiftSYR)]:
   l=next(x for x in s["legs"] if x["flight"]==n)
   l["departureMinute"]-=shift;l["arrivalMinute"]-=shift;l["departure"]=clock(l["departureMinute"]);l["arrival"]=clock(l["arrivalMinute"])
  t=next(x for x in s["legs"] if x["flight"]==1306)["arrivalMinute"]+40
  a=t+block;r=a+40;back=r+block
  if back>990:continue
  for i,(o,d,dep,arr) in enumerate([("CLT","BWI",t,a),("BWI","CLT",r,back)]):
   s["legs"].append(dict(id=f"V143-345-BWI-{i}",route=345,line="AS",day=6,fleet="CRJ700",flight=5400+i,pairing=5400+i,sequenceWithinRoute=0,origin=o,destination=d,departureMinute=dep,arrivalMinute=arr,departure=clock(dep),arrival=clock(arr)))
  for i,x in enumerate(sorted([x for x in s["legs"] if x["route"]==345],key=lambda x:x["departureMinute"]),1):x["sequenceWithinRoute"]=i
  op=validate_operating_rules(s)
  try:export_gate_schedule(s);gate=True
  except Exception:gate=False
  print(json.dumps({"JAXshift":shiftJAX,"SYRshift":shiftSYR,"block":block,"CLTdeparture":clock(t),"CLTreturn":clock(back),"gate":gate,"errors":op["summary"]["effectiveErrorFindings"],"structure":validate_schedule(s)["status"],"overnight":validate_overnight_turns(s)["status"],"failures":[{"id":c["id"],"sample":[f["id"] for f in c["findings"] if "override" not in f][:4]} for c in op["checks"] if c["status"]=="fail"]}),flush=True)
