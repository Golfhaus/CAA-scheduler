"""R316 PHF arrival rebank, plus short PHF turn, screened on retained v1.4.3 draft."""
import json,copy
from pathlib import Path
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads(Path("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json").read_text())
def clock(n):return f"{n//60%24:02d}:{n%60:02d}"
for depart1294 in (930,960,990):
 for destination,block,turnDeparture in [("BWI",48,1140),("RDU",50,1130),("SAV",86,1100),("CLT",66,1100)]:
  s=copy.deepcopy(base)
  l=next(x for x in s["legs"] if x["flight"]==1294)
  change=depart1294-l["departureMinute"];l["departureMinute"]=depart1294;l["arrivalMinute"]+=change;l["departure"]=clock(depart1294);l["arrival"]=clock(l["arrivalMinute"])
  for a in s["bankAssignments"]:
   if a["legId"]==l["id"] and a["operation"]=="arrival":a["bankId"]="PHF-B6"
  if turnDeparture-l["arrivalMinute"]<40 or 1255-(turnDeparture+block*2+40)<40:continue
  add=[("PHF",destination,turnDeparture,turnDeparture+block),(destination,"PHF",turnDeparture+block+40,turnDeparture+block*2+40)]
  for i,(o,d,t,u) in enumerate(add):
   ident=f"V143-316-{destination}-{i}"
   s["legs"].append(dict(id=ident,route=316,line="AH",day=5,fleet="CRJ700",sequenceWithinRoute=0,pairing=3200+i,flight=3200+i,origin=o,destination=d,departureMinute=t,arrivalMinute=u,departure=clock(t),arrival=clock(u)))
   for c,op,m in [(o,"departure",t),(d,"arrival",u)]:
    if c not in s["operatingPolicy"]["hubs"]:continue
    b=[x for x in s["hubBanks"] if x["hub"]==c and x["startMinute"]<=m<=x["endMinute"]]
    if len(b)==1:s["bankAssignments"].append(dict(legId=ident,operation=op,bankId=b[0]["id"]))
  for i,x in enumerate(sorted((x for x in s["legs"] if x["route"]==316),key=lambda v:v["departureMinute"]),1):x["sequenceWithinRoute"]=i
  o=validate_operating_rules(s)
  try:export_gate_schedule(s);gate=True
  except Exception:gate=False
  print(json.dumps({"1294":clock(depart1294),"destination":destination,"gate":gate,"errors":o["summary"]["effectiveErrorFindings"],"structure":validate_schedule(s)["status"],"overnight":validate_overnight_turns(s)["status"]}),flush=True)
