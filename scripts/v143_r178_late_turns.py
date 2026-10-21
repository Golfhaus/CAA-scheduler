"""Screen late R178 turns on top of the verified 12-flight draft; no main changes."""
import runpy,copy,json
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
v=runpy.run_path("scripts/build_schedule_7_v1_4_3_candidate.py")
base=v["s"]
choices=[("ROC",45),("ALB",50),("PWM",65),("PVD",65),("BTV",65),("BDL",50),("BUF",55),("HPN",60),("PIT",65),("CAK",70),("BGR",85),("ORH",60)]
banks=base["hubBanks"]
for dest,block in choices:
 for depart in (1115,1140,1170,1200):
  s=copy.deepcopy(base)
  arr=depart+block;backdep=arr+40;returntime=backdep+block
  for i,(origin,target,d,a) in enumerate([("SYR",dest,depart,arr),(dest,"SYR",backdep,returntime)]):
   leg={"id":f"V143-R178-LATE-{dest}-{i}","route":178,"line":"AC","day":9,"fleet":"CRJ200","sequenceWithinRoute":0,"pairing":3000+i,"flight":3000+i,"origin":origin,"destination":target,"departureMinute":d,"arrivalMinute":a,"departure":f"{d//60:02d}:{d%60:02d}","arrival":f"{a//60:02d}:{a%60:02d}"}
   s["legs"].append(leg)
   for code,operation,minute in [(origin,"departure",d),(target,"arrival",a)]:
    if code!="SYR":continue
    match=[b for b in banks if b["hub"]==code and b["startMinute"]<=minute<=b["endMinute"]]
    if len(match)==1:s["bankAssignments"].append({"legId":leg["id"],"operation":operation,"bankId":match[0]["id"]})
  for seq,l in enumerate(sorted([x for x in s["legs"] if x["route"]==178],key=lambda x:x["departureMinute"]),1):l["sequenceWithinRoute"]=seq
  o=validate_operating_rules(s)
  try:export_gate_schedule(s);gate=True
  except Exception as e:gate=False
  errors=o["summary"]["effectiveErrorFindings"]
  if gate and not errors and validate_schedule(s)["status"]=="pass" and validate_overnight_turns(s)["status"]=="pass":
   print(json.dumps({"destination":dest,"outbound":depart,"return":returntime,"blockTotal":block*2,"status":"PASS"}),flush=True)
