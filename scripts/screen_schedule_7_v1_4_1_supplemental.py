"""Supplemental v1.4.1 native screens: PHF north-south A-B routes and R105 late BGR growth."""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_0/canonical_schedule.json").read_text())
byflight={l["flight"]:l for l in base["legs"]}
cases=[
 {"name":"R107 ISP-PHF-SYR via PHF B3/B4 and SYR M15","route":107,"remove":[1893],
  "retime":[(1792,925,979)],
  "insert":[("ISP","PHF",613,703),("PHF","SYR",800,885)],
  "bankassign":[(1,"arrival","PHF-B3"),(2,"departure","PHF-B4"),(2,"arrival","SYR-M15")],
  "replace":[(1792,"departure","SYR-M15")]},
 {"name":"R108 ORH-PHF-SYR via PHF B3/B4 and SYR M15","route":108,"remove":[1884],
  "retime":[(1826,925,977)],
  "insert":[("ORH","PHF",613,703),("PHF","SYR",800,885)],
  "bankassign":[(1,"arrival","PHF-B3"),(2,"departure","PHF-B4"),(2,"arrival","SYR-M15")],
  "replace":[(1826,"departure","SYR-M15")]},
 {"name":"R105 MHT earlier plus late BGR-SYR-BGR","route":105,
  "retime":[(1839,705,765),(1773,805,885),(1776,925,1005),(1774,1045,1125)],
  "insert":[("BGR","SYR",1210,1290),("SYR","BGR",1330,1410)],
  "bankassign":[(1,"arrival","SYR-B7"),(2,"departure","SYR-B7")],
  "replace":[(1839,"arrival","SYR-M12"),(1773,"departure","SYR-B4")],
  "banks":["M12"]},
]
bankSpecs={"M12":{"id":"SYR-M12","hub":"SYR","startMinute":715,"endMinute":775}}
out=ROOT/"outputs/schedule_7_v1_4_1_utilization";out.mkdir(exist_ok=True,parents=True)
results=[]
for i,case in enumerate(cases):
 record={"name":case["name"],"scope":"read-only","route":case["route"]}
 try:
  ov={"schemaVersion":"1.0.0","id":f"v141-extra-{i}","baseSchedule":{"scheduleId":base["schedule"]["id"]},
   "schedule":{**base["schedule"],"id":"schedule_7_v1_4_1_draft","version":"1.4.1-draft","label":"Schedule 7 v1.4.1 draft","status":"draft"},
   "removeLegs":[{"legId":byflight[n]["id"],"expectedRoute":case["route"]} for n in case.get("remove",[])],
   "retimeLegs":[],"insertLegs":[],"bankAssignmentsToAdd":[],"bankAssignmentReplacements":[]}
  for n,dep,arr in case["retime"]:
   leg=byflight[n]
   assert (leg["arrivalMinute"]-leg["departureMinute"])%1440==(arr-dep)%1440
   ov["retimeLegs"].append({"legId":leg["id"],"expectedDepartureMinute":leg["departureMinute"],
     "expectedArrivalMinute":leg["arrivalMinute"],"departureMinute":dep,"arrivalMinute":arr})
  for k,(u,v,dep,arr) in enumerate(case["insert"],1):
   ov["insertLegs"].append({"id":f"V141-R{case['route']}-EXTRA-{i}-{k}","route":case["route"],
    "origin":u,"destination":v,"departureMinute":dep,"arrivalMinute":arr})
  for k,op,bank in case["bankassign"]:
   ov["bankAssignmentsToAdd"].append({"legId":ov["insertLegs"][k-1]["id"],"operation":op,"bankId":bank})
  for n,op,bank in case["replace"]:
   ov["bankAssignmentReplacements"].append({"legId":byflight[n]["id"],"operation":op,"bankId":bank})
  if case.get("banks"):
   ov["hubBanksToAdd"]=[bankSpecs[x] for x in case["banks"]]
   ov["hubBankCountOverrides"]={"SYR":9+len(case["banks"])}
  c=apply_optimization_overlay(base,ov)
  structural=validate_schedule(c);overnight=validate_overnight_turns(c)
  operating=validate_operating_rules(c)
  planning=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
  try:export_gate_schedule(c);gate="pass"
  except Exception as e:gate=f"{type(e).__name__}: {str(e)[:450]}"
  record.update(structural=structural["status"],overnight=overnight["status"],planning=planning["status"],
   gate=gate,operating=operating["summary"],extraFlights=len(c["legs"])-len(base["legs"]),
   failed=[{"check":z["id"],"findings":z.get("findings",[])[:5]} for z in operating["checks"] if z["status"]=="fail"])
  record["pass"]=structural["status"]==overnight["status"]==planning["status"]=="pass" and gate=="pass" and operating["summary"]["effectiveErrorFindings"]==0
  record["overlay"]=ov
  if record["pass"]:(out/f"extra_{i}_canonical.json").write_text(json.dumps(c)+"\n")
 except Exception as e:record.update(pass_=False,error=repr(e),trace=traceback.format_exc()[-600:])
 results.append(record)
(out/"supplemental_screen.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps([{"name":r["name"],"pass":r.get("pass",False),"errors":r.get("operating",{}).get("effectiveErrorFindings"),"gate":r.get("gate"),"checks":[x["check"] for x in r.get("failed",[])],"error":r.get("error")} for r in results],indent=2))
