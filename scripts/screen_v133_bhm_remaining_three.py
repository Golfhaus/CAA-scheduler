"""Screen alternative BHM mini-bank line inserts against native validators; no schedule writes."""
from pathlib import Path
import json,sys,copy,traceback
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule

base=json.loads((ROOT/"data/schedules/schedule_7_v1_3_3_draft/canonical_schedule.json").read_text())
cases=[
 {"route":529,"from":"BA","host":"AG","insert":11,"shiftFrom":100,"airport":"CMH","outDepart":360,"outArrive":460,"inDepart":1165,"inArrive":1265,"reason":"CMH~ALB endpoints, after AG R519"},
 {"route":357,"from":"BC","host":"AH","insert":10,"shiftFrom":100,"airport":"BDL","outDepart":385,"outArrive":426,"inDepart":1245,"inArrive":1286,"reason":"BDL~ISP endpoints, after AH R320"},
 {"route":358,"from":"BD","host":"AL","insert":12,"shiftFrom":12,"airport":"PHF","outDepart":392,"outArrive":467,"inDepart":1217,"inArrive":1292,"reason":"PHF~HVN endpoints between AL R327 and R321"}
]
def clock(n):return f"{n//60%24:02}:{n%60:02}"
results=[]
for case in cases:
  candidate=copy.deepcopy(base);route=case["route"]; host=case["host"]; day=case["insert"]
  record={"route":route,"host":host,"day":day,"endpoint":case["airport"],"reason":case["reason"]}
  try:
    host_routes=sorted({(l["day"],l["route"]) for l in candidate["legs"] if l["line"]==host})
    # Move all subsequent route-days one later to open chosen insertion slot.
    if case["shiftFrom"]<=max(d for d,r in host_routes):
      for leg in candidate["legs"]:
        if leg["line"]==host and leg["day"]>=case["shiftFrom"]:
          leg["day"]+=1
    routelegs=sorted([l for l in candidate["legs"] if l["route"]==route],key=lambda x:x["sequenceWithinRoute"])
    first,last=routelegs[0],routelegs[-1]
    oldfirst,oldlast=first["id"],last["id"]
    origfirst,origlast=first["origin"],last["destination"]
    first.update(origin=case["airport"],departureMinute=case["outDepart"],arrivalMinute=case["outArrive"],departure=clock(case["outDepart"]),arrival=clock(case["outArrive"]))
    last.update(destination=case["airport"],departureMinute=case["inDepart"],arrivalMinute=case["inArrive"],departure=clock(case["inDepart"]),arrival=clock(case["inArrive"]))
    first["id"]=f"V133-BHM-{route}-1-{case['airport']}-{first['destination']}"
    last["id"]=f"V133-BHM-{route}-6-{last['origin']}-{case['airport']}"
    for leg in routelegs:leg["line"]=host;leg["day"]=day
    # Recompute directed market pairing from existing schedule; allocate distinct pairing if necessary.
    existing={(l["origin"],l["destination"]):l["pairing"] for l in candidate["legs"] if l["route"]!=route}
    nextpair=max(l["pairing"] for l in candidate["legs"])+1
    for leg in (first,last):
      key=(leg["origin"],leg["destination"])
      if key not in existing:existing[key]=nextpair;nextpair+=1
      leg["pairing"]=existing[key]
    candidate["bankAssignments"]=[a for a in candidate["bankAssignments"] if a["legId"] not in (oldfirst,oldlast)]
    record["changedLegs"]=[{"from":oldfirst,"to":first["id"],"flight":first["flight"]},{"from":oldlast,"to":last["id"],"flight":last["flight"]}]
    record["lineRoutes"]=sorted({(l["day"],l["route"]) for l in candidate["legs"] if l["line"]==host})
    record["lineDays"]=max(l["day"] for l in candidate["legs"] if l["line"]==host)
    if record["lineDays"]>13:raise ValueError("Exceeds 13-day line cap")
    s=validate_schedule(candidate); o=validate_operating_rules(candidate)
    n=validate_overnight_turns(candidate)
    p=validate_planning_snapshot(reconstruct_planning_snapshot(candidate),candidate)
    try:export_gate_schedule(candidate);gate="pass"
    except Exception as e:gate=str(e)[:650]
    record.update(structure=s["status"],overnight=n["status"],planning=p["status"],
      gate=gate,operating=o["summary"],
      failed=[{"id":x["id"],"findings":x.get("findings",[])[:4]} for x in o["checks"] if x["status"]=="fail"])
    record["pass"]=s["status"]==n["status"]==p["status"]=="pass" and o["summary"]["effectiveErrorFindings"]==0 and gate=="pass"
  except Exception as e:
    record.update(pass_=False,error=repr(e),trace=traceback.format_exc()[-500:])
  results.append(record)
out=ROOT/"outputs/schedule_7_v1_3_3_bhm_line_insertion"
out.mkdir(parents=True,exist_ok=True)
(out/"remaining_three_screen.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps(results,indent=2))
