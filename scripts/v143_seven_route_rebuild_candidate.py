"""Seven-route reconstruction staging candidate.
Preserve original 1,286 draft; replace only tested flight/aircraft allocations.
Changes are deliberately additive and isolated for hard-stop screening.
"""
import json,copy,sys
from pathlib import Path
sys.path.insert(0,"src")
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
baseline=Path("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json")
s=json.loads(baseline.read_text())
def clk(t):return f"{t//60%24:02d}:{t%60:02d}"
def retime(n,dep,bank=None):
 l=next(x for x in s["legs"] if x["flight"]==n)
 d=dep-l["departureMinute"]
 l["departureMinute"]=dep;l["arrivalMinute"]+=d
 l["departure"]=clk(dep);l["arrival"]=clk(l["arrivalMinute"])
 if bank:
  for x in s["bankAssignments"]:
   if x["legId"]==l["id"] and x["operation"]=="arrival":x["bankId"]=bank
def add(route,segments):
 template=next(l for l in s["legs"] if l["route"]==route)
 newpair=max(x["pairing"] for x in s["legs"])+1
 newflight=max(x["flight"] for x in s["legs"])+1
 for i,(origin,destination,dep,arr) in enumerate(segments):
  l={**template,"id":f"V143-REBUILD-R{route}-{i}-{origin}-{destination}","flight":newflight+i,"pairing":newpair+i,"sequenceWithinRoute":0,"origin":origin,"destination":destination,"departureMinute":dep,"arrivalMinute":arr,"departure":clk(dep),"arrival":clk(arr)}
  s["legs"].append(l)
  for city,operation,minute in ((origin,"departure",dep),(destination,"arrival",arr)):
   if city not in s["operatingPolicy"]["hubs"]:continue
   options=[b for b in s["hubBanks"] if b["hub"]==city and b["startMinute"]<=minute<=b["endMinute"]]
   if len(options)==1:s["bankAssignments"].append(dict(legId=l["id"],operation=operation,bankId=options[0]["id"]))
 for seq,l in enumerate(sorted([l for l in s["legs"] if l["route"]==route],key=lambda x:x["departureMinute"]),1):l["sequenceWithinRoute"]=seq
# 313: release CLT stand for CLT-JAX, preserving original CLT/PHF downstream.
retime(1379,650,"PHF-M12-V141")
add(313,[("CLT","JAX",422,493),("JAX","CLT",533,604)])
# 338: use PHF stand for PHF-RDU round trip while preserving evening SAV-JAX.
retime(1493,1020)
# Move this PHF departure from the former B5 bank to M5 at 17:00.
sav=next(l for l in s['legs'] if l['flight']==1493)
for assignment in s['bankAssignments']:
 if assignment['legId']==sav['id'] and assignment['operation']=='departure':
  assignment['bankId']='PHF-M5'
add(338,[("PHF","RDU",833,883),("RDU","PHF",923,973)])
# 303,316,319,339,345: original schedules preserved for follow-up line reconstruction.
s["schedule"].update(id="schedule_7_v1_4_3_rebuild_candidate",version="1.4.3-rebuild-draft",label="Schedule 7 v1.4.3 seven-route rebuild candidate",status="draft")
checks={"structural":validate_schedule(s),"overnight":validate_overnight_turns(s),"operating":validate_operating_rules(s)}
try:gates=export_gate_schedule(s);gate="pass"
except Exception as e:gates=None;gate=str(e)
report={"legs":len(s["legs"]),"routes":len({l["route"] for l in s["legs"]}),"structure":checks["structural"]["status"],"overnight":checks["overnight"]["status"],"gate":gate,"errors":checks["operating"]["summary"]["effectiveErrorFindings"],"failures":[{"id":c["id"],"findings":[f["id"] for f in c["findings"] if "override" not in f][:8]} for c in checks["operating"]["checks"] if c["status"]=="fail"]}
print(json.dumps(report,indent=2),flush=True)
if report["structure"]=="pass" and report["overnight"]=="pass" and report["gate"]=="pass" and report["errors"]==0:
 p=reconstruct_planning_snapshot(s,demand_data_version="bts-db1c-6mo-jul2025-apr2026-v7")
 pv=validate_planning_snapshot(p,s)
 print("PLANNING",pv["status"],flush=True)
 if pv["status"]=="pass":
  out=Path("data/schedules/schedule_7_v1_4_3_rebuild_candidate");out.mkdir(parents=True,exist_ok=True)
  for file,data in {"canonical_schedule.json":s,"validation_report.json":checks["structural"],"operating_validation_report.json":checks["operating"],"overnight_turn_validation.json":checks["overnight"],"planning_validation_report.json":pv,"planning_snapshot.json":p,"gates.json":gates}.items():
   (out/file).write_text(json.dumps(data,indent=2)+"\n")
  print("STAGED_REBUILD_NATIVE_PASS",flush=True)
