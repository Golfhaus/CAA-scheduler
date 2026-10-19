"""Read-only Syracuse mini-bank arrival plus following-departure screens.
For each long-hold return, test the following outbound at minimum 40-minute
SYR connection, with no downstream route changes. No draft mutations.
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
data=json.loads((out/"syr_hold_inventory.json").read_text())
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_0_draft/canonical_schedule.json").read_text())
byid={x["id"]:x for x in base["legs"]}
banks={b["code"]:b for b in data["gapBanks"]}
def fmt(n):return f"{n//60%24:02}:{n%60:02}"
results=[]
for row in data["rows"]:
 if row["nextLegId"] is None:continue
 nextleg=byid[row["nextLegId"]]
 for candidate in row["candidates"]:
  code=candidate["code"];bank=banks[code]
  # Inbound plus onward departure can both fit in 60-minute mini-bank only
  # when inbound lands at least 40 minutes before the bank ends.
  arrival=min(bank["center"],bank["endMinute"]-45)
  # PHF R129 must still depart PHF inside the existing PHF B2 full bank.
  if row["route"]==129:arrival=590
  dep=arrival-row["durationMinutes"];nextdep=arrival+40
  rec={"route":row["route"],"station":row["station"],"bank":code,
    "returnFlight":row["returnFlight"],"nextFlight":row["nextFlight"],
    "inboundMinute":arrival,"outboundMinute":nextdep,
    "outboundDestination":row["nextDestination"],"scope":"read-only, single pair"}
  if nextdep>=bank["endMinute"]:
   rec.update(pass_=False,reason="Onward outbound misses mini-bank window");results.append(rec);continue
  if dep <row["outstationArrivalMinute"]+40 or nextdep>=row["nextDepartureMinute"]:
   rec.update(pass_=False,reason="Cannot satisfy outstation hold or earlier outbound");results.append(rec);continue
  try:
   afterarr=nextleg["arrivalMinute"]-(nextleg["departureMinute"]-nextdep)
   ov={"schemaVersion":"1.0.0","id":f"v140-syr-next-{row['route']}-{row['returnFlight']}",
    "baseSchedule":{"scheduleId":base["schedule"]["id"]},"schedule":base["schedule"],
    "hubBanksToAdd":[{"id":bank["id"],"hub":"SYR","startMinute":bank["startMinute"],"endMinute":bank["endMinute"]}],
    "hubBankCountOverrides":{"SYR":8},
    "retimeLegs":[{"legId":row["returnLegId"],"expectedDepartureMinute":row["scheduledDepartureMinute"],
       "expectedArrivalMinute":row["scheduledArrivalMinute"],"departureMinute":dep,"arrivalMinute":arrival},
      {"legId":nextleg["id"],"expectedDepartureMinute":nextleg["departureMinute"],
       "expectedArrivalMinute":nextleg["arrivalMinute"],"departureMinute":nextdep,"arrivalMinute":afterarr}],
    "bankAssignmentReplacements":[{"legId":row["returnLegId"],"operation":"arrival","bankId":bank["id"]},
       {"legId":nextleg["id"],"operation":"departure","bankId":bank["id"]}]}
   # If retimed onward arrives at a banked hub, update only when another pre-existing
   # bank contains new arrival. Never invent destination bank or exceptions.
   arrivalAssignments=[a for a in base["bankAssignments"] if a["legId"]==nextleg["id"] and a["operation"]=="arrival"]
   if arrivalAssignments:
    existing=[x for x in base["hubBanks"] if x["hub"]==nextleg["destination"] and
      (x["startMinute"]<=afterarr<x["endMinute"] or
       (x["endMinute"]<x["startMinute"] and (afterarr>=x["startMinute"] or afterarr<x["endMinute"])))]
    if len(existing)==1:
     ov["bankAssignmentReplacements"].append({"legId":nextleg["id"],"operation":"arrival","bankId":existing[0]["id"]})
   c=apply_optimization_overlay(base,ov)
   s=validate_schedule(c);n=validate_overnight_turns(c)
   o=validate_operating_rules(c);p=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
   try:export_gate_schedule(c);gate="pass"
   except Exception as e:gate=f"{type(e).__name__}: {str(e)[:230]}"
   rec.update(structure=s["status"],overnight=n["status"],planning=p["status"],gate=gate,
    operating=o["summary"],failed=[{"check":x["id"],"findings":x.get("findings",[])[:3]} for x in o["checks"] if x["status"]=="fail"])
   rec["pass"]=s["status"]==n["status"]==p["status"]=="pass" and o["summary"]["effectiveErrorFindings"]==0 and gate=="pass"
   if rec["pass"]:rec["overlay"]=ov
  except Exception as e:rec.update(pass_=False,error=repr(e),trace=traceback.format_exc()[-550:])
  results.append(rec)
(out/"syr_outbound_continuations.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps({"total":len(results),"passes":sum(x.get("pass",False) for x in results),
 "passed":[{"route":x["route"],"bank":x["bank"],"next":x["outboundDestination"]} for x in results if x.get("pass")],
 "failed":[{"route":x["route"],"bank":x["bank"],"failedChecks":[a["check"] for a in x.get("failed",[])],
   "gate":x.get("gate"),"reason":x.get("reason")} for x in results if not x.get("pass")]},indent=2))
