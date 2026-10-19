"""Read-only v1.4 SYR bank-linked route continuation and flight-growth screens.

Tests whether retimed return flights can feed new mini-bank departures and
additional routes while still terminating at original stations.
No accepted draft mutations.
"""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_0_draft/canonical_schedule.json").read_text())
assert len(base["legs"])==1257
byflight={x["flight"]:x for x in base["legs"]}
bankDefs={
 "M12":{"id":"SYR-M12","hub":"SYR","startMinute":715,"endMinute":775},
 "M15":{"id":"SYR-M15","hub":"SYR","startMinute":885,"endMinute":945},
 "M17":{"id":"SYR-M17","hub":"SYR","startMinute":1035,"endMinute":1095}}
cases=[
 {"name":"R107-ISP-BDL-CAK-DAY-CAK","banks":["M12","M17"],
 "retimes":[(1893,667,725),(1792,765,819),(1791,996,1050),(1674,1090,1161)],
 "replaceBank":[(1893,"arrival","SYR-M12"),(1792,"departure","SYR-M12"),
                (1791,"arrival","SYR-M17"),(1674,"departure","SYR-M17")],
 "adds":[("CAK","DAY",1215,1265),("DAY","CAK",1305,1355)],
 "addBanks":[(1,"arrival","DAY-B9"),(2,"departure","DAY-B9")],
 "description":"Retimed ISP and BDL returns create SYR M12 and M17 turns; CAK-DAY-CAK adds 100 block minutes, ends at CAK"},
 {"name":"R160-BTV-SYR-PWM-PHF-PWM","banks":["M15"],
 "retimes":[(1829,848,900),(1701,940,1008)],
 "replaceBank":[(1829,"arrival","SYR-M15"),(1701,"departure","SYR-M15")],
 "adds":[("PWM","PHF",1048,1149),("PHF","PWM",1189,1290)],
 "addBanks":[(1,"arrival","PHF-M6"),(2,"departure","PHF-M6")],
 "description":"Shift BTV-SYR and SYR-PWM into M15; add PWM-PHF-PWM to reach original PWM terminator later"},
]
results=[]
for case in cases:
 r={"name":case["name"],"description":case["description"],"scope":"READ ONLY, NOT IN ACCEPTED DRAFT"}
 try:
  codes=case["banks"]
  ov={"schemaVersion":"1.0.0","id":"v140-syr-bank-continue-"+case["name"],
   "baseSchedule":{"scheduleId":base["schedule"]["id"]},"schedule":base["schedule"],
   "hubBanksToAdd":[bankDefs[x] for x in codes],
   "hubBankCountOverrides":{"SYR":7+len(codes)},
   "retimeLegs":[],"bankAssignmentReplacements":[],"insertLegs":[],"bankAssignmentsToAdd":[]}
  for f,d,a in case["retimes"]:
   old=byflight[f]
   assert (old["arrivalMinute"]-old["departureMinute"])%1440==(a-d)%1440,(f,d,a,old)
   ov["retimeLegs"].append({"legId":old["id"],"expectedDepartureMinute":old["departureMinute"],
    "expectedArrivalMinute":old["arrivalMinute"],"departureMinute":d,"arrivalMinute":a})
  for f,operation,b in case["replaceBank"]:
   ov["bankAssignmentReplacements"].append({"legId":byflight[f]["id"],"operation":operation,"bankId":b})
  for i,(u,v,d,a) in enumerate(case["adds"],1):
   target=107 if case["name"].startswith("R107") else 160
   ov["insertLegs"].append({"id":f"V140-R{target}-BANK-TURN-{i}","route":target,
    "origin":u,"destination":v,"departureMinute":d,"arrivalMinute":a})
  for i,operation,b in case["addBanks"]:
   ov["bankAssignmentsToAdd"].append({"legId":ov["insertLegs"][i-1]["id"],"operation":operation,"bankId":b})
  c=apply_optimization_overlay(base,ov)
  s=validate_schedule(c);n=validate_overnight_turns(c);o=validate_operating_rules(c)
  p=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
  try:export_gate_schedule(c);gate="pass"
  except Exception as e:gate=f"{type(e).__name__}: {str(e)[:450]}"
  r.update(structure=s["status"],overnight=n["status"],planning=p["status"],gate=gate,
   operating=o["summary"],addedFlights=len(c["legs"])-len(base["legs"]),
   failures=[{"check":x["id"],"findings":x.get("findings",[])[:8]} for x in o["checks"] if x["status"]=="fail"])
  r["pass"]=s["status"]==n["status"]==p["status"]=="pass" and gate=="pass" and o["summary"]["effectiveErrorFindings"]==0
  r["overlay"]=ov
  if r["pass"]:(ROOT/"outputs/schedule_7_v1_4_0_utilization"/(case["name"]+"_canonical.json")).write_text(json.dumps(c)+"\n")
 except Exception as e:r.update(pass_=False,error=repr(e),trace=traceback.format_exc()[-800:])
 results.append(r)
out=ROOT/"outputs/schedule_7_v1_4_0_utilization"
out.mkdir(exist_ok=True,parents=True)
(out/"syr_bank_continuations.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps([{"name":x["name"],"pass":x.get("pass",False),"extra":x.get("addedFlights"),
 "errors":x.get("operating",{}).get("effectiveErrorFindings"),
 "gate":x.get("gate"),"failed":[z["check"] for z in x.get("failures",[])],"error":x.get("error")} for x in results],indent=2))
