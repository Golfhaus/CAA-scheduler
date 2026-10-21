"""Identify real existing aircraft holds that could absorb v1.4.2 turns."""
from pathlib import Path
import json
s=json.loads(Path("data/schedules/schedule_7_v1_4_1/canonical_schedule.json").read_text())
routes={}
for leg in s["legs"]:routes.setdefault(leg["route"],[]).append(leg)
for arr in routes.values():arr.sort(key=lambda x:x["sequenceWithinRoute"])
def operating(m):return m if m>=180 else m+1440
targets=[("SYR","RDU",680,770,810,900),("DAY","SRQ",600,745,790,935),("BHM","BNA",815,890,930,1005)]
for station,city,a,b,c,d in targets:
 print("\nTARGET",station,city,[(a,b),(c,d)])
 possibilities=[]
 for id,arr in routes.items():
  for x,y in zip(arr,arr[1:]):
   if x["destination"]!=station or y["origin"]!=station:continue
   a0=operating(x["arrivalMinute"]);d0=operating(y["departureMinute"])
   if d0<a0:d0+=1440
   possibilities.append({"route":id,"line":arr[0]["line"],"day":arr[0]["day"],"fleet":arr[0]["fleet"],"arrival":x["flight"],"arrClock":x["arrival"],"next":y["flight"],"nextClock":y["departure"],"hold":d0-a0,"fitsTarget":a-a0>=40 and d0-d>=40,"marginIn":a-a0,"marginOut":d0-d})
 possibilities.sort(key=lambda x:(not x["fitsTarget"],-x["hold"]))
 print(json.dumps(possibilities[:30],indent=2))
