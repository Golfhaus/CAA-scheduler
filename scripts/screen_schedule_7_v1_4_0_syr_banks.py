"""Comprehensive SYR long-hold return-bank screening for Schedule 7 v1.4.0.

Read-only feasibility against accepted unpublished 1,257-flight draft.
Enumerate every >=120-minute outstation hold before a SYR-bound flight.
Evaluate single-return repositioning into five gap banks and route continuation.
No accepted schedule files, released schedules, or manifests are changed.
"""
from pathlib import Path
from collections import defaultdict
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule

base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_0_draft/canonical_schedule.json").read_text())
assert len(base["legs"])==1257 and base["schedule"]["status"]=="draft"
assert base["operatingPolicy"]["hubBankCounts"]["SYR"]==7
groups=defaultdict(list)
for leg in base["legs"]:groups[int(leg["route"])].append(leg)
for route in groups:groups[route].sort(key=lambda x:int(x["sequenceWithinRoute"]))
banks=[
 {"code":"M09","id":"SYR-M09","startMinute":535,"endMinute":595,"center":555},
 {"code":"M12","id":"SYR-M12","startMinute":715,"endMinute":775,"center":725},
 {"code":"M15","id":"SYR-M15","startMinute":885,"endMinute":945,"center":905},
 {"code":"M17","id":"SYR-M17","startMinute":1035,"endMinute":1095,"center":1055},
 {"code":"M20","id":"SYR-M20","startMinute":1215,"endMinute":1275,"center":1235},
]
assert all(not (x["startMinute"]<y["endMinute"] and y["startMinute"]<x["endMinute"])
               for x in banks for y in base["hubBanks"] if y["hub"]=="SYR")
assignments=defaultdict(list)
for a in base["bankAssignments"]:assignments[(a["legId"],a["operation"])].append(a)
inventory=[]
for route,legs in sorted(groups.items()):
 for i in range(1,len(legs)):
  prev,ret=legs[i-1],legs[i]
  if ret["destination"]!="SYR" or prev["destination"]!=ret["origin"]:continue
  hold=(int(ret["departureMinute"])-int(prev["arrivalMinute"]))%1440
  if hold<120:continue
  n=legs[i+1] if i+1<len(legs) else None
  duration=(int(ret["arrivalMinute"])-int(ret["departureMinute"]))%1440
  earliest=int(prev["arrivalMinute"])+40+duration
  latest=min(int(ret["arrivalMinute"])-1,(int(n["departureMinute"])-40) if n else int(ret["arrivalMinute"])-1)
  candidates=[]
  for bank in banks:
   target=bank["center"]
   if earliest<=target<=latest and int(ret["departureMinute"])-(target-duration)>=0:
    candidates.append({"code":bank["code"],"targetArrival":target,"targetDeparture":target-duration,
      "savedOutstationHold":int(ret["departureMinute"])-(target-duration),
      "SYRGroundBeforeNext":int(n["departureMinute"])-target if n else None})
  inventory.append({"route":route,"line":ret["line"],"day":ret["day"],"fleet":ret["fleet"],
    "station":ret["origin"],"holdMinutes":hold,"beforeFlight":prev["flight"],
    "outstationArrivalMinute":prev["arrivalMinute"],
    "returnFlight":ret["flight"],"returnLegId":ret["id"],
    "scheduledDepartureMinute":ret["departureMinute"],
    "scheduledArrivalMinute":ret["arrivalMinute"],
    "durationMinutes":duration,"nextFlight":n["flight"] if n else None,
    "nextLegId":n["id"] if n else None,
    "nextDepartureMinute":n["departureMinute"] if n else None,
    "nextDestination":n["destination"] if n else None,
    "arrivalAssignment":assignments[(ret["id"],"arrival")],
    "candidates":candidates})
assert len(inventory)==22,(len(inventory),inventory)
out=ROOT/"outputs/schedule_7_v1_4_0_utilization"
out.mkdir(parents=True,exist_ok=True)
(out/"syr_hold_inventory.json").write_text(json.dumps({"baseline":"schedule_7_v1_4_0_draft",
 "minimumHoldMinutes":120,"rows":inventory,"gapBanks":banks},indent=2)+"\n")
results=[]
for i,hold in enumerate(inventory):
 for option in hold["candidates"]:
  bank=next(b for b in banks if b["code"]==option["code"])
  tag=f'{hold["route"]}-{hold["returnFlight"]}-{bank["code"]}'
  rec={"route":hold["route"],"station":hold["station"],"flight":hold["returnFlight"],
    "bank":bank["id"],"targetArrivalMinute":option["targetArrival"],
    "newDepartureMinute":option["targetDeparture"],"holdReducedMinutes":option["savedOutstationHold"],
    "nextFlight":hold["nextFlight"],"nextDestination":hold["nextDestination"],"scope":"single flight, read only"}
  try:
   ov={"schemaVersion":"1.0.0","id":f"v140-syr-hold-{tag}",
     "baseSchedule":{"scheduleId":base["schedule"]["id"]},"schedule":base["schedule"],
     "hubBanksToAdd":[{"id":bank["id"],"hub":"SYR","startMinute":bank["startMinute"],"endMinute":bank["endMinute"]}],
     "hubBankCountOverrides":{"SYR":8},
     "retimeLegs":[{"legId":hold["returnLegId"],"expectedDepartureMinute":hold["scheduledDepartureMinute"],
                    "expectedArrivalMinute":hold["scheduledArrivalMinute"],
                    "departureMinute":option["targetDeparture"],"arrivalMinute":option["targetArrival"]}],
     "bankAssignmentReplacements":[{"legId":hold["returnLegId"],"operation":"arrival","bankId":bank["id"]}]}
   c=apply_optimization_overlay(base,ov)
   s=validate_schedule(c);night=validate_overnight_turns(c)
   op=validate_operating_rules(c)
   planning=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
   try:export_gate_schedule(c);gate="pass"
   except Exception as e:gate=f"{type(e).__name__}: {str(e)[:220]}"
   rec.update(structure=s["status"],overnight=night["status"],planning=planning["status"],gate=gate,
     operating=op["summary"],failed=[{"check":x["id"],"findings":x.get("findings",[])[:4]} for x in op["checks"] if x["status"]=="fail"])
   rec["pass"]=s["status"]==night["status"]==planning["status"]=="pass" and op["summary"]["effectiveErrorFindings"]==0 and gate=="pass"
   if rec["pass"]:rec["overlay"]=ov
  except Exception as e:rec.update(pass_=False,error=repr(e),trace=traceback.format_exc()[-600:])
  results.append(rec)
(out/"syr_single_return_feasibility.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps({
 "holds":len(inventory),
 "theoretical":len(results),
 "pass":sum(x.get("pass",False) for x in results),
 "byBank":{bank["code"]:{"theoretical":sum(x["bank"]==bank["id"] for x in results),
   "pass":sum(x["bank"]==bank["id"] and x.get("pass",False) for x in results)} for bank in banks},
 "failures":[{"route":x["route"],"from":x["station"],"bank":x["bank"],"failed":[v["check"] for v in x.get("failed",[])],
 "gate":x.get("gate"),"error":x.get("error")} for x in results if not x.get("pass")],
 },indent=2))
