"""Manual-only experimental transfer of R319's SYR-PHF pair to AH day 10/R320.
Does not modify the accepted v1.4.3 draft; prints native validity of each scenario.
"""
import copy,json
from pathlib import Path
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule

base=json.loads(Path("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json").read_text())
def clock(n):return f"{n//60%24:02d}:{n%60:02d}"
def assign_bank(s,leg,operation):
    city=leg["origin"] if operation=="departure" else leg["destination"]
    minute=leg["departureMinute"] if operation=="departure" else leg["arrivalMinute"]
    choices=[b for b in s["hubBanks"] if b["hub"]==city and b["startMinute"]<=minute<=b["endMinute"]]
    s["bankAssignments"]=[a for a in s["bankAssignments"] if not(a["legId"]==leg["id"] and a["operation"]==operation)]
    if len(choices)==1:
        s["bankAssignments"].append({"legId":leg["id"],"operation":operation,"bankId":choices[0]["id"]})
for shift in (86,90,100,110,120):
    s=copy.deepcopy(base)
    for num,dep in ((1951,841),(1952,971),(1307,1010+shift),(1102,1160+shift)):
        leg=next(x for x in s["legs"] if x["flight"]==num)
        d=dep-leg["departureMinute"]
        leg["departureMinute"]=dep
        leg["arrivalMinute"]+=d
        leg["departure"]=clock(dep)
        leg["arrival"]=clock(leg["arrivalMinute"])
        if num in (1951,1952):
            leg["route"]=320
            leg["day"]=10
            leg["line"]="AH"
        for op in ("departure","arrival"):
            if any(a["legId"]==leg["id"] and a["operation"]==op for a in s["bankAssignments"]):
                assign_bank(s,leg,op)
    for route in (319,320):
        legs=sorted((l for l in s["legs"] if l["route"]==route),key=lambda x:x["departureMinute"])
        for i,l in enumerate(legs,1):l["sequenceWithinRoute"]=i
    structural=validate_schedule(s)
    overnight=validate_overnight_turns(s)
    operating=validate_operating_rules(s)
    try:
        export_gate_schedule(s)
        gate="pass"
    except Exception as exc:
        gate=str(exc)
    failures=[{"check":c["id"],"ids":[f["id"] for f in c["findings"] if "override" not in f][:5]}
              for c in operating["checks"] if c["status"]=="fail"]
    print(json.dumps({"shift":shift,"pair":"14:01 SYR-PHF 15:26 / 16:11 PHF-SYR 17:36",
                      "SYRCLTDeparture":clock(1010+shift),
                      "CLTBDLDeparture":clock(1160+shift),
                      "structural":structural["status"],"overnight":overnight["status"],
                      "gate":gate,"effectiveErrors":operating["summary"]["effectiveErrorFindings"],
                      "failures":failures}),flush=True)
