"""Cumulative AH R317/R319 pair exchange atop 1,292-flight experiment, not approved draft."""
from pathlib import Path
source=Path("scripts/v143_seven_route_rebuild_candidate.py").read_text()
pivot='s["schedule"].update(id="schedule_7_v1_4_3_rebuild_candidate"'
assert pivot in source
inject='''# Reassign paired flying across AH day 7 / AH day 9, retaining both route endpoints.
for number,route,dep,block in (
 (2103,319,720,54),(2104,319,834,174),
 (1951,317,1090,85),(1952,317,1215,85),
):
 leg=next(l for l in s["legs"] if l["flight"]==number)
 leg["route"]=route
 leg["day"]=7 if route==317 else 9
 leg["departureMinute"]=dep
 leg["arrivalMinute"]=dep+block
 leg["departure"]=clk(dep)
 leg["arrival"]=clk(dep+block)
 for assignment in s["bankAssignments"]:
  if assignment["legId"]!=leg["id"]:continue
  minute=dep if assignment["operation"]=="departure" else dep+block
  station=leg["origin"] if assignment["operation"]=="departure" else leg["destination"]
  options=[b for b in s["hubBanks"] if b["hub"]==station and b["startMinute"]<=minute<=b["endMinute"]]
  if len(options)==1:assignment["bankId"]=options[0]["id"]
for route in (317,319):
 matches=sorted((l for l in s["legs"] if l["route"]==route),key=lambda x:x["departureMinute"])
 for seq,leg in enumerate(matches,1):leg["sequenceWithinRoute"]=seq
'''
source=source.replace(pivot,inject+'\n'+pivot)
source=source.replace('schedule_7_v1_4_3_rebuild_candidate','schedule_7_v1_4_3_ah_exchange_candidate')
exec(compile(source,"scripts/v143_seven_route_rebuild_candidate.py","exec"),{"__name__":"__main__"})
