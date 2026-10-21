"""Measure all internal ground holds and endpoint slack on five CRJ700 routes."""
import json
from pathlib import Path
s=json.loads(Path("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json").read_text())
for route in (339,303,313,316,319):
 ls=sorted((x for x in s["legs"] if x["route"]==route),key=lambda x:x["sequenceWithinRoute"])
 print("ROUTE",route,"LINE",ls[0]["line"],"DAY",ls[0]["day"],"FLEET",ls[0]["fleet"])
 for a,b in zip(ls,ls[1:]):
  duration=(b["departureMinute"]-a["arrivalMinute"])%1440
  print(json.dumps(dict(station=a["destination"],arrival=a["arrival"],nextDeparture=b["departure"],minutes=duration,roomOver40=duration-40,flightIn=a["flight"],flightOut=b["flight"])))
 # Other routing-days at the same endpoint stations, useful for holistic swaps
 for station in {l["destination"] for l in ls}:
  alternatives=[x for x in s["legs"] if x["fleet"]=="CRJ700" and x["route"]!=route and (x["origin"]==station or x["destination"]==station)]
  print("STATION",station,"CRJ700-OTHER",len(alternatives))
