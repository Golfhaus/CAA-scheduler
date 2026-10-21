"""Native v1.4.2 insert-one-day cycle screens using precisely three spares.
All tests are hypothetical until native validation and commercial audits pass.
"""
from pathlib import Path
import json,sys,copy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot

base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_1/canonical_schedule.json").read_text())
def clock(n):return f"{n//60%24:02d}:{n%60:02d}"
def scenario(label,line,after,route,fleet,legs):
 c=copy.deepcopy(base)
 c["schedule"].update(id="schedule_7_v1_4_2_draft",version="1.4.2-draft",status="draft")
 for l in c["legs"]:
  if l["line"]==line and l["day"]>after:l["day"]+=1
 existing={(l["origin"],l["destination"]):l["pairing"] for l in c["legs"]}
 nextpair=max(l["pairing"] for l in c["legs"])+1
 nextflight=max(l["flight"] for l in c["legs"])+1
 for i,(origin,dest,depart,arrive) in enumerate(legs,1):
  pairing=existing.get((origin,dest))
  if pairing is None:pairing=nextpair;nextpair+=1;existing[origin,dest]=pairing
  c["legs"].append({"id":f"V142-{label}-{i}","route":route,"line":line,"fleet":fleet,"day":after+1,"sequenceWithinRoute":i,"pairing":pairing,"flight":nextflight+i-1,"origin":origin,"destination":dest,"departureMinute":depart,"arrivalMinute":arrive,"departure":clock(depart),"arrival":clock(arrive)})
 v=validate_schedule(c)
 n=validate_overnight_turns(c)
 o=validate_operating_rules(c)
 try:
  export_gate_schedule(c);gate="pass"
 except Exception as e:gate="fail: "+str(e)
 counts=[(l["line"],l["day"]) for l in c["legs"]]
 records={"scenario":label,"addedRoute":route,"addedFleet":fleet,"line":line,"lineDays":len(set(x[1] for x in counts if x[0]==line)),"structure":v["status"],"overnight":n["status"],"operatingErrors":o["summary"]["effectiveErrorFindings"],"gates":gate,"failedChecks":[{"check":x["id"],"count":len(x["findings"]),"samples":[f["id"] for f in x["findings"][:5]]} for x in o["checks"] if x["status"]=="fail"]}
 print(json.dumps(records,indent=2),flush=True)
 return c,records

candidates=[
 ("BNA","AH",5,359,"CRJ700",[("BNA","BHM",690,765),("BHM","BNA",815,890),("BNA","BHM",930,1005),("BHM","BNA",1045,1120),("BNA","BHM",1160,1235),("BHM","BNA",1315,1390)]),
 ("DAY","AF",6,177,"CRJ200",[("DAY","SRQ",600,745),("SRQ","DAY",790,935)]),
 ("SYR","AC",8,178,"CRJ200",[("SYR","RDU",650,740),("RDU","SYR",780,870)])
]
for args in candidates:scenario(*args)
