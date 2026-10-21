"""Try BNA-MCI #1080 advancement to connect MCI-OMA #1636, with legal preceding R705 turn."""
from pathlib import Path
import json
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.validation import validate_schedule
src=Path("scripts/v142_release_candidate.py").read_text()
exec(src.split("struct=validate_schedule(s)")[0],globals())
new=[x for x in s["legs"] if x["route"]==359]
s["legs"]=[x for x in s["legs"] if x["route"]!=359 or x in new[:2]]
for l,t in zip(new[:2],[1210,1330]):
 l["departureMinute"]=t;l["arrivalMinute"]=t+75;l["departure"]=clock(t);l["arrival"]=clock(t+75)
for n,t in [(1235,1045),(1236,1145)]:
 l=next(l for l in s["legs"] if l["flight"]==n);shift=t-l["departureMinute"]
 l["departureMinute"]=t;l["arrivalMinute"]+=shift;l["departure"]=clock(t);l["arrival"]=clock(l["arrivalMinute"])
for d1077 in (884,):
 for d1080 in (1016,1010,1005):
  c=__import__("copy").deepcopy(s)
  for n,t in [(1077,d1077),(1080,d1080)]:
   l=next(l for l in c["legs"] if l["flight"]==n);shift=t-l["departureMinute"]
   l["departureMinute"]=t;l["arrivalMinute"]+=shift;l["departure"]=clock(t);l["arrival"]=clock(l["arrivalMinute"])
  for assignment in c['bankAssignments']:
   if assignment['legId']==next(l['id'] for l in c['legs'] if l['flight']==1080) and assignment['operation']=='arrival':assignment['bankId']='MCI-B9'
  # MCI arrival is now within the earlier B9 bank
  op=validate_operating_rules(c)
  try:export_gate_schedule(c);gate=True
  except Exception as e:gate=str(e)
  failed=[(k["id"],[x["id"] for x in k["findings"] if "override" not in x][:5]) for k in op["checks"] if k["status"]=="fail"]
  print(json.dumps({"1077":d1077,"1080":d1080,"MCIarrival":d1080+89,"transferToOMA":1135-(d1080+89),"errors":op["summary"]["effectiveErrorFindings"],"gate":gate,"failed":failed}),flush=True)
