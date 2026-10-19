"""Read-only group gate/bank screening for Syracuse proposed mini-bank waves."""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
p=ROOT/"outputs/schedule_7_v1_4_0_utilization"
inventory=json.loads((p/"syr_hold_inventory.json").read_text())
rows=inventory["rows"];bankByCode={b["code"]:b for b in inventory["gapBanks"]}
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_0_draft/canonical_schedule.json").read_text())
scenarios=[
 ("M12_only",["M12"]),("M15_only",["M15"]),("M17_only",["M17"]),
 ("M09_only",["M09"]),("M20_only",["M20"]),
 ("core_M12_M15_M17",["M12","M15","M17"]),
 ("all_except_M09",["M12","M15","M17","M20"]),
 ("all_except_M20",["M09","M12","M15","M17"]),
 ("all_five",["M09","M12","M15","M17","M20"])
]
results=[]
for name,selected in scenarios:
 rec={"name":name,"bankCodes":selected,"scope":"READ ONLY — no draft update"}
 try:
  ov={"schemaVersion":"1.0.0","id":f"v140-syr-group-{name}",
  "baseSchedule":{"scheduleId":base["schedule"]["id"]},"schedule":base["schedule"],
  "hubBanksToAdd":[{"id":b["id"],"hub":"SYR","startMinute":b["startMinute"],"endMinute":b["endMinute"]} for b in inventory["gapBanks"] if b["code"] in selected],
  "hubBankCountOverrides":{"SYR":7+len(selected)},
  "retimeLegs":[],"bankAssignmentReplacements":[]}
  changes=[]
  for code in selected:
   members=[x for x in rows if any(k["code"]==code for k in x["candidates"])]
   members.sort(key=lambda x:(0 if x["route"] in (107,160) else 1,x["route"],x["returnFlight"]))
   bank=bankByCode[code]
   for i,x in enumerate(members):
    target=590 if code=="M09" and x["route"]==129 else bank["center"]+i*5
    before=x["scheduledDepartureMinute"];after=target-x["durationMinutes"]
    minimum=x["outstationArrivalMinute"]+40
    maximum=(x["nextDepartureMinute"]-40) if x["nextDepartureMinute"] is not None else x["scheduledArrivalMinute"]
    if not (after>=minimum and target<=maximum and after<before):
     raise ValueError(f'{name}: route {x["route"]} bank {code} cannot arrive {target}, dep {after} earliest {minimum}, next max {maximum}')
    # Existing arrival bank association must be exactly one (for full-banked SYR touch).
    if len(x["arrivalAssignment"])!=1:
     raise ValueError(f'route {x["route"]} inbound bank assignment count {len(x["arrivalAssignment"])}')
    ov["retimeLegs"].append({"legId":x["returnLegId"],"expectedDepartureMinute":before,
       "expectedArrivalMinute":x["scheduledArrivalMinute"],"departureMinute":after,"arrivalMinute":target})
    ov["bankAssignmentReplacements"].append({"legId":x["returnLegId"],"operation":"arrival","bankId":bank["id"]})
    changes.append({"route":x["route"],"returnFlight":x["returnFlight"],"station":x["station"],"bank":bank["id"],
     "oldArrival":x["scheduledArrivalMinute"],"newArrival":target,
     "newDeparture":after,"oldHold":x["holdMinutes"],"newHold":after-x["outstationArrivalMinute"],
     "nextFlight":x["nextFlight"],"nextDeparture":x["nextDepartureMinute"]})
  c=apply_optimization_overlay(base,ov)
  s=validate_schedule(c);n=validate_overnight_turns(c);o=validate_operating_rules(c)
  pval=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
  try:
   gates=export_gate_schedule(c);gate="pass"
   syr=next(g for g in gates["cities"] if g["code"]=="SYR")
   syrStands=sum(x["rowType"]=="stand" for x in syr["claims"])
  except Exception as e:gate=f"{type(e).__name__}: {str(e)[:450]}";syrStands=None
  rec.update(structure=s["status"],overnight=n["status"],planning=pval["status"],
   gate=gate,operating=o["summary"],changedReturns=changes,retimedCount=len(changes),
   gateStandClaims=syrStands,
   failures=[{"check":x["id"],"findings":x.get("findings",[])[:5]} for x in o["checks"] if x["status"]=="fail"])
  rec["pass"]=s["status"]==n["status"]==pval["status"]=="pass" and gate=="pass" and o["summary"]["effectiveErrorFindings"]==0
  if rec["pass"]:
   rec["overlay"]=ov
   (ROOT/"outputs/schedule_7_v1_4_0_utilization"/f"syr_group_{name}_canonical.json").write_text(json.dumps(c)+"\n")
 except Exception as e:rec.update(pass_=False,error=repr(e),trace=traceback.format_exc()[-700:])
 results.append(rec)
(ROOT/"outputs/schedule_7_v1_4_0_utilization"/"syr_group_feasibility.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps([{"name":r["name"],"pass":r.get("pass",False),
"count":r.get("retimedCount"),"gate":r.get("gate"),
"errors":r.get("operating",{}).get("effectiveErrorFindings"),"failed":[x["check"] for x in r.get("failures",[])],"exception":r.get("error")} for r in results],indent=2))
