"""Demand-aware daytime alternatives for R160, R176 and R158.

Read-only screen against R144+R146 validated working baseline.
Reject any scenario failing canonical native operating, overnight, planning or gates.
"""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.bank_placement import _block_minutes,_local_arrival
base=json.loads((ROOT/"outputs/schedule_7_v1_3_2_selected/canonical_schedule.json").read_text())
out=ROOT/"outputs/schedule_7_v1_3_2_daytime_screen";out.mkdir(parents=True,exist_ok=True)
cities={c["code"]:c for c in base["cities"]}
profile=next(x for x in json.loads((ROOT/"config/policies/planning_rules_v7.json").read_text())["frequencyAllocation"]["fleetProfiles"] if x["fleet"]=="CRJ200")
old={x["flight"]:x for x in base["legs"]}
banks=base["hubBanks"];hubset=set(base["operatingPolicy"]["hubs"])
assign={(x["legId"],x["operation"]):x["bankId"] for x in base.get("bankAssignments",[])}
def bank(city,minute):
 choices=[b for b in banks if b["hub"]==city and b["startMinute"]<=minute<b["endMinute"]]
 return choices[0]["id"] if choices else None
def proposal():
 return {"baseSchedule":{"scheduleId":base["schedule"]["id"]},"schedule":base["schedule"]}
def retime(o,flight,d):
 l=old[flight];delta=d-l["departureMinute"]
 arr=l["arrivalMinute"]+delta
 if not(0<=d<1440 and 0<=arr<1440):raise ValueError("clock overflow")
 o.setdefault("retimeLegs",[]).append({"legId":l["id"],"expectedDepartureMinute":l["departureMinute"],"expectedArrivalMinute":l["arrivalMinute"],"departureMinute":d,"arrivalMinute":arr})
 for city,op,t in ((l["origin"],"departure",d),(l["destination"],"arrival",arr)):
  if city not in hubset:continue
  target=bank(city,t)
  if not target:raise ValueError(f"Retimed flight {flight} {op} {city} off bank at {t}")
  if (l["id"],op) in assign and assign[l["id"],op]!=target:
   o.setdefault("bankAssignmentReplacements",[]).append({"legId":l["id"],"operation":op,"bankId":target})
 return arr
def insert(o,route,origin,dest,d,tag):
 duration=_block_minutes(origin,dest,profile,cities)
 a=_local_arrival(d,duration,origin,dest,cities)
 ident=f"V132-DAY-{route}-{tag}-{origin}-{dest}"
 o.setdefault("insertLegs",[]).append({"id":ident,"route":route,"origin":origin,"destination":dest,"departureMinute":d,"arrivalMinute":a})
 for city,op,t in ((origin,"departure",d),(dest,"arrival",a)):
  if city not in hubset:continue
  target=bank(city,t)
  if not target:raise ValueError(f"Inserted {ident} {op} {city} off bank {t}")
  o.setdefault("bankAssignmentsToAdd",[]).append({"legId":ident,"operation":op,"bankId":target})
 return a
def turn(o,route,origin,dest,start,tag):
 arrival=insert(o,route,origin,dest,start,tag)
 return insert(o,route,dest,origin,arrival+40,tag)
def r176(dest):
 o=proposal()
 retime(o,1761,555)  # GSO 09:15 -> PHF 10:11, into M1
 arrival=turn(o,176,"PHF",dest,651,dest)
 next_depart=max(835,arrival+40)
 if next_depart>844:raise ValueError(f"No legal PHF B4 departure after {dest}, need {next_depart}")
 retime(o,1615,next_depart)
 return o
def r160(dest):
 o=proposal()
 retime(o,1829,800) # BTV 13:20 -> SYR 14:12 B4, rather than 15:15 -> 16:07 B5
 arrival=turn(o,160,"SYR",dest,1005,dest) # 16:45 SYR B5, return B6
 dep=max(1140,arrival+40)
 if dep>=1185:raise ValueError(f"SYR B6 ends before {dest} return turnover")
 retime(o,1701,dep)
 return o
def r158(dest):
 o=proposal()
 retime(o,1868,615)  # LEX 10:15 -> DAY 11:01
 retime(o,1657,702)  # DAY 11:42 -> SYR 13:15 B4
 arrival=turn(o,158,"SYR",dest,838,dest) # 13:58 SYR B4, return at B5
 dep=max(1005,arrival+40)
 if dep>=1020:raise ValueError(f"SYR B5 ends before {dest} return turnover")
 retime(o,1752,dep)
 return o
cases={**{f"R176_PHF_{d}":lambda d=d:r176(d) for d in ["RDU","BWI","ROA","GSO"]},
 **{f"R160_SYR_{d}":lambda d=d:r160(d) for d in ["ROC","BUF","ALB","AVP"]},
 **{f"R158_SYR_{d}":lambda d=d:r158(d) for d in ["ROC","BUF","AVP","ALB"]}}
results={}
for name,make in cases.items():
 try:
  overlay=make();c=apply_optimization_overlay(base,overlay)
  structural=validate_schedule(c);operating=validate_operating_rules(c)
  overnight=validate_overnight_turns(c)
  planning=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
  try:
   gates=export_gate_schedule(c);gate="pass"
  except Exception as e:gate=repr(e)
  ok=(structural["status"]==overnight["status"]==planning["status"]=="pass" and operating["summary"]["effectiveErrorFindings"]==0 and gate=="pass")
  results[name]={"pass":ok,"structural":structural["status"],"overnight":overnight["status"],"planning":planning["status"],"gate":gate,"operating":operating["summary"],"failedChecks":[{"id":x["id"],"findings":x.get("findings",[])[:4]} for x in operating["checks"] if x["status"]=="fail"],"overlay":overlay}
  if ok:
   (out/(name+"_overlay.json")).write_text(json.dumps(overlay,indent=2)+"\n")
   (out/(name+"_canonical.json")).write_text(json.dumps(c,indent=2)+"\n")
  print(name,"PASS" if ok else "FAIL","gate",gate,"failures",[(z["id"],len(z["findings"])) for z in results[name]["failedChecks"]],flush=True)
 except Exception as e:
  results[name]={"pass":False,"exception":repr(e),"traceback":traceback.format_exc()[-1500:]}
  print(name,"ERROR",str(e),flush=True)
 (out/"physical_screen.json").write_text(json.dumps(results,indent=2)+"\n")
