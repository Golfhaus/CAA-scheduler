"""Debug near-compliant four-leg BNA/BHM gate pattern (one unresolved touch)."""
import json,sys,pathlib
from caa_scheduler.operating_validation import validate_operating_rules
from caa_scheduler.gate_export import export_gate_schedule
src=pathlib.Path("scripts/v142_release_candidate.py").read_text()
exec(src.split("struct=validate_schedule(s)")[0],globals())
# Two-leg BNA-BHM dedicated ECP connector, OMA handled by retimed R705.
newleg=[x for x in s["legs"] if x["route"]==359]
s["legs"]=[x for x in s["legs"] if x["route"]!=359 or x in newleg[:2]]
for l,d in zip(newleg[:2],[1020,1315]):
 l["departureMinute"]=d;l["arrivalMinute"]=d+75;l["departure"]=clock(d);l["arrival"]=clock(d+75)
retime=next(l for l in s["legs"] if l["flight"]==1080)
retime["departureMinute"]=1013;retime["arrivalMinute"]=1102
retime["departure"]=clock(1013);retime["arrival"]=clock(1102)
for x in s["bankAssignments"]:
 if x["legId"]==retime["id"] and x["operation"]=="arrival":x["bankId"]="MCI-B9"
report=validate_operating_rules(s)
for c in report["checks"]:
 if c["id"] in ("passenger_touch_on_stand","fixed_physical_inventory","bank_alignment","departure_windows"):
  print(json.dumps({"id":c["id"],"status":c["status"],"findings":[{"id":f["id"],"evidence":f.get("evidence")} for f in c["findings"] if "override" not in f]},indent=2),flush=True)
try:export_gate_schedule(s);print("GATES PASS")
except Exception as e:print("GATES FAIL",e)
