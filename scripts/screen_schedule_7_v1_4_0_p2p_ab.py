"""Screen P2P / A-B-C triangle replacements on unpublished v1.4 draft.

A-B-C paths retain previous and following route legs, replace one intermediate
outstation-to-hub leg, and use pinned native validation. No publication.
"""
from pathlib import Path
import json,sys,csv,math,traceback
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_0_draft/canonical_schedule.json").read_text())
assert len(base["legs"])==1257 and base["schedule"]["id"]=="schedule_7_v1_4_0_draft"
csvpath=ROOT/"data/reference/airport_od_matrix_consolidated_v2.csv"
with csvpath.open(newline="") as f:
    rows=list(csv.reader(f))
header=next(i for i,row in enumerate(rows) if row and row[0]=="Origin \\ Dest")
cities=rows[header][1:]
od={}
for row in rows[header+1:]:
    if row and row[0] in cities:
        od[row[0]]={to:float(row[i+1] or 0) for i,to in enumerate(cities)}
byflight={x["flight"]:x for x in base["legs"]}
cases=[
 {"route":107,"market":"ISP-BWI-SYR","remove":1893,"legs":[("ISP","BWI",615,687),("BWI","SYR",730,795)],"banks":[(2,"arrival","SYR-B4")],
  "purpose":"Strong ISP-BWI directional demand (18.1/day), replacing ISP-SYR midday return"},
 {"route":107,"market":"BDL-BWI-SYR","remove":1791,"legs":[("BDL","BWI",940,1010),("BWI","SYR",1060,1125)],"banks":[(2,"arrival","SYR-B6")],
  "purpose":"Strong BDL-BWI directional demand (32.9/day), instead of BDL-SYR late return"},
 {"route":107,"market":"BDL-PVD-SYR","remove":1791,"legs":[("BDL","PVD",939,974),("PVD","SYR",1062,1125)],"banks":[(2,"arrival","SYR-B6")],
  "purpose":"Regional BDL-PVD point-to-point and PVD-SYR feeder"},
 {"route":160,"market":"BTV-PHF-SYR","remove":1829,"legs":[("BTV","PHF",790,890),("PHF","SYR",930,1015)],
  "banks":[(1,"arrival","PHF-M3"),(2,"departure","PHF-B5"),(2,"arrival","SYR-B5")],
  "purpose":"BTV-PHF nonstop and PHF-SYR bank connection, replacing BTV-SYR return"},
 {"route":160,"market":"BTV-PWM-SYR","remove":1829,"legs":[("BTV","PWM",805,860),("PWM","SYR",940,1008)],"banks":[(2,"arrival","SYR-B5")],
  "purpose":"BTV-PWM P2P and PWM-SYR A-B-C triangle"},
 {"route":160,"market":"BTV-ROC-SYR","remove":1829,"legs":[("BTV","ROC",800,865),("ROC","SYR",940,979)],"banks":[(2,"arrival","SYR-B5")],
  "purpose":"BTV-ROC P2P and ROC-SYR feeder through SYR-B5"},
 {"route":107,"market":"ISP-ALB-SYR","remove":1893,"legs":[("ISP","ALB",615,662),("ALB","SYR",710,754)],"banks":[(2,"arrival","SYR-B4")],
  "purpose":"ISP-ALB regional A-B leg, while feeding existing SYR B4"},
]
results=[]
for idx,c in enumerate(cases):
 rec={"route":c["route"],"market":c["market"],"purpose":c["purpose"],"scope":"read-only"}
 try:
    old=byflight[c["remove"]]
    assert old["route"]==c["route"]
    assert len(c["legs"])==2 and old["origin"]==c["legs"][0][0] and old["destination"]==c["legs"][1][1]
    assert c["legs"][0][1]==c["legs"][1][0]
    ov={"schemaVersion":"1.0.0","id":f"v140-p2p-triangle-{idx}","baseSchedule":{"scheduleId":base["schedule"]["id"]},
      "schedule":base["schedule"],"removeLegs":[{"legId":old["id"],"expectedRoute":old["route"]}],
      "insertLegs":[],"bankAssignmentsToAdd":[]}
    for i,(a,b,d,arr) in enumerate(c["legs"],1):
      ov["insertLegs"].append({"id":f"V140-R{c['route']}-P2P-{idx}-{i}","route":c["route"],
        "origin":a,"destination":b,"departureMinute":d,"arrivalMinute":arr})
    for i,operation,bank in c["banks"]:
      ov["bankAssignmentsToAdd"].append({"legId":ov["insertLegs"][i-1]["id"],"operation":operation,"bankId":bank})
    cand=apply_optimization_overlay(base,ov)
    struct=validate_schedule(cand)
    op=validate_operating_rules(cand)
    night=validate_overnight_turns(cand)
    plan=validate_planning_snapshot(reconstruct_planning_snapshot(cand),cand)
    try:export_gate_schedule(cand);gate="pass"
    except Exception as e:gate=f"{type(e).__name__}: {str(e)[:400]}"
    rec.update(structure=struct["status"],overnight=night["status"],planning=plan["status"],gate=gate,
      operating=op["summary"],failed=[{"check":x["id"],"findings":x.get("findings",[])[:7]} for x in op["checks"] if x["status"]=="fail"])
    rec["pass"]=struct["status"]==night["status"]==plan["status"]=="pass" and op["summary"]["effectiveErrorFindings"]==0 and gate=="pass"
    rec["marketOD"]={"firstLeg":od[c["legs"][0][0]][c["legs"][0][1]],"secondLeg":od[c["legs"][1][0]][c["legs"][1][1]]}
    rec["removedLeg"]={"flight":old["flight"],"origin":old["origin"],"destination":old["destination"]}
    rec["addedLegs"]=c["legs"]
    rec["deltaFlights"]=len(cand["legs"])-len(base["legs"])
    rec["overlay"]=ov if rec["pass"] else None
 except Exception as e:
    rec.update(pass_=False,error=repr(e),trace=traceback.format_exc()[-900:])
 results.append(rec)
out=ROOT/"outputs/schedule_7_v1_4_0_utilization";out.mkdir(parents=True,exist_ok=True)
(out/"p2p_ab_triangle_screen.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps([{"route":r["route"],"market":r["market"],"pass":r.get("pass",False),"errors":r.get("operating",{}).get("effectiveErrorFindings"),"gate":r.get("gate"),"failed":[x["check"] for x in r.get("failed",[])],"error":r.get("error")} for r in results],indent=2))
