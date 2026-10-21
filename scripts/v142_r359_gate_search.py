"""Search legal four-flight BNA-BHM gate patterns without changing physical inventories."""
import pathlib,random,json,sys
from caa_scheduler.gate_export import export_gate_schedule
# Reuse the deterministic latest combined construction up to its validation statements.
source=pathlib.Path("scripts/v142_release_candidate.py").read_text()
exec(source.split("struct=validate_schedule(s)")[0],globals())
original=[l for l in s["legs"] if l["route"]==359]
assert len(original)==4
rng=random.Random(142)
def test(dep):
 times=[]
 prev_arr=None
 for i,t in enumerate(dep):
  arr=t+75
  if prev_arr is not None and t-prev_arr<40:return None
  prev_arr=arr
  times.append((t,arr))
 if not(870<=times[0][1]<=1040 and 1076<=times[2][1]<=1286 and 1299<=dep[3]<=1410):return None
 if dep[0]<270 or dep[2]>1260:return None
 for leg,(d,a) in zip(original,times):
  leg["departureMinute"]=d;leg["arrivalMinute"]=a
  leg["departure"]=clock(d);leg["arrival"]=clock(a)
 try:
  export_gate_schedule(s);return 0
 except Exception as exc:
  import re
  m=re.search(r"(\d+) passenger touch",str(exc))
  return int(m.group(1)) if m else 100
best=(100,None);successes=[]
# Grid over operationally sensible bank times; prefer low slack and realistic long holds.
choices=[
 list(range(870,1001,10)),
 list(range(1020,1161,10)),
 list(range(1120,1251,10)),
 list(range(1300,1411,10)),
]
for i in range(550):
 d1=rng.choice(choices[0])
 d2=rng.choice([v for v in choices[1] if v>=d1+115] or choices[1])
 d3=rng.choice([v for v in choices[2] if v>=d2+115] or choices[2])
 d4=rng.choice([v for v in choices[3] if v>=d3+115] or choices[3])
 d=(d1,d2,d3,d4)
 n=test(d)
 if n is None:continue
 if n<best[0]:
  best=(n,d)
  print(json.dumps({"trial":i,"bestGateMisses":n,"departures":d}),flush=True)
 if n==0:
  successes.append(d)
  if len(successes)>=5:break

# Concentrate on +/-30min of the best found global pattern.
for i in range(2500):
 center=best[1] or (900,1050,1210,1350)
 d=tuple(center[j]+rng.choice(range(-30,31,5)) for j in range(4))
 n=test(d)
 if n is None:continue
 if n<best[0]:
  best=(n,d);print(json.dumps({"localTrial":i,"bestGateMisses":n,"departures":d}),flush=True)
 if n==0:
  successes.append(d)
  if len(successes)>=5:break
if best[1]:
 test(best[1])
 from caa_scheduler.operating_validation import validate_operating_rules
 rep=validate_operating_rules(s)
 print(json.dumps({"bestFindings":{c["id"]:[{"id":f["id"],"evidence":f.get("evidence",{})} for f in c["findings"]] for c in rep["checks"] if c["id"] in ("passenger_touch_on_stand","fixed_physical_inventory")}},default=str),flush=True)
print(json.dumps({"best":best,"successes":successes}),flush=True)

