"""Native independent turn-feasibility screen atop released v1.4.2.
Models each candidate as an insertion within an existing aircraft-day, without fleet release.
"""
import json,copy,sys
from pathlib import Path
sys.path.insert(0,"src")
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads(Path("data/schedules/schedule_7_v1_4_2/canonical_schedule.json").read_text())
def clk(n):return f"{(n//60)%24:02d}:{n%60:02d}"
options=[
 (177,"SFB",[("DAY","SFB",975,1100),("SFB","DAY",1145,1270)]),
 (177,"PIE",[("DAY","PIE",975,1105),("PIE","DAY",1150,1280)]),
 (177,"BNA",[("DAY","BNA",975,980),("BNA","DAY",1025,1150)]),
 (177,"CMH",[("DAY","CMH",310,345),("CMH","DAY",390,425)]),
 (177,"CLT",[("DAY","CLT",355,430),("CLT","DAY",475,550)]),
 (178,"BDL",[("SYR","BDL",930,980),("BDL","SYR",1025,1075)]),
 (178,"CMH",[("SYR","CMH",930,1010),("CMH","SYR",1055,1135)]),
 (178,"CHS",[("SYR","CHS",310,430),("CHS","SYR",475,595)]),
 (178,"PVD",[("SYR","PVD",930,990),("PVD","SYR",1035,1095)]),
 (359,"DAL",[("BNA","DAL",360,405),("DAL","BNA",450,615)]),
 (359,"FLL",[("BNA","FLL",360,485),("FLL","BNA",530,655)]),
 (359,"PIE",[("BNA","PIE",360,465),("PIE","BNA",510,615)]),
 (359,"AUS",[("BNA","AUS",360,480),("AUS","BNA",525,645)]),
 (359,"RDU",[("BNA","RDU",360,505),("RDU","BNA",550,575)]),
]
# Some published legs cross timezones. Candidate minute values above are per-station local.
hubs=set(base["operatingPolicy"]["hubs"])
banks=base["hubBanks"]
pairings={(x["origin"],x["destination"]):x["pairing"] for x in base["legs"]}
new_pair=max(x["pairing"] for x in base["legs"])+1
num=max(x["flight"] for x in base["legs"])+1
for route,dst,flights in options:
 s=copy.deepcopy(base)
 ident=s["legs"][[x["route"] for x in s["legs"]].index(route)]
 for i,(a,b,dep,arr) in enumerate(flights):
  leg={"id":f"V143-{route}-{dst}-{i}","route":route,"line":ident["line"],"day":ident["day"],"fleet":ident["fleet"],"flight":num+i,"pairing":pairings.get((a,b),new_pair+i),"sequenceWithinRoute":0,"origin":a,"destination":b,"departureMinute":dep,"arrivalMinute":arr,"departure":clk(dep),"arrival":clk(arr)}
  s["legs"].append(leg)
  for city,operation,minute in ((a,"departure",dep),(b,"arrival",arr)):
   if city not in hubs:continue
   candidates=[bk for bk in banks if bk["hub"]==city and bk["startMinute"]<=minute<=bk["endMinute"]]
   if len(candidates)==1:s["bankAssignments"].append({"legId":leg["id"],"operation":operation,"bankId":candidates[0]["id"]})
 route_legs=[x for x in s["legs"] if x["route"]==route]
 route_legs.sort(key=lambda x:(x["departureMinute"]+1440 if x["departureMinute"]<180 else x["departureMinute"]))
 for i,x in enumerate(route_legs,1):x["sequenceWithinRoute"]=i
 structure=validate_schedule(s)
 overnight=validate_overnight_turns(s)
 operating=validate_operating_rules(s)
 try:export_gate_schedule(s);gate="pass"
 except Exception as e:gate=str(e)
 checks=[(c["id"],[f["id"] for f in c["findings"] if "override" not in f][:8]) for c in operating["checks"] if c["status"]=="fail"]
 print(json.dumps({"route":route,"destination":dst,"structure":structure["status"],"overnight":overnight["status"],"gates":gate,"operatingErrors":operating["summary"]["effectiveErrorFindings"],"failures":checks},default=str),flush=True)
