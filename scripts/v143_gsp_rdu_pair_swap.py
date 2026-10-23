"""Test a genuine R338/R345 cross-line PHF-GSP / PHF-RDU flight-pair exchange.

This experiment retains the 1,286-flight accepted draft and the independent 1,292-flight builder.

Inputs: preserved 1286-flight v1.4.3 draft and separately staged R313/R338/R345
1292-flight experimental reconstruction. Does not alter the accepted draft.
"""
import runpy,copy,json
from pathlib import Path
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot

state=runpy.run_path("scripts/v143_seven_route_rebuild_candidate.py")
s=copy.deepcopy(state["s"])
def clk(v):return f"{v//60%24:02d}:{v%60:02d}"
def change(leg,route,dep):
 anchor=next(x for x in s["legs"] if x["route"]==route)
 delta=dep-leg["departureMinute"]
 leg.update(route=route,line=anchor["line"],day=anchor["day"],departureMinute=dep,
            arrivalMinute=leg["arrivalMinute"]+delta)
 leg["departure"]=clk(leg["departureMinute"]);leg["arrival"]=clk(leg["arrivalMinute"])
 # Require an explicit unique active bank if the leg has a bank assignment.
 for a in s["bankAssignments"]:
  if a["legId"]!=leg["id"]:continue
  station=leg["origin"] if a["operation"]=="departure" else leg["destination"]
  minute=leg["departureMinute"] if a["operation"]=="departure" else leg["arrivalMinute"]
  options=[b for b in s["hubBanks"] if b["hub"]==station and b["startMinute"]<=minute<=b["endMinute"]]
  if len(options)!=1:raise ValueError(f"Missing or ambiguous {station} bank for {leg['id']} at {clk(minute)}: {options}")
  a["bankId"]=options[0]["id"]

# Existing flights retain their numbers and markets; move from AS day6 to AK day1.
change(next(x for x in s["legs"] if x["flight"]==2035),338,833)  # PHF-GSP 13:53-15:08
change(next(x for x in s["legs"] if x["flight"]==2036),338,948)  # GSP-PHF 15:48-17:03
# Transfer the newly staged PHF-RDU-PHF side-turn from AK day1 to AS day6.
rdu_out=next(x for x in s["legs"] if x["id"].startswith("V143-REBUILD-R338-0-PHF-RDU"))
rdu_in=next(x for x in s["legs"] if x["id"].startswith("V143-REBUILD-R338-1-RDU-PHF"))
change(rdu_out,345,1155)  # PHF-RDU 19:15-20:05
change(rdu_in,345,1245)   # RDU-PHF 20:45-21:35
# R338 PHF-SAV now follows inbound GSP with its required 40min turn.
change(next(x for x in s["legs"] if x["flight"]==1493),338,1065) # PHF-SAV 17:45-19:11

for route in (338,345):
 matches=sorted((x for x in s["legs"] if x["route"]==route),key=lambda x:x["departureMinute"])
 for seq,x in enumerate(matches,1):x["sequenceWithinRoute"]=seq

s["schedule"].update(id="schedule_7_v1_4_3_gsp_rdu_swap_candidate",version="1.4.3-swap-test",
                     label="Schedule 7 v1.4.3 GSP/RDU pair swap (unpublished)",status="draft")
struct=validate_schedule(s)
night=validate_overnight_turns(s)
op=validate_operating_rules(s)
try:gates=export_gate_schedule(s);gate_status="pass"
except Exception as error:gates=None;gate_status=str(error)
summary={"legs":len(s["legs"]),"routes":len({x["route"] for x in s["legs"]}),
"structure":struct["status"],"overnight":night["status"],"gate":gate_status,
"effectiveOperatingErrors":op["summary"]["effectiveErrorFindings"],
"failures":[{"id":c["id"],"items":[f["id"] for f in c["findings"] if "override" not in f][:8]}
 for c in op["checks"] if c["status"]=="fail"]}
print("GSP_RDU_SWAP",json.dumps(summary),flush=True)
if summary["structure"]!="pass" or summary["overnight"]!="pass" or summary["gate"]!="pass" or summary["effectiveOperatingErrors"]!=0:
 raise SystemExit("Swap is not native-valid; accepted draft remains unchanged")
planning=reconstruct_planning_snapshot(s,demand_data_version="bts-db1c-6mo-jul2025-apr2026-v7")
plancheck=validate_planning_snapshot(planning,s)
print("PLANNING",plancheck["status"],flush=True)
if plancheck["status"]!="pass":raise SystemExit("Planning check failed")
out=Path("data/schedules/schedule_7_v1_4_3_gsp_rdu_swap_candidate")
out.mkdir(parents=True,exist_ok=True)
for filename,obj in {"canonical_schedule.json":s,"validation_report.json":struct,
"overnight_turn_validation.json":night,"operating_validation_report.json":op,
"gates.json":gates,"planning_snapshot.json":planning,
"planning_validation_report.json":plancheck}.items():
 (out/filename).write_text(json.dumps(obj,indent=2)+"\n")
print("GSP_RDU_SWAP_NATIVE_VALIDATED",flush=True)
