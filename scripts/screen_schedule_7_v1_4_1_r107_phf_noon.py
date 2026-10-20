"""Native test of R107 ISP-PHF-SYR noon PHF mini-bank with a nine-minute BDL offset."""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_1_draft/canonical_schedule.json").read_text())
assert len(base["legs"])==1263
byflight={l["flight"]:l for l in base["legs"]}
old=byflight[1893];bdl=byflight[1792]
assert old["route"]==bdl["route"]==107
bank={"id":"PHF-M12-V141","hub":"PHF","startMinute":715,"endMinute":775}
options=[
 {"label":"ISP-PHF-SYR with 09min BDL adjustment","ispBlock":77,"phfBlock":84,"phfDepart":730,"bdlDepart":854},
 {"label":"ISP-PHF-SYR with 08min BDL adjustment","ispBlock":76,"phfBlock":84,"phfDepart":729,"bdlDepart":853}
]
results=[]
for i,opt in enumerate(options):
 r={"label":opt["label"],"scope":"read-only candidate"}
 try:
  ispDep=old["departureMinute"]-132 # 10:13
  ispArr=ispDep+opt["ispBlock"]
  phfDep=opt["phfDepart"];syrArr=phfDep+opt["phfBlock"]
  assert ispArr+40<=phfDep
  assert syrArr+40<=opt["bdlDepart"]<855
  newBdlArr=bdl["arrivalMinute"]+opt["bdlDepart"]-bdl["departureMinute"]
  ov={"schemaVersion":"1.0.0","id":f"v141-r107-phf-noon-{i}",
   "baseSchedule":{"scheduleId":base["schedule"]["id"]},"schedule":base["schedule"],
   "removeLegs":[{"legId":old["id"],"expectedRoute":107}],
   "retimeLegs":[{"legId":bdl["id"],"expectedDepartureMinute":bdl["departureMinute"],
    "expectedArrivalMinute":bdl["arrivalMinute"],"departureMinute":opt["bdlDepart"],"arrivalMinute":newBdlArr}],
   "insertLegs":[{"id":f"V141-R107-ISP-PHF-{i}","route":107,"origin":"ISP","destination":"PHF",
     "departureMinute":ispDep,"arrivalMinute":ispArr},
    {"id":f"V141-R107-PHF-SYR-{i}","route":107,"origin":"PHF","destination":"SYR",
     "departureMinute":phfDep,"arrivalMinute":syrArr}],
   "bankAssignmentsToAdd":[{"legId":f"V141-R107-ISP-PHF-{i}","operation":"arrival","bankId":"PHF-B3"},
    {"legId":f"V141-R107-PHF-SYR-{i}","operation":"departure","bankId":bank["id"]},
    {"legId":f"V141-R107-PHF-SYR-{i}","operation":"arrival","bankId":"SYR-B4"}],
   "hubBanksToAdd":[bank],"hubBankCountOverrides":{"PHF":base["operatingPolicy"]["hubBankCounts"]["PHF"]+1}}
  c=apply_optimization_overlay(base,ov)
  s=validate_schedule(c);n=validate_overnight_turns(c)
  o=validate_operating_rules(c);p=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
  try:export_gate_schedule(c);gate="pass"
  except Exception as e:gate=f"{type(e).__name__}: {str(e)[:430]}"
  r.update(structural=s["status"],overnight=n["status"],planning=p["status"],gate=gate,
   operating=o["summary"],failed=[{"check":x["id"],"findings":x.get("findings",[])[:5]} for x in o["checks"] if x["status"]=="fail"])
  r["pass"]=s["status"]==n["status"]==p["status"]=="pass" and gate=="pass" and o["summary"]["effectiveErrorFindings"]==0
  r["overlay"]=ov
  if r["pass"]:(ROOT/"outputs/schedule_7_v1_4_1_utilization"/f"r107_phf_noon_{i}_canonical.json").write_text(json.dumps(c)+"\n")
 except Exception as e:r.update(pass_=False,error=repr(e),trace=traceback.format_exc()[-600:])
 results.append(r)
out=ROOT/"outputs/schedule_7_v1_4_1_utilization";out.mkdir(parents=True,exist_ok=True)
(out/"r107_phf_noon_screen.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps([{"label":x["label"],"pass":x.get("pass",False),"gate":x.get("gate"),
"errors":x.get("operating",{}).get("effectiveErrorFindings"),"failed":[y["check"] for y in x.get("failed",[])],
"error":x.get("error")} for x in results],indent=2))
