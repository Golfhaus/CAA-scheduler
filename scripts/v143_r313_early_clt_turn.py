"""Add an early CLT turn to R313 before retimed CLT-PHF, preserving rest."""
import copy,json
from pathlib import Path
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
s0=json.loads(Path("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json").read_text())
tz={c["code"]:{"Eastern":-4,"Central":-5,"Mountain":-6,"Pacific":-7}[c["timezone"]] for c in s0["cities"]}
def block(a,b):
 n=[l for l in s0["legs"] if l["origin"]==a and l["destination"]==b]
 return min(((l["arrivalMinute"]-l["departureMinute"]-(tz[b]-tz[a])*60)%1440 for l in n),default=None)
def clock(n):return f"{n//60%24:02d}:{n%60:02d}"
for to in ("JAX","DAY","BHM","SYR","MCI"):
 b1=block("CLT",to);b2=block(to,"CLT")
 print("BLOCK",to,b1,b2,flush=True)
 if not b1 or not b2:continue
 for cltdeparture in (645,650,655,660):
  departure=422;arr=departure+b1+(tz[to]-tz["CLT"])*60;rev=arr+40;end=rev+b2+(tz["CLT"]-tz[to])*60
  if end+40>cltdeparture:continue
  s=copy.deepcopy(s0);leg=next(x for x in s["legs"] if x["flight"]==1379)
  leg["departureMinute"]=cltdeparture;leg["arrivalMinute"]=cltdeparture+66
  leg["departure"]=clock(cltdeparture);leg["arrival"]=clock(cltdeparture+66)
  for ass in s["bankAssignments"]:
   if ass["legId"]==leg["id"] and ass["operation"]=="arrival":ass["bankId"]="PHF-M12-V141"
  for i,(orig,dest,d,a) in enumerate([("CLT",to,departure,arr),(to,"CLT",rev,end)]):
   ident=f"V143-R313-{to}-{i}"
   s["legs"].append(dict(id=ident,route=313,line="AH",day=2,fleet="CRJ700",sequenceWithinRoute=i+2,pairing=3300+i,flight=3300+i,origin=orig,destination=dest,departureMinute=d,arrivalMinute=a,departure=clock(d),arrival=clock(a)))
   for c,op,m in [(orig,"departure",d),(dest,"arrival",a)]:
    if c not in s["operatingPolicy"]["hubs"]:continue
    b=[bk for bk in s["hubBanks"] if bk["hub"]==c and bk["startMinute"]<=m<=bk["endMinute"]]
    if len(b)==1:s["bankAssignments"].append(dict(legId=ident,operation=op,bankId=b[0]["id"]))
  for i,x in enumerate(sorted([x for x in s["legs"] if x["route"]==313],key=lambda l:l["departureMinute"]),1):x["sequenceWithinRoute"]=i
  res=validate_operating_rules(s)
  try:export_gate_schedule(s);gate=True
  except Exception:gate=False
  if gate and res["summary"]["effectiveErrorFindings"]==0 and validate_schedule(s)["status"]=="pass" and validate_overnight_turns(s)["status"]=="pass":
   print(json.dumps({"dest":to,"CLTfirst":clock(departure),"turnBack":clock(end),"CLTPHF":clock(cltdeparture),"status":"PASS"}),flush=True)
