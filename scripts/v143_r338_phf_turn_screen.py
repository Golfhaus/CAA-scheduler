"""R338 alternative: extend PHF hold, PHF out-and-back, preserve 20:00 SAV-JAX."""
import json,copy
from pathlib import Path
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.validation import validate_schedule
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads(Path("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json").read_text())
def clock(n):return f"{n//60%24:02d}:{n%60:02d}"
for destination,block in [("BWI",48),("RDU",50),("ORF",40),("CLT",66),("SAV",86),("RIC",40)]:
 for departure in (833,843,853,863):
  for later in (990,1020):
   back=departure+block*2+40
   if back+40>later:continue
   s=copy.deepcopy(base); leg=next(l for l in s["legs"] if l["flight"]==1493)
   leg["departureMinute"]=later;leg["arrivalMinute"]=later+86;leg["departure"]=clock(later);leg["arrival"]=clock(later+86)
   for ass in s["bankAssignments"]:
    if ass["legId"]==leg["id"] and ass["operation"]=="departure":
     match=[b for b in s["hubBanks"] if b["hub"]=="PHF" and b["startMinute"]<=later<=b["endMinute"]]
     if len(match)==1:ass["bankId"]=match[0]["id"]
   for i,(origin,dest,t,u) in enumerate([("PHF",destination,departure,departure+block),(destination,"PHF",departure+block+40,back)]):
    q=dict(id=f"V143-R338-PHF-{destination}-{i}",route=338,line="AK",day=1,fleet="CRJ700",sequenceWithinRoute=0,pairing=4700+i,flight=4700+i,origin=origin,destination=dest,departureMinute=t,arrivalMinute=u,departure=clock(t),arrival=clock(u))
    s["legs"].append(q)
    if origin=="PHF" or dest=="PHF":
     minute=t if origin=="PHF" else u
     bank=[b for b in s["hubBanks"] if b["hub"]=="PHF" and b["startMinute"]<=minute<=b["endMinute"]]
     if len(bank)==1:s["bankAssignments"].append(dict(legId=q["id"],operation="departure" if origin=="PHF" else "arrival",bankId=bank[0]["id"]))
   for i,l in enumerate(sorted([x for x in s["legs"] if x["route"]==338],key=lambda z:z["departureMinute"]),1):l["sequenceWithinRoute"]=i
   op=validate_operating_rules(s)
   try:export_gate_schedule(s);gate=True
   except Exception:gate=False
   if gate and op["summary"]["effectiveErrorFindings"]==0 and validate_schedule(s)["status"]=="pass" and validate_overnight_turns(s)["status"]=="pass":
    print(json.dumps(dict(destination=destination,departure=clock(departure),returnTime=clock(back),SAVDeparture=clock(later),addedFlying=block*2,status="PASS")),flush=True)
