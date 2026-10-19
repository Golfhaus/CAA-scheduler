"""Read-only paired Syracuse mini-bank selective proposal with fewer lost connections."""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
root=ROOT/"outputs/schedule_7_v1_4_0_utilization"
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_0_draft/canonical_schedule.json").read_text())
pairs=json.loads((root/"syr_outbound_continuations.json").read_text())
extensions=json.loads((root/"syr_bank_continuations.json").read_text())
core={(110,"M15"),(124,"M15"),(167,"M15"),(106,"M17"),(130,"M17"),(131,"M17")}
banks=[
 {"id":"SYR-M15","hub":"SYR","startMinute":885,"endMinute":945},
 {"id":"SYR-M17","hub":"SYR","startMinute":1035,"endMinute":1095}]
plans=[
 ("selective_six",False,False),
 ("selective_seven_HVN",True,False),
 ("selective_six_plus_R160_extension",False,True)
]
results=[]
for name,addHVN,addR160 in plans:
 record={"name":name,"scope":"READ-ONLY selective Syracuse proposal"}
 try:
  selected=[x for x in pairs if x.get("pass") and ((x["route"],x["bank"]) in core or (addHVN and x["route"]==104 and x["bank"]=="M15"))]
  assert len(selected)==6+int(addHVN)
  ov={"schemaVersion":"1.0.0","id":"v140-syr-"+name,
  "baseSchedule":{"scheduleId":base["schedule"]["id"]},"schedule":base["schedule"],
  "hubBanksToAdd":banks,"hubBankCountOverrides":{"SYR":9},
  "retimeLegs":[],"bankAssignmentReplacements":[],"insertLegs":[],"bankAssignmentsToAdd":[]}
  for x in selected:
   part=x["overlay"]
   ov["retimeLegs"].extend(part["retimeLegs"])
   ov["bankAssignmentReplacements"].extend(part["bankAssignmentReplacements"])
  if addR160:
   x=next(y for y in extensions if y["name"]=="R160-BTV-SYR-PWM-PHF-PWM")
   assert x["pass"]
   part=x["overlay"]
   ov["retimeLegs"].extend(part["retimeLegs"])
   ov["bankAssignmentReplacements"].extend(part["bankAssignmentReplacements"])
   ov["insertLegs"].extend(part["insertLegs"])
   ov["bankAssignmentsToAdd"].extend(part["bankAssignmentsToAdd"])
  assert len({x["legId"] for x in ov["retimeLegs"]})==len(ov["retimeLegs"])
  assert len({(x["legId"],x["operation"]) for x in ov["bankAssignmentReplacements"]})==len(ov["bankAssignmentReplacements"])
  c=apply_optimization_overlay(base,ov)
  s=validate_schedule(c);n=validate_overnight_turns(c);o=validate_operating_rules(c)
  p=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
  try:export_gate_schedule(c);gate="pass"
  except Exception as e:gate=f"{type(e).__name__}: {str(e)[:430]}"
  record.update(paired=len(selected)+int(addR160),extraFlights=len(c["legs"])-len(base["legs"]),
   structure=s["status"],overnight=n["status"],planning=p["status"],gate=gate,operating=o["summary"],
   failed=[{"check":x["id"],"findings":x.get("findings",[])[:6]} for x in o["checks"] if x["status"]=="fail"])
  record["pass"]=s["status"]==n["status"]==p["status"]=="pass" and gate=="pass" and o["summary"]["effectiveErrorFindings"]==0
  if record["pass"]:
   record["overlay"]=ov
   (root/f"syr_selective_{name}_canonical.json").write_text(json.dumps(c)+"\n")
 except Exception as e:record.update(pass_=False,error=repr(e),trace=traceback.format_exc()[-700:])
 results.append(record)
(root/"syr_selective_native.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps([{"name":x["name"],"pass":x.get("pass",False),"pairs":x.get("paired"),
 "extraFlights":x.get("extraFlights"),"errors":x.get("operating",{}).get("effectiveErrorFindings"),
 "gate":x.get("gate"),"checks":[y["check"] for y in x.get("failed",[])],
 "error":x.get("error")} for x in results],indent=2))
