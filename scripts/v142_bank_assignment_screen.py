"""Native screening for explicit DAY and Syracuse logical bank assignments."""
import json,copy,sys
from pathlib import Path
sys.path.insert(0,"src")
from caa_scheduler.operating_validation import validate_operating_rules
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.validation import validate_schedule
base=json.loads(Path("data/schedules/schedule_7_v1_4_1/canonical_schedule.json").read_text())
def add(base,name,line,after,route,legs):
 s=copy.deepcopy(base);s["schedule"].update(id="schedule_7_v1_4_2_draft",status="draft")
 for l in s["legs"]:
  if l["line"]==line and l["day"]>after:l["day"]+=1
 pairs={(l["origin"],l["destination"]):l["pairing"] for l in s["legs"]};fresh=max(l["pairing"] for l in s["legs"])+1
 for i,(o,d,t,u) in enumerate(legs):
  pair=pairs.get((o,d),fresh+i)
  s["legs"].append(dict(id=f"V142-{name}-{i}",route=route,line=line,day=after+1,fleet="CRJ200",flight=2280+i,pairing=pair,sequenceWithinRoute=i+1,origin=o,destination=d,departureMinute=t,arrivalMinute=u,departure=f"{t//60:02d}:{t%60:02d}",arrival=f"{u//60:02d}:{u%60:02d}"))
 return s
def report(s,label):
 v=validate_operating_rules(s)
 try:export_gate_schedule(s);g="pass"
 except Exception as e:g=str(e)
 a=[(c["id"],f["id"]) for c in v["checks"] for f in c["findings"] if "override" not in f]
 print(json.dumps(dict(case=label,structural=validate_schedule(s)["status"],gates=g,errors=v["summary"]["effectiveErrorFindings"],new=[list(x) for x in a if x[1].startswith("V142-") or x[1].startswith("HVN-SYR-CRJ200-02-OUT") or x[1]=="RDU"]),flush=True)
 return s
s=add(base,"DAY","AF",6,177,[("DAY","SRQ",600,745),("SRQ","DAY",790,935)])
s["bankAssignments"] += [{"legId":"V142-DAY-0","operation":"departure","bankId":"DAY-B3"},{"legId":"V142-DAY-1","operation":"arrival","bankId":"DAY-B6"}]
report(s,"DAY-assigned")
for shift in (-35,-40,-46,-50):
 for return_arr in (870,885,900):
  sy=add(base,"SYR","AC",8,178,[("SYR","RDU",650,740),("RDU","SYR",return_arr-90,return_arr)])
  l=next(l for l in sy["legs"] if l["flight"]==1879)
  l["departureMinute"]+=shift;l["arrivalMinute"]+=shift
  l["departure"]=f"{l['departureMinute']//60:02d}:{l['departureMinute']%60:02d}"
  l["arrival"]=f"{l['arrivalMinute']//60:02d}:{l['arrivalMinute']%60:02d}"
  sy["bankAssignments"]=[x for x in sy["bankAssignments"] if not(x["legId"]==l["id"] and x["operation"]=="arrival")]
  bank="SYR-M09" if l["arrivalMinute"]<=595 else "SYR-B3"
  sy["bankAssignments"] += [{"legId":l["id"],"operation":"arrival","bankId":bank},{"legId":"V142-SYR-0","operation":"departure","bankId":"SYR-B3"},{"legId":"V142-SYR-1","operation":"arrival","bankId":"SYR-M15"}]
  report(sy,f"SYR-{shift}-{return_arr}")
