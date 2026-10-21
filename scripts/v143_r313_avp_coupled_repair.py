"""Joint R313 CLT-JAX-CLT and PHF-AVP feeder repair screen."""
import json,copy
from pathlib import Path
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads(Path("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json").read_text())
def clock(n):return f"{n//60%24:02d}:{n%60:02d}"
for shift in (55,60,65):
 s=copy.deepcopy(base)
 old=next(x for x in s["legs"] if x["flight"]==1379)
 old["departureMinute"]=650;old["arrivalMinute"]=716;old["departure"]="10:50";old["arrival"]="11:56"
 for a in s["bankAssignments"]:
  if a["legId"]==old["id"] and a["operation"]=="arrival":a["bankId"]="PHF-M12-V141"
 avp=next(x for x in s["legs"] if x["flight"]==1745)
 avp["departureMinute"]+=shift;avp["arrivalMinute"]+=shift;avp["departure"]=clock(avp["departureMinute"]);avp["arrival"]=clock(avp["arrivalMinute"])
 for a in s["bankAssignments"]:
  if a["legId"]==avp["id"] and a["operation"]=="departure":a["bankId"]="PHF-M12-V141"
 for i,(o,d,dep,arr) in enumerate([("CLT","JAX",422,493),("JAX","CLT",533,604)]):
  l={**old,"id":f"V143-R313-JAX-{i}","flight":3300+i,"pairing":3300+i,"origin":o,"destination":d,"departureMinute":dep,"arrivalMinute":arr,"departure":clock(dep),"arrival":clock(arr),"sequenceWithinRoute":i+2}
  s["legs"].append(l)
  for city,op,minute in [(o,"departure",dep),(d,"arrival",arr)]:
   if city not in s["operatingPolicy"]["hubs"]:continue
   match=[b for b in s["hubBanks"] if b["hub"]==city and b["startMinute"]<=minute<=b["endMinute"]]
   if len(match)==1:s["bankAssignments"].append(dict(legId=l["id"],operation=op,bankId=match[0]["id"]))
 for i,l in enumerate(sorted((x for x in s["legs"] if x["route"]==313),key=lambda y:y["departureMinute"]),1):l["sequenceWithinRoute"]=i
 op=validate_operating_rules(s)
 try:export_gate_schedule(s);gate=True
 except Exception as e:gate=str(e)
 print(json.dumps({"shift":shift,"gate":gate,"errors":op["summary"]["effectiveErrorFindings"],"structural":validate_schedule(s)["status"],"structuralFindings":[x for x in validate_schedule(s)["checks"] if x["status"]=="fail"],"overnight":validate_overnight_turns(s)["status"],"failed":[{"check":c["id"],"ids":[f["id"] for f in c["findings"] if "override" not in f][:8]} for c in op["checks"] if c["status"]=="fail"]}),flush=True)
