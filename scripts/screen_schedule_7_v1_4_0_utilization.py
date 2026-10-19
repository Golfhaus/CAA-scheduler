"""Read-only native v1.4.0 utilization experiments against released v1.3.3.

No schedules are published or amended. Reports candidate validation and
commercial/physical findings for four short CRJ200 routes.
"""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
BASE=json.loads((ROOT/"data/schedules/schedule_7_v1_3_3/canonical_schedule.json").read_text())
assert BASE["schedule"]["id"]=="schedule_7_v1_3_3"
# Changed leg minutes must preserve origin/destination and block duration.
# Extra pair is inserted at SYR in the reclaimed hub gap.
plans=[
 {"route":160,"market":"PVD","returns":[(1829,772,824)],"add":[("SYR","PVD",865,928),("PVD","SYR",968,1031)]},
 {"route":160,"market":"PHF","returns":[(1829,772,824)],"add":[("SYR","PHF",865,950),("PHF","SYR",990,1075)]},
 {"route":160,"market":"ROC","returns":[(1829,772,824)],"add":[("SYR","ROC",865,904),("ROC","SYR",944,983)]},
 {"route":106,"market":"ROC","returns":[(1854,609,663),(1853,865,919),(1856,959,1013)],"add":[("SYR","ROC",703,742),("ROC","SYR",782,821)]},
 {"route":106,"market":"ALB","returns":[(1854,609,663),(1853,865,919),(1856,959,1013)],"add":[("SYR","ALB",703,747),("ALB","SYR",787,831)]},
 {"route":107,"market":"ROC","returns":[(1893,613,671),(1792,875,929),(1791,969,1023)],"add":[("SYR","ROC",711,750),("ROC","SYR",790,829)]},
 {"route":107,"market":"ALB","returns":[(1893,613,671),(1792,875,929),(1791,969,1023)],"add":[("SYR","ALB",711,755),("ALB","SYR",795,839)]},
 {"route":110,"market":"ROC","returns":[(1879,446,502),(1836,710,770),(1840,810,870)],"add":[("SYR","ROC",542,581),("ROC","SYR",621,660)]},
 {"route":110,"market":"ALB","returns":[(1879,446,502),(1836,710,770),(1840,810,870)],"add":[("SYR","ALB",542,586),("ALB","SYR",626,670)]}
]
byflight={int(x["flight"]):x for x in BASE["legs"]}
results=[]
for plan in plans:
    n=plan["route"];market=plan["market"]
    record={"route":n,"market":market,"experiment":"retime held return(s) and add SYR round trip","status":"unreviewed"}
    try:
        legs=[l for l in BASE["legs"] if l["route"]==n]
        assert len({l["fleet"] for l in legs})==1 and legs[0]["fleet"]=="CRJ200"
        overlay={"id":f"v140-{n}-{market}-hold-screen","baseSchedule":{"scheduleId":BASE["schedule"]["id"]},
          "schedule":BASE["schedule"],"retimeLegs":[],"insertLegs":[]}
        for flight,dep,arr in plan["returns"]:
            leg=byflight[flight]
            assert leg["route"]==n
            assert (leg["arrivalMinute"]-leg["departureMinute"])%1440==(arr-dep)%1440, (flight,leg["departureMinute"],leg["arrivalMinute"],dep,arr)
            overlay["retimeLegs"].append({"legId":leg["id"],"expectedDepartureMinute":leg["departureMinute"],"expectedArrivalMinute":leg["arrivalMinute"],"departureMinute":dep,"arrivalMinute":arr})
        for i,(a,b,dep,arr) in enumerate(plan["add"],1):
            overlay["insertLegs"].append({"id":f"V140-R{n}-{market}-{i}-{a}-{b}","route":n,"origin":a,"destination":b,"departureMinute":dep,"arrivalMinute":arr})
        c=apply_optimization_overlay(BASE,overlay)
        route=sorted((l for l in c["legs"] if l["route"]==n),key=lambda l:l["sequenceWithinRoute"])
        record["flights"]= [{"flight":l["flight"],"dep":l["departure"],"from":l["origin"],"to":l["destination"],"arr":l["arrival"]} for l in route]
        record["newFlightCount"]=len(c["legs"])-len(BASE["legs"])
        s=validate_schedule(c)
        o=validate_operating_rules(c)
        overnight=validate_overnight_turns(c)
        planning=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
        try:export_gate_schedule(c);gate="pass"
        except Exception as e:gate=f"{type(e).__name__}: {str(e)[:500]}"
        record.update(structure=s["status"],overnight=overnight["status"],planning=planning["status"],
          gate=gate,operating=o["summary"],failed=[{"check":x["id"],"findings":x.get("findings",[])[:8]} for x in o["checks"] if x["status"]=="fail"])
        record["pass"]=s["status"]==overnight["status"]==planning["status"]=="pass" and gate=="pass" and o["summary"]["effectiveErrorFindings"]==0
        record["status"]="pass" if record["pass"] else "fail"
        record["retimes"]=overlay["retimeLegs"]
        record["inserts"]=overlay["insertLegs"]
    except Exception as e:
        record.update(status="exception",exception=repr(e),trace=traceback.format_exc()[-900:])
    results.append(record)
out=ROOT/"outputs/schedule_7_v1_4_0_utilization"
out.mkdir(parents=True,exist_ok=True)
(out/"initial_feasibility.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps([{"route":r["route"],"market":r["market"],"status":r["status"],"gate":r.get("gate"),"operatingErrors":r.get("operating",{}).get("effectiveErrorFindings"),"failedChecks":[f["check"] for f in r.get("failed",[])],"error":r.get("exception")} for r in results],indent=2))
