"""Screen tightly bank-aligned v1.4.0 midday route extensions and DAY midnight bank."""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
b=json.loads((ROOT/"data/schedules/schedule_7_v1_3_3/canonical_schedule.json").read_text())
flights={l["flight"]:l for l in b["legs"]}
cases=[
 {"name":"R160 keep BTV, add SYR-ROC-SYR, delay PWM terminator","route":160,
 "retimes":[(1701,1180,1248)],"legs":[("SYR","ROC",1007,1046),("ROC","SYR",1086,1125)],
 "banks":[(1,"departure","SYR-B5"),(2,"arrival","SYR-B6")]},
 {"name":"R107 retime BDL, add SYR-SWF-SYR, late CAK","route":107,
 "retimes":[(1792,812,866),(1791,906,960),(1674,1180,1251)],
 "legs":[("SYR","SWF",1000,1049),("SWF","SYR",1089,1138)],
 "banks":[(1,"departure","SYR-B5"),(2,"arrival","SYR-B6")]},
 {"name":"R110 DAY-SYR-DAY using new midnight DAY arrival mini-bank","route":110,
 "retimes":[(1794,1119,1176)],
 "legs":[("DAY","SYR",1216,1309),("SYR","DAY",1349,1442)],
 "banks":[(1,"departure","DAY-B8"),(1,"arrival","SYR-B7"),(2,"departure","SYR-B7"),(2,"arrival","DAY-M0")],
 "newBank":{"id":"DAY-M0","hub":"DAY","startMinute":0,"endMinute":45}},
]
results=[]
for index,item in enumerate(cases):
 record={"name":item["name"],"route":item["route"],"kind":"read-only feasibility"}
 try:
  ov={"id":f"v140-focused-{index}","baseSchedule":{"scheduleId":b["schedule"]["id"]},"schedule":b["schedule"],
      "retimeLegs":[],"insertLegs":[],"bankAssignmentsToAdd":[]}
  for number,dep,arr in item["retimes"]:
   l=flights[number];assert l["route"]==item["route"]
   assert (l["arrivalMinute"]-l["departureMinute"])%1440==(arr-dep)%1440
   ov["retimeLegs"].append({"legId":l["id"],"expectedDepartureMinute":l["departureMinute"],"expectedArrivalMinute":l["arrivalMinute"],"departureMinute":dep,"arrivalMinute":arr})
  for i,(a,d,dep,arr) in enumerate(item["legs"],1):
   ov["insertLegs"].append({"id":f"V140-R{item['route']}-FOCUSED-{index}-{i}","route":item["route"],"origin":a,"destination":d,"departureMinute":dep,"arrivalMinute":arr})
  for seq,operation,bank in item["banks"]:
   ov["bankAssignmentsToAdd"].append({"legId":ov["insertLegs"][seq-1]["id"],"operation":operation,"bankId":bank})
  if item.get("newBank"):ov["hubBanksToAdd"]=[item["newBank"]]
  c=apply_optimization_overlay(b,ov)
  s=validate_schedule(c);n=validate_overnight_turns(c);o=validate_operating_rules(c)
  p=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
  try:export_gate_schedule(c);g="pass"
  except Exception as e:g=f"{type(e).__name__}: {str(e)[:450]}"
  record.update(structure=s["status"],overnight=n["status"],planning=p["status"],gate=g,operating=o["summary"],
   failed=[{"check":x["id"],"findings":x.get("findings",[])[:8]} for x in o["checks"] if x["status"]=="fail"])
  record["pass"]=s["status"]==n["status"]==p["status"]=="pass" and o["summary"]["effectiveErrorFindings"]==0 and g=="pass"
  record["overlay"]=ov
 except Exception as e:record.update(pass_=False,error=repr(e),trace=traceback.format_exc()[-700:])
 results.append(record)
out=ROOT/"outputs/schedule_7_v1_4_0_utilization";out.mkdir(exist_ok=True,parents=True)
(out/"focused_midday_options.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps([{"name":z["name"],"pass":z.get("pass",False),"errors":z.get("operating",{}).get("effectiveErrorFindings"),"gate":z.get("gate"),"failed":[f["check"] for f in z.get("failed",[])],"exception":z.get("error")} for z in results],indent=2))
