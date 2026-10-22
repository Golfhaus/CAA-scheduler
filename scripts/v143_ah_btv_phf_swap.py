"""Targeted AH line day-8/day-9 genuine pair exchange (manual research only).
Swap SYR-BTV-SYR R318 and SYR-PHF-SYR R319, preserving AH line endpoints.
Do not modify accepted draft or use an automated push/PR trigger.
"""
import copy,json
from pathlib import Path
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
s0=json.loads(Path("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json").read_text())
def clock(t):return f"{t//60%24:02d}:{t%60:02d}"
for phf_start in (380,390,400):
 for phf_return_departure in (510,525,540):
  for btv_start in (750,795):
   phf_arrive=phf_start+85
   phf_return_arrive=phf_return_departure+85
   if phf_return_departure-phf_arrive<40 or 680-phf_return_arrive<40:continue
   btv_arrive=btv_start+52
   btv_return_departure=btv_arrive+45
   btv_return_arrive=btv_return_departure+52
   if 1135-btv_return_arrive<40:continue
   s=copy.deepcopy(s0)
   changes=((1951,318,8,phf_start,85),(1952,318,8,phf_return_departure,85),
            (2189,319,9,btv_start,52),(2190,319,9,btv_return_departure,52))
   for no,route,day,dep,block in changes:
    l=next(x for x in s["legs"] if x["flight"]==no)
    l["route"]=route;l["day"]=day;l["departureMinute"]=dep;l["arrivalMinute"]=dep+block
    l["departure"]=clock(dep);l["arrival"]=clock(dep+block)
    for a in s["bankAssignments"]:
     if a["legId"]!=l["id"]:continue
     airport=l["origin"] if a["operation"]=="departure" else l["destination"]
     moment=l["departureMinute"] if a["operation"]=="departure" else l["arrivalMinute"]
     options=[b for b in s["hubBanks"] if b["hub"]==airport and b["startMinute"]<=moment<=b["endMinute"]]
     if len(options)==1:a["bankId"]=options[0]["id"]
   for rt in (318,319):
    for seq,l in enumerate(sorted((x for x in s["legs"] if x["route"]==rt),key=lambda x:x["departureMinute"]),1):l["sequenceWithinRoute"]=seq
   op=validate_operating_rules(s)
   try: export_gate_schedule(s);gate="pass"
   except Exception as e:gate=str(e)
   structural=validate_schedule(s)["status"]
   overnight=validate_overnight_turns(s)["status"]
   report={"phfStart":clock(phf_start),"phfReturn":clock(phf_return_arrive),"btvStart":clock(btv_start),"btvReturn":clock(btv_return_arrive),"structure":structural,"overnight":overnight,"gates":gate,"effectiveErrors":op["summary"]["effectiveErrorFindings"],"failed":[{"id":c["id"],"sample":[f["id"] for f in c["findings"] if "override" not in f][:5]} for c in op["checks"] if c["status"]=="fail"]}
   print(json.dumps(report),flush=True)
   if structural=="pass" and overnight=="pass" and gate=="pass" and report["effectiveErrors"]==0:
    out=Path("data/schedules/schedule_7_v1_4_3_ah_btv_phf_swap_candidate")
    out.mkdir(parents=True,exist_ok=True)
    (out/"canonical_schedule.json").write_text(json.dumps(s,indent=2)+"\n")
    print("AH_BTV_PHF_SWAP_NATIVE_PASS",flush=True)
    raise SystemExit(0)
raise SystemExit("No fully valid AH BTV/PHF reassignment among screened timings")
