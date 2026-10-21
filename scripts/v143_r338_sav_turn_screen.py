"""Native SAV short-turn screen after gate-clean R338 PHF-SAV 14:30."""
import json,copy
from pathlib import Path
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.validation import validate_schedule
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads(Path("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json").read_text())
def clk(n):return f"{n//60%24:02d}:{n%60:02d}"
for dest,block in (("CHS",45),("MYR",60),("ILM",55),("JAX",45),("DAB",70),("CAE",55),("GSP",65)):
 for departure in (990,1005,1020):
  back=departure+block+40+block
  if back>1160:continue
  s=copy.deepcopy(base);old=next(l for l in s["legs"] if l["flight"]==1493)
  old["departureMinute"]=870;old["arrivalMinute"]=956;old["departure"]="14:30";old["arrival"]="15:56"
  for ass in s["bankAssignments"]:
   if ass["legId"]==old["id"] and ass["operation"]=="departure":
    cand=[b for b in s["hubBanks"] if b["hub"]=="PHF" and b["startMinute"]<=870<=b["endMinute"]]
    if len(cand)==1:ass["bankId"]=cand[0]["id"]
  for i,(o,d,t,u) in enumerate([("SAV",dest,departure,departure+block),(dest,"SAV",departure+block+40,back)]):
   s["legs"].append({"id":f"V143-R338-{dest}-{i}","route":338,"line":"AK","day":1,"fleet":"CRJ700","sequenceWithinRoute":0,"pairing":4100+i,"flight":4100+i,"origin":o,"destination":d,"departureMinute":t,"arrivalMinute":u,"departure":clk(t),"arrival":clk(u)})
  for i,x in enumerate(sorted((x for x in s["legs"] if x["route"]==338),key=lambda y:y["departureMinute"]),1):x["sequenceWithinRoute"]=i
  op=validate_operating_rules(s)
  try:export_gate_schedule(s);gate="pass"
  except Exception as e:gate=str(e)
  if gate=="pass" and op["summary"]["effectiveErrorFindings"]==0 and validate_schedule(s)["status"]=="pass" and validate_overnight_turns(s)["status"]=="pass":
   print(json.dumps({"destination":dest,"departure":clk(departure),"return":clk(back),"newBlock":block*2,"status":"NATIVE_PASS"}),flush=True)
