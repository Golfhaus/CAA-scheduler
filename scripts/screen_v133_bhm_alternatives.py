"""Native feasibility screen for remaining R357/R358 alternatives. Read-only."""
from pathlib import Path
import json,sys,copy,traceback
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule

base=json.loads((ROOT/"data/schedules/schedule_7_v1_3_3_draft/canonical_schedule.json").read_text())
assert len(base["legs"])==1253
assert len({l["line"] for l in base["legs"]})==19
assert {(l["route"],l["line"],l["day"]) for l in base["legs"] if l["route"] in (529,530)}=={(529,"AG",11),(530,"AG",9)}
# All times are local minutes, following canonical schema.
cases=[
 {"route":357,"host":"AH","day":4,"airport":"PHF","first":[366,426],"last":[1245,1305],"label":"PHF AH day4"},
 {"route":357,"host":"AK","day":10,"airport":"RDU","first":[336,426],"last":[1245,1335],"label":"RDU AK day10"},
 {"route":357,"host":"AL","day":12,"airport":"PHF","first":[366,426],"last":[1245,1305],"label":"PHF AL day12"},
 {"route":358,"host":"AA","day":8,"airport":"CHS","first":[365,467],"last":[1217,1319],"label":"CHS AA day8"},
 {"route":358,"host":"AK","day":11,"airport":"PHF","first":[392,467],"last":[1217,1292],"label":"PHF AK day11"},
 {"route":358,"host":"AH","day":4,"airport":"PHF","first":[392,467],"last":[1217,1292],"label":"PHF AH day4"}
]
def clock(n):return f"{(n//60)%24:02}:{n%60:02}"
def candidate_for(x,original):
    schedule=copy.deepcopy(original)
    host,day,route=x["host"],x["day"],x["route"]
    lines=sorted({(l["day"],l["route"]) for l in schedule["legs"] if l["line"]==host})
    assert len(lines)==max(y[0] for y in lines)
    assert 1<=day<=len(lines)+1
    for l in schedule["legs"]:
        if l["line"]==host and l["day"]>=day:l["day"]+=1
    routelegs=sorted((l for l in schedule["legs"] if l["route"]==route),key=lambda l:l["sequenceWithinRoute"])
    assert len(routelegs)==6
    first,last=routelegs[0],routelegs[-1]
    old_ids={first["id"],last["id"]}
    first["origin"]=x["airport"];last["destination"]=x["airport"]
    first["departureMinute"],first["arrivalMinute"]=x["first"]
    last["departureMinute"],last["arrivalMinute"]=x["last"]
    for leg in (first,last):
        leg["departure"]=clock(leg["departureMinute"]);leg["arrival"]=clock(leg["arrivalMinute"])
    first["id"]=f"V133-BHM-{route}-1-{first['origin']}-{first['destination']}"
    last["id"]=f"V133-BHM-{route}-6-{last['origin']}-{last['destination']}"
    directed={(l["origin"],l["destination"]):l["pairing"] for l in schedule["legs"] if l["route"]!=route}
    number=max(l["pairing"] for l in schedule["legs"])+1
    for leg in (first,last):
        market=(leg["origin"],leg["destination"])
        if market not in directed:directed[market]=number;number+=1
        leg["pairing"]=directed[market]
    for leg in routelegs:
        leg["line"]=host;leg["day"]=day
    schedule["bankAssignments"]=[a for a in schedule["bankAssignments"] if a["legId"] not in old_ids]
    return schedule

results=[]
for case in cases:
    r={k:v for k,v in case.items()}
    try:
        c=candidate_for(case,base)
        r["lineDays"]=max(l["day"] for l in c["legs"] if l["line"]==case["host"])
        if r["lineDays"]>13:raise ValueError("Over 13-day line maximum")
        s=validate_schedule(c)
        n=validate_overnight_turns(c)
        o=validate_operating_rules(c)
        p=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
        try:export_gate_schedule(c);gate="pass"
        except Exception as e:gate=f"{type(e).__name__}: {str(e)[:300]}"
        r.update(structure=s["status"],overnight=n["status"],planning=p["status"],
                 effectiveErrors=o["summary"]["effectiveErrorFindings"],
                 operatingFailedChecks=[{"id":v["id"],"findings":v.get("findings",[])[:5]} for v in o["checks"] if v["status"]=="fail"],
                 gate=gate)
        r["pass"]=s["status"]==n["status"]==p["status"]=="pass" and o["summary"]["effectiveErrorFindings"]==0 and gate=="pass"
        r["totalLines"]=len({l["line"] for l in c["legs"]})
        r["totalFlights"]=len(c["legs"])
    except Exception as e:r.update(pass_=False,error=repr(e),trace=traceback.format_exc()[-600:])
    results.append(r)
out=ROOT/"outputs/schedule_7_v1_3_3_bhm_line_insertion"
out.mkdir(parents=True,exist_ok=True)
(out/"remaining_two_alternatives.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps([{"label":r["label"],"pass":r.get("pass",False),"errors":r.get("effectiveErrors"),"gate":r.get("gate"),"checks":[f["id"] for f in r.get("operatingFailedChecks",[])]} for r in results],indent=2))
