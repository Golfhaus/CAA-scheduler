"""Check R345 CLT long-hold extension using demand, real block times and fixed gates."""
import json,copy,math
from pathlib import Path
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.validation import validate_schedule
from caa_scheduler.gate_export import export_gate_schedule
s0=json.loads(Path("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json").read_text())
lines=Path("data/reference/airport_od_matrix_consolidated_v2.csv").read_text().splitlines()
h=next(i for i,x in enumerate(lines) if x.startswith("Origin \\ Dest"))
codes=lines[h].split(",")[1:];od={}
for row in lines[h+1:]:
 v=row.split(",")
 if len(v)==len(codes)+1:od[v[0]]={c:float(v[i+1] or 0) for i,c in enumerate(codes)}
city={c["code"]:c for c in s0["cities"] if c["active"]}
def block(a,b):
 available=[l for l in s0["legs"] if l["origin"]==a and l["destination"]==b]
 if available:
  return min((x["arrivalMinute"]-x["departureMinute"]-(int(city[b]["timezone"]=="Central")-int(city[a]["timezone"]=="Central"))*(-60))%1440 for x in available)
 x,y=city[a],city[b];p=math.pi/180;h=math.sin((y["latitude"]-x["latitude"])*p/2)**2+math.cos(x["latitude"]*p)*math.cos(y["latitude"]*p)*math.sin((y["longitude"]-x["longitude"])*p/2)**2
 return round((32+3440*2*math.asin(min(1,math.sqrt(h)))*60/400)/5)*5
def clk(m):return f"{m//60%24:02d}:{m%60:02d}"
for dst in ("AVL","CAE","GSO","GSP","ROA","TRI","TYS","FAY","CLT","CHS"):
 if dst=="CLT":continue
 length=block("CLT",dst);back=block(dst,"CLT")
 demand=round(od["CLT"].get(dst,0)+od[dst].get("CLT",0),1)
 print("CANDIDATE",dst,"block",length,back,"OD",demand,flush=True)
 for dep in (827,840,850,865):
  arr=dep+length;ret=arr+40;end=ret+back
  if end>990:continue
  s=copy.deepcopy(s0);ls=[l for l in s["legs"] if l["route"]==345]
  for i,(a,b,d,t) in enumerate([("CLT",dst,dep,arr),(dst,"CLT",ret,end)]):
   q={"id":f"V143-R345-{dst}-{i}","route":345,"line":"AS","day":6,"fleet":"CRJ700","sequenceWithinRoute":0,"pairing":4000+i,"flight":4000+i,"origin":a,"destination":b,"departureMinute":d,"arrivalMinute":t,"departure":clk(d),"arrival":clk(t)}
   s["legs"].append(q)
  for i,l in enumerate(sorted((l for l in s["legs"] if l["route"]==345),key=lambda x:x["departureMinute"]),1):l["sequenceWithinRoute"]=i
  v=validate_operating_rules(s)
  try:export_gate_schedule(s);gate=True
  except Exception:gate=False
  if gate and v["summary"]["effectiveErrorFindings"]==0 and validate_schedule(s)["status"]=="pass" and validate_overnight_turns(s)["status"]=="pass":
   print(json.dumps({"dst":dst,"depart":clk(dep),"return":clk(end),"flying":length+back,"roundOD":demand,"status":"NATIVE_PASS"}),flush=True)
