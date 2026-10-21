"""Search nearby time offsets for native gate feasibility; read-only."""
import sys,json
from pathlib import Path
sys.path.insert(0,"src")
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads(Path("data/schedules/schedule_7_v1_4_1/canonical_schedule.json").read_text())
base["schedule"].update(id="schedule_7_v1_4_2_draft",status="draft")
options={
"BNA_BHM":[("BHM","BNA",815,890),("BNA","BHM",930,1005),("BHM","BNA",1045,1120),("BNA","BHM",1160,1235),("BHM","BNA",1315,1390)],
"SYR_RDU":[("SYR","RDU",680,770),("RDU","SYR",810,900)]
}
for key,arr in options.items():
 print("SCENARIO",key,flush=True)
 for shift in [-45,-30,-20,-15,-10,0,10,15,20,30,45]:
  ov={"baseSchedule":{"scheduleId":"schedule_7_v1_4_2_draft"},"schedule":{"id":"schedule_7_v1_4_2_draft","status":"draft"},"addRoutes":[{"route":800+(key=="SYR_RDU"),"line":"V142-"+key,"day":1,"fleet":"CRJ700","legs":[{"id":f"{key}-{i}","origin":o,"destination":d,"departureMinute":dep+shift,"arrivalMinute":arrive+shift} for i,(o,d,dep,arrive) in enumerate(arr)]}]}
  try:
   c=apply_optimization_overlay(base,ov)
   g=export_gate_schedule(c)
   print(json.dumps({"shift":shift,"gates":"pass"}),flush=True)
  except Exception as exc:
   print(json.dumps({"shift":shift,"gates":"fail","error":str(exc)[:100]}),flush=True)
