"""Native tactical P2P and A-B-C alternatives using published flight legs, no draft mutation."""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_0_draft/canonical_schedule.json").read_text())
byflight={l["flight"]:l for l in base["legs"]}
cases=[
{"route":160,"name":"BTV-PHF-SYR tactical bank retiming","remove":1829,
"replace":[("BTV","PHF",762,862),("PHF","SYR",902,987)],
"retimes":[(1908,566,630),(1825,670,722),(1952,933,1018)],
"banks":[(1,"arrival","PHF-M3"),(2,"departure","PHF-M3"),(2,"arrival","SYR-B5")]},
{"route":107,"name":"BDL-BUF-SYR A-B-C triangle","remove":1791,
"replace":[("BDL","BUF",939,1019),("BUF","SYR",1079,1125)],"retimes":[],
"banks":[(2,"arrival","SYR-B6")]},
{"route":107,"name":"BDL-ROC-SYR A-B-C triangle","remove":1791,
"replace":[("BDL","ROC",939,1014),("ROC","SYR",1086,1125)],"retimes":[],
"banks":[(2,"arrival","SYR-B6")]},
]
results=[]
for idx,c in enumerate(cases):
 r={"route":c["route"],"name":c["name"],"scope":"read-only"}
 try:
  old=byflight[c["remove"]]
  assert old["route"]==c["route"] and c["replace"][0][0]==old["origin"] and c["replace"][-1][1]==old["destination"]
  ov={"schemaVersion":"1.0.0","id":f"v140-p2p-tactical-{idx}",
   "baseSchedule":{"scheduleId":base["schedule"]["id"]},"schedule":base["schedule"],
   "removeLegs":[{"legId":old["id"],"expectedRoute":old["route"]}],"retimeLegs":[],"insertLegs":[],"bankAssignmentsToAdd":[]}
  for f,dep,arr in c["retimes"]:
   l=byflight[f]
   assert (l["arrivalMinute"]-l["departureMinute"])%1440==(arr-dep)%1440
   ov["retimeLegs"].append({"legId":l["id"],"expectedDepartureMinute":l["departureMinute"],"expectedArrivalMinute":l["arrivalMinute"],"departureMinute":dep,"arrivalMinute":arr})
  for n,(u,v,dep,arr) in enumerate(c["replace"],1):
   ov["insertLegs"].append({"id":f"V140-R{c['route']}-ABTACT-{idx}-{n}",
    "route":c["route"],"origin":u,"destination":v,"departureMinute":dep,"arrivalMinute":arr})
  for n,op,b in c["banks"]:
   ov["bankAssignmentsToAdd"].append({"legId":ov["insertLegs"][n-1]["id"],"operation":op,"bankId":b})
  sched=apply_optimization_overlay(base,ov)
  s=validate_schedule(sched);o=validate_operating_rules(sched);n=validate_overnight_turns(sched)
  p=validate_planning_snapshot(reconstruct_planning_snapshot(sched),sched)
  try:export_gate_schedule(sched);gate="pass"
  except Exception as e:gate=f"{type(e).__name__}: {str(e)[:500]}"
  r.update(structure=s["status"],overnight=n["status"],planning=p["status"],gate=gate,
   operating=o["summary"],failed=[{"check":x["id"],"findings":x.get("findings",[])[:6]} for x in o["checks"] if x["status"]=="fail"])
  r["pass"]=s["status"]==n["status"]==p["status"]=="pass" and gate=="pass" and o["summary"]["effectiveErrorFindings"]==0
  r["changes"]=ov
 except Exception as e:r.update(pass_=False,error=repr(e),trace=traceback.format_exc()[-900:])
 results.append(r)
out=ROOT/"outputs/schedule_7_v1_4_0_utilization";out.mkdir(parents=True,exist_ok=True)
(out/"tactical_p2p_screen.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps([{"name":x["name"],"pass":x.get("pass",False),"errors":x.get("operating",{}).get("effectiveErrorFindings"),"gate":x.get("gate"),"failed":[z["check"] for z in x.get("failed",[])],"error":x.get("error")} for x in results],indent=2))
