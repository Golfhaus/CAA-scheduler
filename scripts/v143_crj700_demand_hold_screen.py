"""Find promising short point-to-point turns inside existing long CRJ700 holds.
Read-only discovery; no timetable changes or release state edits.
"""
import json, math
from pathlib import Path
from collections import defaultdict,Counter
s=json.loads(Path("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json").read_text())
lines=Path("data/reference/airport_od_matrix_consolidated_v2.csv").read_text().splitlines()
hdr=next(i for i,l in enumerate(lines) if l.startswith("Origin \\ Dest"))
codes=lines[hdr].split(",")[1:]
od={}
for line in lines[hdr+1:]:
 row=line.split(",")
 if len(row)==len(codes)+1:od[row[0]]={c:float(row[i+1] or 0) for i,c in enumerate(codes)}
geo={x["code"]:x for x in s["cities"] if x["active"]}
rad=math.pi/180
def dist(a,b):
 x,y=geo[a],geo[b]
 z=math.sin((y["latitude"]-x["latitude"])*rad/2)**2+math.cos(x["latitude"]*rad)*math.cos(y["latitude"]*rad)*math.sin((y["longitude"]-x["longitude"])*rad/2)**2
 return 3440.065*2*math.asin(min(1,math.sqrt(z)))
freq=Counter((x["origin"],x["destination"]) for x in s["legs"])
direct={}
for leg in s["legs"]:
 directed=(leg["origin"],leg["destination"])
 duration=(leg["arrivalMinute"]-leg["departureMinute"])%1440
 off={"Eastern":-4,"Central":-5,"Mountain":-6,"Pacific":-7}
 # arrival clock - origin departure clock; convert to duration UTC
 duration=(duration-(off[geo[leg["destination"]]["timezone"]]-off[geo[leg["origin"]]["timezone"]])*60)%1440
 if duration<300:direct[directed]=min(direct.get(directed,300),duration)
for route in [339,303,313,316,319]:
 legs=sorted((x for x in s["legs"] if x["route"]==route),key=lambda x:x["sequenceWithinRoute"])
 print("ROUTE",route)
 for a,b in zip(legs,legs[1:]):
  city=a["destination"];hold=(b["departureMinute"]-a["arrivalMinute"])%1440
  if hold<100:continue
  opts=[]
  for destination in geo:
   if destination==city:continue
   d=dist(city,destination)
   block=direct.get((city,destination)) or round((32+d*60/380)/5)*5
   reverse=direct.get((destination,city)) or round((32+d*60/380)/5)*5
   # at least 40 each beginning, destination, end
   if block+reverse+120>hold:continue
   demand=(od.get(city,{}).get(destination,0)+od.get(destination,{}).get(city,0))
   if demand<12:continue
   opts.append(dict(dest=destination,distanceNm=round(d),block=block,reverse=reverse,roundOD=round(demand,1),existingAB=freq[city,destination],existingBA=freq[destination,city],turnRequired=block+reverse+120,slack=hold-(block+reverse+120)))
  opts.sort(key=lambda x:(-(x["roundOD"]*(1.4 if x["existingAB"]+x["existingBA"]==0 else 1)),x["turnRequired"]))
  print(json.dumps({"station":city,"hold":hold,"options":opts[:16]}))
