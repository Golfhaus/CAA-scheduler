"""Read-only cross-line consolidation screen on the validated R144-augmented v1.3.2 draft.

This ranks plausible handoff locations, NOT a certified aircraft-release solution.
"""
from collections import defaultdict
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
src=ROOT/"outputs/schedule_7_v1_3_2_r144_accepted/canonical_schedule.json"
c=json.loads(src.read_text())
targets={160,176,146,158,107,125}
legs=c["legs"]
by_route=defaultdict(list)
by_line=defaultdict(list)
for leg in legs:
 by_route[int(leg["route"])].append(leg)
 by_line[str(leg["line"])].append(leg)
for arr in by_route.values():
 arr.sort(key=lambda l:l["sequenceWithinRoute"])
timezone={"Eastern":0,"Central":-60,"Mountain":-120,"Pacific":-180}
zones={city["code"]:timezone.get(city["timezone"],0) for city in c["cities"]}
def block(l):
 elapsed=(l["arrivalMinute"]-l["departureMinute"]+zones[l["origin"]]-zones[l["destination"]])%1440
 assert 20<=elapsed<=600,(l["flight"],elapsed)
 return elapsed
def critical(l):
 d=l["departureMinute"]
 b=block(l)
 # Evaluate against 06:00-22:00 in the originating station's local clock.
 return max(0,min(d+b,1320)-max(d,360))
def route_summary(route):
 arr=by_route[route]
 return {"route":route,"line":arr[0]["line"],"day":arr[0]["day"],
 "fleet":arr[0]["fleet"],"flights":len(arr),
 "blockMinutes":sum(map(block,arr)),"criticalMinutesOriginLocal":sum(map(critical,arr)),
 "starts":arr[0]["origin"],"ends":arr[-1]["destination"],
 "legs":[{"flight":x["flight"],"origin":x["origin"],"destination":x["destination"],
 "departureMinute":x["departureMinute"],"arrivalMinute":x["arrivalMinute"]} for x in arr]}
rows=[route_summary(k) for k in sorted(targets)]
line_routes={}
for line,items in by_line.items():
 if any(x["route"] in targets for x in items):
  route_days=defaultdict(list)
  for x in items:route_days[int(x["day"])].append(x)
  route_list=[]
  for day,daylegs in sorted(route_days.items()):
   daylegs.sort(key=lambda l:l["sequenceWithinRoute"])
   route_list.append({"day":day,"route":daylegs[0]["route"],"starts":daylegs[0]["origin"],
   "ends":daylegs[-1]["destination"],"flights":len(daylegs)})
  line_routes[line]=route_list
# A handoff is potentially useful when an existing aircraft finishes a leg at a
# station with a feasible 40+ minute turn before another line's next departure.
# Same-airport times are already in the same timezone. Evaluate all cross-line
# options, but label them as *splice candidates*, not validated schedules.
stations=defaultdict(list)
for leg in legs:
 if leg["fleet"]!="CRJ200":continue
 stations[leg["destination"]].append(("arrival",leg))
 stations[leg["origin"]].append(("departure",leg))
handoffs=[]
for airport,ops in stations.items():
 arrivals=[l for op,l in ops if op=="arrival" and l["route"] in targets]
 deps=[l for op,l in ops if op=="departure" and l["line"] in line_routes]
 for a in arrivals:
  for d in deps:
   if a["line"]==d["line"] or a["day"]!=d["day"]:continue
   gap=d["departureMinute"]-a["arrivalMinute"]
   if 40<=gap<=180:
    handoffs.append({"station":airport,"sourceRoute":a["route"],"sourceFlight":a["flight"],
     "sourceLine":a["line"],"targetRoute":d["route"],"targetFlight":d["flight"],
     "targetLine":d["line"],"day":a["day"],"gapMinutes":gap})
handoffs.sort(key=lambda x:(x["gapMinutes"],x["station"],x["sourceRoute"]))
result={
 "status":"diagnostic only — not a validated consolidation",
 "baseline":"R144 staged, unpublished; six target routes unchanged",
 "targetRoutes":rows,
 "physicalLineCountBefore":len(set(x["line"] for x in legs)),
 "targetDistinctLines":sorted(line_routes),
 "lineDayCycles":line_routes,
 "sameDayCrossLineHandoffCandidates":handoffs[:100],
 "candidateCount":len(handoffs),
 "caveats":[
 "A handoff does not remove an aircraft: full circular rotation and MX/RON constraints must pass.",
 "Cross-line handoffs at matching day numbers are only a starting search and do not prove physical co-location across line cycles.",
 "Critical period uses 06:00–22:00 at the flight origin, with timezone-adjusted elapsed duration; final app metric should independently verify clock convention.",
 "No passenger demand, gate/stand conflicts or one-stop network effects were certified for a consolidated candidate.",
 "R125 contains its prior PVD-BWI extension and is not the old 7-flight route." ]}
out=ROOT/"outputs/schedule_7_v1_3_2_consolidation"
out.mkdir(exist_ok=True,parents=True)
(out/"screen.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({"status":result["status"],"routes":rows,
 "candidateCount":len(handoffs),"handoffExamples":handoffs[:15]},indent=2))
