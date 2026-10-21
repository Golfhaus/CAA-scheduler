"""Screen R303 move from PNS ground time to MCI for additional short turns."""
import copy,json
from pathlib import Path
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads(Path("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json").read_text())
def fmt(n):return f"{n//60%24:02d}:{n%60:02d}"
for city,block in [("SGF",50),("TUL",58),("DSM",55),("OKC",65),("RFD",75),("OMA",50),("MEM",80)]:
 for outbound in [965,975,985,995]:
  s=copy.deepcopy(base);old=next(x for x in s["legs"] if x["flight"]==1346)
  old["departureMinute"]=800;old["arrivalMinute"]=925;old["departure"]="13:20";old["arrival"]="15:25"
  for ba in s["bankAssignments"]:
   if ba["legId"]==old["id"] and ba["operation"]=="arrival":ba["bankId"]="MCI-B7"
  in_time=outbound+block+40;back=in_time+block
  if back>1150:continue
  for i,(o,d,dep,arr) in enumerate([("MCI",city,outbound,outbound+block),(city,"MCI",in_time,back)]):
   leg=dict(id=f"V143-R303-{city}-{i}",route=303,line="AA",day=3,fleet="CRJ700",sequenceWithinRoute=0,pairing=3100+i,flight=3100+i,origin=o,destination=d,departureMinute=dep,arrivalMinute=arr,departure=fmt(dep),arrival=fmt(arr))
   s["legs"].append(leg)
   if o=="MCI" or d=="MCI":
    minute=dep if o=="MCI" else arr
    bs=[x for x in s["hubBanks"] if x["hub"]=="MCI" and x["startMinute"]<=minute<=x["endMinute"]]
    if len(bs)==1:s["bankAssignments"].append(dict(legId=leg["id"],operation="departure" if o=="MCI" else "arrival",bankId=bs[0]["id"]))
  for j,l in enumerate(sorted([x for x in s["legs"] if x["route"]==303],key=lambda x:x["departureMinute"]),1):l["sequenceWithinRoute"]=j
  v=validate_operating_rules(s)
  try:export_gate_schedule(s);gate=True
  except Exception:gate=False
  if gate and v["summary"]["effectiveErrorFindings"]==0 and validate_schedule(s)["status"]=="pass" and validate_overnight_turns(s)["status"]=="pass":
   print(json.dumps({"destination":city,"dep":fmt(outbound),"return":fmt(back),"flightTime":block*2,"result":"PASS"}),flush=True)
