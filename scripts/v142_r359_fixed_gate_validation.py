"""Validate the discovered fixed-gate BNA-ECP pattern within the complete v1.4.2 candidate."""
import pathlib,json
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.validation import validate_schedule
src=pathlib.Path("scripts/v142_release_candidate.py").read_text()
exec(src.split("struct=validate_schedule(s)")[0],globals())
newlegs=[l for l in s["legs"] if l["route"]==359]
s["legs"]=[l for l in s["legs"] if l["route"]!=359 or l in newlegs[:2]]
for l,t in zip(newlegs[:2],[1210,1330]):
 l["departureMinute"]=t;l["arrivalMinute"]=t+75;l["departure"]=clock(t);l["arrival"]=clock(t+75)
for n,t in [(1235,1045),(1236,1145)]:
 l=next(l for l in s["legs"] if l["flight"]==n)
 d=t-l["departureMinute"];l["departureMinute"]=t;l["arrivalMinute"]+=d;l["departure"]=clock(t);l["arrival"]=clock(l["arrivalMinute"])
checks={"structural":validate_schedule(s)["status"],"overnight":validate_overnight_turns(s)["status"]}
try: export_gate_schedule(s);checks["gates"]="pass"
except Exception as e:checks["gates"]=str(e)
r=validate_operating_rules(s)
checks["effectiveErrors"]=r["summary"]["effectiveErrorFindings"]
checks["failures"]=[{"check":c["id"],"findingIds":[f["id"] for f in c["findings"] if "override" not in f][:20]} for c in r["checks"] if c["status"]=="fail"]
print(json.dumps(checks,indent=2),flush=True)
