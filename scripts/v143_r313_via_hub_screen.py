"""R313 holistic replacement: CLT-PHF nonstop #1379 swapped for CLT-via-hub-PHF.
Proof-of-concept only; original flight number retained if feasible.
"""
import json,copy
from pathlib import Path
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.validation import validate_schedule
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads(Path("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json").read_text())
def clk(t):return f"{t//60%24:02d}:{t%60:02d}"
# Search existing directional block time rather than invented times.
def block(a,b):
 ls=[l for l in base["legs"] if l["origin"]==a and l["destination"]==b]
 if not ls:return None
 zones={c["code"]:{"Eastern":-4,"Central":-5,"Mountain":-6,"Pacific":-7}[c["timezone"]] for c in base["cities"]}
 return min((l["arrivalMinute"]-l["departureMinute"]-(zones[b]-zones[a])*60)%1440 for l in ls)
for mid in ["DAY","JAX","SYR","BHM","MCI"]:
 first,second=block("CLT",mid),block(mid,"PHF")
 print("BLOCK",mid,first,second,flush=True)
 if first is None or second is None:continue
 for departure in [425,435,445,455,465,475]:
  arrival=departure+first+({"Eastern":-4,"Central":-5}[next(c["timezone"] for c in base["cities"] if c["code"]==mid)]-(-4))*60
  nextdep=arrival+40
  phfarr=nextdep+second+(-4-{"Eastern":-4,"Central":-5}[next(c["timezone"] for c in base["cities"] if c["code"]==mid)])*60
  if phfarr>835:continue
  s=copy.deepcopy(base)
  old=next(l for l in s["legs"] if l["flight"]==1379)
  s["legs"].remove(old)
  s["bankAssignments"]=[a for a in s["bankAssignments"] if a["legId"]!=old["id"]]
  for i,(origin,dest,dep,arr) in enumerate([("CLT",mid,departure,arrival),(mid,"PHF",nextdep,phfarr)]):
   ident=f"V143-R313-VIA-{mid}-{i}"
   s["legs"].append({**old,"id":ident,"flight":3100+i,"origin":origin,"destination":dest,"departureMinute":dep,"arrivalMinute":arr,"departure":clk(dep),"arrival":clk(arr),"sequenceWithinRoute":i+2})
   for code,operation,minute in [(origin,"departure",dep),(dest,"arrival",arr)]:
    if code not in s["operatingPolicy"]["hubs"]:continue
    match=[b for b in s["hubBanks"] if b["hub"]==code and b["startMinute"]<=minute<=b["endMinute"]]
    if len(match)==1:s["bankAssignments"].append({"legId":ident,"operation":operation,"bankId":match[0]["id"]})
  for j,l in enumerate(sorted([x for x in s["legs"] if x["route"]==313],key=lambda l:l["departureMinute"]),1):l["sequenceWithinRoute"]=j
  result=validate_operating_rules(s)
  try:export_gate_schedule(s);gate=True
  except Exception:gate=False
  if gate and result["summary"]["effectiveErrorFindings"]==0 and validate_schedule(s)["status"]=="pass" and validate_overnight_turns(s)["status"]=="pass":
   print(json.dumps({"hub":mid,"dep":clk(departure),"hubArr":clk(arrival),"hubDep":clk(nextdep),"PHFArr":clk(phfarr),"status":"PASS"}),flush=True)
