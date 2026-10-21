"""Cumulative nonpublishing v1.4.3 utilization concept; published v1.4.2 pinned.
No extra aircraft, no gate/stand increases, no policy changes.
"""
import json,copy,sys
from pathlib import Path
sys.path.insert(0,"src")
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
base=json.loads(Path("data/schedules/schedule_7_v1_4_2/canonical_schedule.json").read_text())
s=copy.deepcopy(base);s["schedule"].update(id="schedule_7_v1_4_3_draft",version="1.4.3-draft",label="Schedule 7 v1.4.3 draft",status="draft")
legs=[
 # R177 pre-SRQ feeder, scheduled to reach DAY 40 minutes before DAY-SRQ
 (177,"DAY","CMH",450,485),(177,"CMH","DAY",525,560),
 # R177 evening utilization, resumes 40 minutes after SRQ-DAY arrives
 (177,"DAY","SFB",975,1100),(177,"SFB","DAY",1145,1270),
 (178,"SYR","CHS",310,430),(178,"CHS","SYR",470,590),
 # R178 connects RDU to the Hartford corridor via Syracuse
 (178,"SYR","BDL",930,980),(178,"BDL","SYR",1025,1075),
 # Second BDL turn improves evening BWI and RFD onward connections.
 (178,"SYR","BDL",1170,1220),(178,"BDL","SYR",1260,1310),
 # R359 first high-demand return from BNA, then a second before BHM night bank
 (359,"BNA","FLL",360,545),(359,"FLL","BNA",590,655),
 (359,"BNA","DAL",780,885),(359,"DAL","BNA",930,1035)
]
def clk(v):return f"{v//60%24:02d}:{v%60:02d}"
directed={(x["origin"],x["destination"]):x["pairing"] for x in s["legs"]}
newpair=max(x["pairing"] for x in s["legs"])+1
num=max(x["flight"] for x in s["legs"])+1
hubs=set(s["operatingPolicy"]["hubs"])
for i,(route,origin,dest,dep,arr) in enumerate(legs):
 first=next(l for l in s["legs"] if l["route"]==route)
 ident=f"V143-R{route}-{origin}-{dest}-{i}"
 s["legs"].append({"id":ident,"route":route,"line":first["line"],"day":first["day"],"fleet":first["fleet"],"sequenceWithinRoute":0,"pairing":directed.get((origin,dest),newpair+i),"flight":num+i,"origin":origin,"destination":dest,"departureMinute":dep,"arrivalMinute":arr,"departure":clk(dep),"arrival":clk(arr)})
 for city,operation,minute in ((origin,"departure",dep),(dest,"arrival",arr)):
  if city not in hubs:continue
  possible=[b for b in s["hubBanks"] if b["hub"]==city and b["startMinute"]<=minute<=b["endMinute"]]
  if len(possible)==1:s["bankAssignments"].append({"legId":ident,"operation":operation,"bankId":possible[0]["id"]})
for route in (177,178,359):
 matches=sorted((l for l in s["legs"] if l["route"]==route),key=lambda x:x["departureMinute"])
 for seq,l in enumerate(matches,1):l["sequenceWithinRoute"]=seq
checks={"structural":validate_schedule(s),"overnight":validate_overnight_turns(s),"operating":validate_operating_rules(s)}
try:gates=export_gate_schedule(s);gate="pass"
except Exception as e:gates=None;gate=str(e)
report={"base":base["schedule"]["id"],"draft":s["schedule"]["id"],"newFlights":len(legs),"flights":len(s["legs"]),"gate":gate,"structural":checks["structural"]["status"],"overnight":checks["overnight"]["status"],"effectiveOperatingErrors":checks["operating"]["summary"]["effectiveErrorFindings"],"findings":[{"id":c["id"],"samples":[f["id"] for f in c["findings"] if "override" not in f][:12]} for c in checks["operating"]["checks"] if c["status"]=="fail"]}
print(json.dumps(report,indent=2),flush=True)
if report["structural"]=="pass" and report["overnight"]=="pass" and report["gate"]=="pass" and report["effectiveOperatingErrors"]==0:
 p=reconstruct_planning_snapshot(s,demand_data_version="bts-db1c-6mo-jul2025-apr2026-v7")
 pv=validate_planning_snapshot(p,s)
 print("PLANNING",pv["status"],flush=True)
 if pv["status"]=="pass":
  out=Path("data/schedules/schedule_7_v1_4_3_draft");out.mkdir(parents=True,exist_ok=True)
  for key,obj in {"canonical_schedule.json":s,"validation_report.json":checks["structural"],"operating_validation_report.json":checks["operating"],"overnight_turn_validation.json":checks["overnight"],"gates.json":gates,"planning_snapshot.json":p,"planning_validation_report.json":pv}.items():
   (out/key).write_text(json.dumps(obj,indent=2)+"\n")
  print("V143_COMBINED_VALIDATED",flush=True)
