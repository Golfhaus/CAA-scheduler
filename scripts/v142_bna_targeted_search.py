"""Search BNA/BHM geometry with a two-leg R359 and targeted existing flight retimes.
Keeps gates fixed; prints only valid or best attempts.
"""
import pathlib,random,json
from caa_scheduler.gate_export import export_gate_schedule
src=pathlib.Path("scripts/v142_release_candidate.py").read_text()
exec(src.split("struct=validate_schedule(s)")[0],globals())
allnew=[x for x in s["legs"] if x["route"]==359]
s["legs"]=[x for x in s["legs"] if x["route"]!=359 or x in allnew[:2]]
pair=allnew[:2]
# BNA-BHM departure must arrive before 21:56 BHM-ECP; ECP-BHM arrives 21:09,
# then BHM-BNA may depart at/after 21:39.
r512=[x for x in s["legs"] if x["flight"] in (1235,1236)]
r705=[x for x in s["legs"] if x["flight"]==1080][0]
def retime(leg,dep):
 delta=dep-leg["departureMinute"]
 leg["departureMinute"]=dep;leg["arrivalMinute"]+=delta
 leg["departure"]=clock(dep);leg["arrival"]=clock(leg["arrivalMinute"])
rng=random.Random(342)
best=(999,None)
for i in range(2600):
 # Target earlier R512 turn to clear BNA gate or move to later time; also target
 # one BNA-BHM ECP connector and return for next-day BNA R317.
 a=rng.randrange(1040,1211,5)
 b=rng.randrange(1300,1411,5)
 if b-(a+75)<40:continue
 retime(pair[0],a);retime(pair[1],b)
 # Try original R512 or limited timing changes in a valid 40-min turn pair.
 move=rng.choice([-55,-45,-35,-25,-15,0,15,25,35])
 retime(r512[0],1080+move);retime(r512[1],1180+move)
 try:
  export_gate_schedule(s);n=0
 except Exception as e:
  import re
  m=re.search(r"(\d+) passenger touch",str(e));n=int(m.group(1)) if m else 100
 if n<best[0]:
  best=(n,{"new":[a,b],"R512move":move})
  print(json.dumps({"trial":i,"best":best}),flush=True)
 if n==0:
  print("FOUND",json.dumps(best),flush=True);break
print("FINAL",json.dumps(best),flush=True)
