"""Explore shifting R303's BHM originator earlier instead of upsetting PNS returns.
This preserves the 16:10 PNS->MCI feeder and may create an MCI early mini-turn.
"""
import copy,json
from pathlib import Path
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads(Path("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json").read_text())
def fmt(t):return f"{t//60%24:02d}:{t%60:02d}"
for originator in (290,300,310,320,330):
 for city,block in (("SGF",50),("OMA",50),("DSM",55),("TUL",58)):
  s=copy.deepcopy(base);l=next(x for x in s["legs"] if x["flight"]==1409)
  shift=originator-l["departureMinute"];l["departureMinute"]+=shift;l["arrivalMinute"]+=shift;l["departure"]=fmt(l["departureMinute"]);l["arrival"]=fmt(l["arrivalMinute"])
  for a in s["bankAssignments"]:
   if a["legId"]==l["id"] and a["operation"]=="arrival":
    match=[b for b in s["hubBanks"] if b["hub"]=="MCI" and b["startMinute"]<=l["arrivalMinute"]<=b["endMinute"]]
    if len(match)==1:a["bankId"]=match[0]["id"]
  dep=l["arrivalMinute"]+40;arr=dep+block;rev=arr+40;back=rev+block
  if back>595:continue
  for i,(a,b,d,u) in enumerate([("MCI",city,dep,arr),(city,"MCI",rev,back)]):
   ident=f"V143-R303-MORNING-{city}-{i}"
   s["legs"].append(dict(id=ident,route=303,line="AA",day=3,fleet="CRJ700",sequenceWithinRoute=0,pairing=4900+i,flight=4900+i,origin=a,destination=b,departureMinute=d,arrivalMinute=u,departure=fmt(d),arrival=fmt(u)))
   if a=="MCI" or b=="MCI":
    minute=d if a=="MCI" else u
    match=[bn for bn in s["hubBanks"] if bn["hub"]=="MCI" and bn["startMinute"]<=minute<=bn["endMinute"]]
    if len(match)==1:s["bankAssignments"].append(dict(legId=ident,operation="departure" if a=="MCI" else "arrival",bankId=match[0]["id"]))
  for i,x in enumerate(sorted([x for x in s["legs"] if x["route"]==303],key=lambda x:x["departureMinute"]),1):x["sequenceWithinRoute"]=i
  op=validate_operating_rules(s)
  try:export_gate_schedule(s);gate=True
  except Exception:gate=False
  if gate and op["summary"]["effectiveErrorFindings"]==0 and validate_schedule(s)["status"]=="pass" and validate_overnight_turns(s)["status"]=="pass":
   print(json.dumps({"BHMdepart":fmt(originator),"MCIarr":fmt(l["arrivalMinute"]),"destination":city,"turn":fmt(dep)+"-"+fmt(back),"minutes":block*2,"native":"PASS"}),flush=True)
