"""Experimental AH day-9/day-10 aircraft reassignment on top of the native-pass 1,292-leg candidate.
Run manually, not on every push. Source acceptance draft (1,286) and 1,292 baseline are not edited.
"""
import json,runpy,copy
from pathlib import Path
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules, validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.planning import reconstruct_planning_snapshot, validate_planning_snapshot

# Rebuild the existing 1,292-leg separate experimental candidate first.
ctx=runpy.run_path("scripts/v143_seven_route_rebuild_candidate.py",run_name="__main__")
s=copy.deepcopy(ctx["s"])
assert len(s["legs"])==1292
old319=[l for l in s["legs"] if l["route"]==319]
old320=[l for l in s["legs"] if l["route"]==320]
assert len(old319)==6 and len(old320)==5

def clock(minute):
 return f"{minute//60%24:02d}:{minute%60:02d}"
def retime(flight,departure):
 l=next(x for x in s["legs"] if x["flight"]==flight)
 shift=departure-l["departureMinute"]
 l["departureMinute"]=departure
 l["arrivalMinute"]+=shift
 l["departure"]=clock(l["departureMinute"])
 l["arrival"]=clock(l["arrivalMinute"])
 return l
def assign_banks(leg):
 for a in s["bankAssignments"]:
  if a["legId"]!=leg["id"]:continue
  code=leg["origin"] if a["operation"]=="departure" else leg["destination"]
  minute=leg["departureMinute"] if a["operation"]=="departure" else leg["arrivalMinute"]
  choices=[b for b in s["hubBanks"] if b["hub"]==code and b["startMinute"]<=minute<=b["endMinute"]]
  if len(choices)==1:a["bankId"]=choices[0]["id"]

# AH R320: SRQ-SYR return arrives 12:36 (42-minute SRQ turn);
# 40-minute SYR turn, existing 85/85-minute SYR-PHF pair, 40-minute SYR turn,
# 107-minute CLT sector and 40-minute CLT turn to BDL terminator.
changed=[retime(1302,580),retime(1307,1051),retime(1102,1198)]
for flight,dep in [(1951,796),(1952,926)]:
 l=retime(flight,dep)
 l["route"]=320
 l["day"]=10
 assert l["line"]=="AH"
 changed.append(l)
# The original R319 SRQ-SYR arrives SYR at 10:41. Use its freed 8h14m
# for a BNA turn while preserving the 18:55 SYR-BWI/SYR-ABE continuation.
template=next(x for x in s["legs"] if x["route"]==319)
newpair=max(x["pairing"] for x in s["legs"])+1
newflight=max(x["flight"] for x in s["legs"])+1
for i,(origin,dest,dep,arr) in enumerate([
 ("SYR","BNA",690,754),   # 11:30 ET -> 12:34 CT; 124-minute elapsed
 ("BNA","SYR",794,978),   # 13:14 CT -> 16:18 ET; 124-minute elapsed
]):
 ident=f"V143-AH-REASSIGN-R319-BNA-{i}"
 l={**template,"id":ident,"route":319,"day":9,"origin":origin,
    "destination":dest,"flight":newflight+i,"pairing":newpair+i,
    "departureMinute":dep,"arrivalMinute":arr,
    "departure":clock(dep),"arrival":clock(arr),"sequenceWithinRoute":0}
 s["legs"].append(l)
 changed.append(l)
 for code,operation,minute in [(origin,"departure",dep),(dest,"arrival",arr)]:
  choices=[b for b in s["hubBanks"] if b["hub"]==code and b["startMinute"]<=minute<=b["endMinute"]]
  if len(choices)==1:s["bankAssignments"].append({
   "legId":ident,"operation":operation,"bankId":choices[0]["id"]})
for leg in changed:assign_banks(leg)
for route in (319,320):
 for i,l in enumerate(sorted((x for x in s["legs"] if x["route"]==route),
                              key=lambda x:x["departureMinute"]),1):
  l["sequenceWithinRoute"]=i
assert len(s["legs"])==1294
assert all(l["route"]==320 for l in s["legs"] if l["flight"] in (1951,1952))
assert [l["origin"] for l in sorted((x for x in s["legs"] if x["route"]==319),key=lambda x:x["sequenceWithinRoute"])][0]=="SRQ"
s["schedule"].update(id="schedule_7_v1_4_3_ah_reassignment_experiment",
                     version="1.4.3-ah-experiment",status="draft")
v=validate_schedule(s)
o=validate_operating_rules(s)
n=validate_overnight_turns(s)
try:
 g=export_gate_schedule(s); gate="pass"
except Exception as e:
 g=None; gate=str(e)
summary={
 "legs":len(s["legs"]),"reassignedFlights":[1951,1952],
 "newBNAFlights":[newflight,newflight+1],
 "structural":v["status"],"overnight":n["status"],
 "gate":gate,"errors":o["summary"]["effectiveErrorFindings"],
 "failedChecks":[{"id":c["id"],
   "findings":[f["id"] for f in c["findings"] if "override" not in f][:8]}
   for c in o["checks"] if c["status"]=="fail"]}
print(json.dumps(summary,indent=2),flush=True)
if v["status"]=="pass" and n["status"]=="pass" and gate=="pass" and summary["errors"]==0:
 p=reconstruct_planning_snapshot(s,demand_data_version="bts-db1c-6mo-jul2025-apr2026-v7")
 pv=validate_planning_snapshot(p,s)
 print("PLANNING",pv["status"],flush=True)
 if pv["status"]=="pass":
  out=Path("data/schedules/schedule_7_v1_4_3_ah_reassignment_experiment")
  out.mkdir(parents=True,exist_ok=True)
  for filename,datum in {"canonical_schedule.json":s,
   "validation_report.json":v,"operating_validation_report.json":o,
   "overnight_turn_validation.json":n,"planning_snapshot.json":p,
   "planning_validation_report.json":pv,"gates.json":g}.items():
   (out/filename).write_text(json.dumps(datum,indent=2)+"\n")
  print("AH_REASSIGNMENT_NATIVE_PASS; run v143_rebuild_guard.mjs before adoption")
