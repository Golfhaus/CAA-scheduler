"""Construct v1.4.2 proposed full candidate with four-leg R359 option.
Read-only validation. Never updates manifest or publishes.
"""
import json,copy,sys
from pathlib import Path
sys.path.insert(0,"src")
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.timetable import export_timetable

root=Path("data/schedules/schedule_7_v1_4_2_r177_candidate")
s=json.loads((root/"canonical_schedule.json").read_text())
s["operatingPolicy"]["hubCountCeilingEnabled"]=False
s["schedule"]["id"]="schedule_7_v1_4_2_draft"
def clock(n):return f"{n//60%24:02d}:{n%60:02d}"
def add_day(line,after,route,fleet,legs,tag):
 for x in s["legs"]:
  if x["line"]==line and x["day"]>after:x["day"]+=1
 nextpair=max(x["pairing"] for x in s["legs"])+1
 nextnum=max(x["flight"] for x in s["legs"])+1
 pairing={(x["origin"],x["destination"]):x["pairing"] for x in s["legs"]}
 for i,(a,b,dep,arr) in enumerate(legs):
  s["legs"].append(dict(id=f"V142-{tag}-{i+1}",route=route,line=line,day=after+1,fleet=fleet,sequenceWithinRoute=i+1,flight=nextnum+i,pairing=pairing.get((a,b),nextpair+i),origin=a,destination=b,departureMinute=dep,arrivalMinute=arr,departure=clock(dep),arrival=clock(arr)))
 return [x for x in s["legs"] if x["route"]==route]
# R178: reroute HVN feeder to open SYR's M09; 59-minute dwell before SYR/RDU flight.
leg=next(x for x in s["legs"] if x["flight"]==1879)
leg["departureMinute"]-=50;leg["arrivalMinute"]-=50
leg["departure"]=clock(leg["departureMinute"]);leg["arrival"]=clock(leg["arrivalMinute"])
for x in s["bankAssignments"]:
 if x["legId"]==leg["id"] and x["operation"]=="arrival":x["bankId"]="SYR-M09"
r178=add_day("AC",8,178,"CRJ200",[("SYR","RDU",650,740),("RDU","SYR",795,885)],"R178")
s["bankAssignments"] += [dict(legId=r178[0]["id"],operation="departure",bankId="SYR-B3"),dict(legId=r178[1]["id"],operation="arrival",bankId="SYR-M15")]
# Try slim four-leg R359: preserves BNA->OMA, BNA->ECP, ECP->BNA.
times=[("BNA","BHM",930,1005),("BHM","BNA",1045,1120),("BNA","BHM",1160,1235),("BHM","BNA",1315,1390)]
if len(sys.argv)>1:
 vals=[int(x) for x in sys.argv[1].split(",")]
 if len(vals)==4:times=[(a,b,t+vals[i],u+vals[i]) for i,(a,b,t,u) in enumerate(times)]
r359=add_day("AH",5,359,"CRJ700",times,"R359")
struct=validate_schedule(s);overnight=validate_overnight_turns(s);operating=validate_operating_rules(s)
try:gates=export_gate_schedule(s);gate_status="pass"
except Exception as e:gates=None;gate_status=str(e)
print(json.dumps({"candidateLegs":len(s["legs"]),"routes":len(set(x["route"] for x in s["legs"])),"lines":len(set(x["line"] for x in s["legs"])),"status":{"structural":struct["status"],"overnight":overnight["status"],"gate":gate_status,"operatingErrors":operating["summary"]["effectiveErrorFindings"]},"checks":[{"id":c["id"],"new":[f["id"] for f in c["findings"] if "override" not in f][:12]} for c in operating["checks"] if c["status"]=="fail"]},indent=2))
Path("outputs/schedule_7_v1_4_2").mkdir(parents=True,exist_ok=True)
Path("outputs/schedule_7_v1_4_2/construction_screen.json").write_text(json.dumps({"gate":gate_status,"operating":operating},indent=2))
if struct["status"]=="pass" and overnight["status"]=="pass" and gate_status=="pass" and operating["summary"]["effectiveErrorFindings"]==0:
 p=reconstruct_planning_snapshot(s,demand_data_version="bts-db1c-6mo-jul2025-apr2026-v7");pv=validate_planning_snapshot(p,s)
 if pv["status"]=="pass":
  out=Path("data/schedules/schedule_7_v1_4_2_draft");out.mkdir(parents=True,exist_ok=True)
  for n,o in {"canonical_schedule.json":s,"validation_report.json":struct,"overnight_turn_validation.json":overnight,"operating_validation_report.json":operating,"gates.json":gates,"timetable.json":export_timetable(s),"planning_snapshot.json":p,"planning_validation_report.json":pv}.items():(out/n).write_text(json.dumps(o,indent=2)+"\n")
  print("VALIDATED_CANDIDATE")
