"""Compare actual novel operating findings against baseline, and test coordinated SYR bank retime."""
import json,copy,sys
from pathlib import Path
sys.path.insert(0,"src")
from caa_scheduler.operating_validation import validate_operating_rules
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.optimization_overlay import apply_optimization_overlay
base=json.loads(Path("data/schedules/schedule_7_v1_4_1/canonical_schedule.json").read_text())
def failures(s):
 r=validate_operating_rules(s)
 return {(c["id"],f["id"]) for c in r["checks"] for f in c["findings"] if "override" not in f},r
before,_=failures(base)
print("BASELINE",len(before),sorted(before)[:15],flush=True)
def clock(n):return f"{n//60%24:02d}:{n%60:02d}"
for name,line,day,route,fleet,legs in [
 ("DAY","AF",6,177,"CRJ200",[("DAY","SRQ",600,745),("SRQ","DAY",790,935)]),
 ("SYR","AC",8,178,"CRJ200",[("SYR","RDU",650,740),("RDU","SYR",780,870)])
]:
 s=copy.deepcopy(base);s["schedule"].update(id="schedule_7_v1_4_2_draft",status="draft")
 for l in s["legs"]:
  if l["line"]==line and l["day"]>day:l["day"]+=1
 pairs={(l["origin"],l["destination"]):l["pairing"] for l in s["legs"]};num=max(l["pairing"] for l in s["legs"])+1
 for i,(origin,destination,dep,arr) in enumerate(legs):
  pair=pairs.get((origin,destination))
  if pair is None:pair=num;num+=1
  s["legs"].append(dict(id=f"V142-{name}-{i}",route=route,line=line,fleet=fleet,day=day+1,sequenceWithinRoute=i+1,pairing=pair,flight=2280+i,origin=origin,destination=destination,departureMinute=dep,arrivalMinute=arr,departure=clock(dep),arrival=clock(arr)))
 if name=="SYR":
  for l in s["legs"]:
   if l["flight"]==1879:
    l["departureMinute"]-=30;l["arrivalMinute"]-=30;l["departure"]=clock(l["departureMinute"]);l["arrival"]=clock(l["arrivalMinute"])
  for assignment in s["bankAssignments"]:
   if assignment["legId"]==next(l["id"] for l in s["legs"] if l["flight"]==1879) and assignment["operation"]=="arrival":
    assignment["bankId"]="SYR-B2"
 after,report=failures(s)
 try:export_gate_schedule(s);gates="pass"
 except Exception as e:gates=str(e)
 print(json.dumps(dict(candidate=name,novel=sorted(after-before),resolved=sorted(before-after),effectiveErrors=report["summary"]["effectiveErrorFindings"],gates=gates),indent=2),flush=True)
