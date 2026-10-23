"""Reassign existing SAV–JAX–SAV from AK day 1/R338 to day 2/R339.
Preserves flight numbers, line, fleet, endpoints and published main.
Then screen an additional late R338 SAV turn as optional, not assumed.
"""
import copy,json
from pathlib import Path
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
root=Path("data/schedules/schedule_7_v1_4_3_draft")
original=json.loads((root/"canonical_schedule.json").read_text())
def clk(x):return f"{x//60%24:02d}:{x%60:02d}"
def update_leg(s,num,route=None,departure=None):
 l=next(x for x in s["legs"] if x["flight"]==num)
 if route is not None:
  anchor=next(x for x in s["legs"] if x["route"]==route)
  l.update(route=route,line=anchor["line"],day=anchor["day"])
 if departure is not None:
  change=departure-l["departureMinute"]
  l["departureMinute"]+=change;l["arrivalMinute"]+=change
  l["departure"]=clk(l["departureMinute"]);l["arrival"]=clk(l["arrivalMinute"])
 # Reassign any existing hub operation to its exact time window.
 for a in s["bankAssignments"]:
  if a["legId"]!=l["id"]:continue
  station=l["origin"] if a["operation"]=="departure" else l["destination"]
  minute=l["departureMinute"] if a["operation"]=="departure" else l["arrivalMinute"]
  eligible=[b for b in s["hubBanks"] if b["hub"]==station and b["startMinute"]<=minute<=b["endMinute"]]
  if len(eligible)==1:a["bankId"]=eligible[0]["id"]
 return l
def assess(s,label):
 for route in (338,339):
  matches=sorted((l for l in s["legs"] if l["route"]==route),key=lambda x:x["departureMinute"])
  for i,l in enumerate(matches,1):l["sequenceWithinRoute"]=i
 structural=validate_schedule(s);overnight=validate_overnight_turns(s);op=validate_operating_rules(s)
 try:gates=export_gate_schedule(s);gate="pass"
 except Exception as e:gates=None;gate=str(e)
 status={"scenario":label,"legs":len(s["legs"]),"structure":structural["status"],"overnight":overnight["status"],"gates":gate,"operatingErrors":op["summary"]["effectiveErrorFindings"],"failed":[{"check":x["id"],"findings":[v["id"] for v in x["findings"] if "override" not in v][:8]} for x in op["checks"] if x["status"]=="fail"]}
 print(json.dumps(status),flush=True)
 valid=structural["status"]=="pass" and overnight["status"]=="pass" and gate=="pass" and not status["operatingErrors"]
 if valid:
  planning=reconstruct_planning_snapshot(s,demand_data_version="bts-db1c-6mo-jul2025-apr2026-v7")
  pv=validate_planning_snapshot(planning,s)
  print("PLANNING",label,pv["status"],flush=True)
  valid=pv["status"]=="pass"
 else:planning=pv=None
 return valid,dict(canonical=s,structural=structural,overnight=overnight,operating=op,gates=gates,planning=planning,planningValidation=pv)
s=copy.deepcopy(original)
update_leg(s,2068,departure=350) # BHM–SAV 05:50–08:03.
update_leg(s,2127,route=339,departure=523) # SAV–JAX 08:43–09:28.
update_leg(s,2128,route=339,departure=608) # JAX–SAV 10:08–10:53.
s["schedule"].update(id="schedule_7_v1_4_3_ak_transfer_candidate",version="1.4.3-AK-test",label="Schedule 7 v1.4.3 AK route exchange (unpublished)",status="draft")
good,data=assess(s,"transferred SAV-JAX pair")
if not good:
 print("NO_VALID_AK_TRANSFER: preserved accepted draft untouched",flush=True)
 raise SystemExit(1)
out=Path("data/schedules/schedule_7_v1_4_3_ak_transfer_candidate")
out.mkdir(parents=True,exist_ok=True)
files={"canonical_schedule.json":data["canonical"],"validation_report.json":data["structural"],"overnight_turn_validation.json":data["overnight"],"operating_validation_report.json":data["operating"],"gates.json":data["gates"],"planning_snapshot.json":data["planning"],"planning_validation_report.json":data["planningValidation"]}
for filename,obj in files.items():(out/filename).write_text(json.dumps(obj,indent=2)+"\n")
print("AK_TRANSFER_VALIDATED_FOR_COVERAGE_GUARD",flush=True)
# Investigate optional longer R338 end-of-day SAV–BWI–SAV using the freed slot.
variant=copy.deepcopy(s);template=next(l for l in variant["legs"] if l["route"]==338)
newpair=max(x["pairing"] for x in variant["legs"])+1
newflight=max(x["flight"] for x in variant["legs"])+1
for i,(origin,destination,dep,arr) in enumerate([("SAV","BWI",1105,1185),("BWI","SAV",1225,1305)]):
 l={**template,"id":f"V143-R338-BWI-{i}","pairing":newpair+i,"flight":newflight+i,"origin":origin,"destination":destination,"departureMinute":dep,"arrivalMinute":arr,"departure":clk(dep),"arrival":clk(arr)}
 variant["legs"].append(l)
 for station,operation,minute in [(origin,"departure",dep),(destination,"arrival",arr)]:
  match=[b for b in variant["hubBanks"] if b["hub"]==station and b["startMinute"]<=minute<=b["endMinute"]]
  if len(match)==1:variant["bankAssignments"].append({"legId":l["id"],"operation":operation,"bankId":match[0]["id"]})
assess(variant,"transfer plus exploratory SAV-BWI turn")
