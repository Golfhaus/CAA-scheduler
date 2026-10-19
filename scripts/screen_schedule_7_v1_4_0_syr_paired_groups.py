"""Group co-validation of Syracuse inbound+outbound mini-bank waves.

Builds scenarios from individually native-passed return/onward retimes, with
nonpaired arrivals retained where justified. Does not modify working draft.
"""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
out=ROOT/"outputs/schedule_7_v1_4_0_utilization"
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_0_draft/canonical_schedule.json").read_text())
outbounds=json.loads((out/"syr_outbound_continuations.json").read_text())
groups=json.loads((out/"syr_group_feasibility.json").read_text())
pairs=[x for x in outbounds if x.get("pass")]
banks={
 "M09":{"id":"SYR-M09","hub":"SYR","startMinute":535,"endMinute":595},
 "M12":{"id":"SYR-M12","hub":"SYR","startMinute":715,"endMinute":775},
 "M15":{"id":"SYR-M15","hub":"SYR","startMinute":885,"endMinute":945},
 "M17":{"id":"SYR-M17","hub":"SYR","startMinute":1035,"endMinute":1095},
 "M20":{"id":"SYR-M20","hub":"SYR","startMinute":1215,"endMinute":1275}}
scenarios=[
 ("paired_M12",["M12"],False),
 ("paired_M15",["M15"],False),
 ("paired_M17",["M17"],False),
 ("paired_core",["M12","M15","M17"],False),
 ("paired_core_plus_R107_M12",["M12","M15","M17"],True),
 ("paired_all_five",["M09","M12","M15","M17","M20"],True)
]
results=[]
for name,codes,include_extra in scenarios:
 report={"name":name,"banks":codes,"scope":"READ ONLY: unaccepted draft alternative"}
 try:
  selected=[x for x in pairs if x["bank"] in codes]
  add={code:[] for code in codes}
  for x in selected:add[x["bank"]].append(x["route"])
  ov={"schemaVersion":"1.0.0","id":f"v140-syr-grouped-outbound-{name}",
    "baseSchedule":{"scheduleId":base["schedule"]["id"]},"schedule":base["schedule"],
    "hubBanksToAdd":[banks[x] for x in codes],
    "hubBankCountOverrides":{"SYR":7+len(codes)},
    "retimeLegs":[],"bankAssignmentReplacements":[]}
  for x in selected:
   part=x["overlay"]
   ov["retimeLegs"].extend(part["retimeLegs"])
   ov["bankAssignmentReplacements"].extend(part["bankAssignmentReplacements"])
  extras=[]
  if include_extra:
   # Carry arrivals whose immediate onward cannot be shifted, preserving original departures.
   group=next(x for x in groups if x["name"]=="all_five")
   assert group["pass"]
   for row in group["changedReturns"]:
    code=row["bank"].split("-")[-1]
    if code not in codes or any(x["returnFlight"]==row["returnFlight"] for x in selected):continue
    extras.append(row)
    baseleg=next(x for x in base["legs"] if x["flight"]==row["returnFlight"])
    ov["retimeLegs"].append({"legId":baseleg["id"],
      "expectedDepartureMinute":baseleg["departureMinute"],"expectedArrivalMinute":baseleg["arrivalMinute"],
      "departureMinute":row["newDeparture"],"arrivalMinute":row["newArrival"]})
    ov["bankAssignmentReplacements"].append({"legId":baseleg["id"],"operation":"arrival","bankId":row["bank"]})
  # Every leg's retiming and operation assignment must be unique.
  assert len({x["legId"] for x in ov["retimeLegs"]})==len(ov["retimeLegs"])
  assert len({(x["legId"],x["operation"]) for x in ov["bankAssignmentReplacements"]})==len(ov["bankAssignmentReplacements"])
  c=apply_optimization_overlay(base,ov)
  s=validate_schedule(c);n=validate_overnight_turns(c);o=validate_operating_rules(c)
  p=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
  try:export_gate_schedule(c);gate="pass"
  except Exception as e:gate=f"{type(e).__name__}: {str(e)[:450]}"
  report.update(structure=s["status"],overnight=n["status"],planning=p["status"],gate=gate,
   operating=o["summary"],paired=len(selected),extraInbound=len(extras),pairsByBank=add,
   failures=[{"check":x["id"],"findings":x.get("findings",[])[:6]} for x in o["checks"] if x["status"]=="fail"])
  report["pass"]=s["status"]==n["status"]==p["status"]=="pass" and gate=="pass" and o["summary"]["effectiveErrorFindings"]==0
  if report["pass"]:
   (out/f"syr_paired_{name}_canonical.json").write_text(json.dumps(c)+"\n")
   report["overlay"]=ov
 except Exception as e:report.update(pass_=False,error=repr(e),trace=traceback.format_exc()[-900:])
 results.append(report)
(out/"syr_paired_banks_native.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps([{"name":r["name"],"pass":r.get("pass",False),"paired":r.get("paired"),
"extraInbound":r.get("extraInbound"),"gate":r.get("gate"),
"errors":r.get("operating",{}).get("effectiveErrorFindings"),
"failed":[f["check"] for f in r.get("failures",[])],"exception":r.get("error")} for r in results],indent=2))
