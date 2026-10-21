"""Negative/positive native screen of hypothetical service as independent one-day routes.
Not a release candidate: these are intentionally NOT cyclic ten-day lines.
"""
import json,sys,copy
from pathlib import Path
sys.path.insert(0,"src")
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads(Path("data/schedules/schedule_7_v1_4_1/canonical_schedule.json").read_text())
base["schedule"]["id"]="schedule_7_v1_4_2_draft"
base["schedule"]["status"]="draft"
ideas=[
 ("BNA_BHM",801,"V142A","CRJ700",[("BHM","BNA",815,890),("BNA","BHM",930,1005),("BHM","BNA",1045,1120),("BNA","BHM",1160,1235),("BHM","BNA",1315,1390)]),
 ("SYR_RDU",802,"V142B","CRJ700",[("SYR","RDU",680,770),("RDU","SYR",810,900)]),
 ("DAY_SRQ",803,"V142C","CRJ700",[("DAY","SRQ",600,745),("SRQ","DAY",790,935)]),
]
for key,route,line,fleet,legs in ideas:
 ov={"schemaVersion":"1.0.0","baseSchedule":{"scheduleId":"schedule_7_v1_4_2_draft"},
 "schedule":{"id":"schedule_7_v1_4_2_draft","status":"draft"},
 "addRoutes":[{"route":route,"line":line,"day":1,"fleet":fleet,"legs":[{"id":f"V142-{key}-{i}","origin":o,"destination":d,"departureMinute":dep,"arrivalMinute":arr} for i,(o,d,dep,arr) in enumerate(legs)]}]}
 try:
  c=apply_optimization_overlay(base,ov)
  operating=validate_operating_rules(c)
  summary={"idea":key,"structural":validate_schedule(c)["status"],"effectiveErrors":operating["summary"]["effectiveErrorFindings"],"failedChecks":[{"id":x["id"],"count":len(x["findings"]),"samples":[f["id"] for f in x["findings"][:4]]} for x in operating["checks"] if x["status"]=="fail"]}
  try:
   gate=export_gate_schedule(c)
   summary["gates"]="export success"
  except Exception as e:summary["gates"]=str(e)
  print(json.dumps(summary,indent=2))
 except Exception as e:print(json.dumps({"idea":key,"exception":str(e)}))
