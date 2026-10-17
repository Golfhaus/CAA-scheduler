"""Candidate BHM mini-bank working schedules, four aircraft days exactly.

The experiment does not modify the canonical v1.3.3 draft. It reserves two
CRJ900 and two CRJ700 line-days, each a BHM→North→BHM→South→BHM→North→BHM
closed maintenance-base cycle. Every emitted schedule passes the *native*
checks or remains rejected evidence. The route-count guideline (9–12 line
days) is recorded as a warning for deliberately one-day trial rotations.
"""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.bank_placement import _block_minutes
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
base=json.loads((ROOT/"data/schedules/schedule_7_v1_3_3_draft/canonical_schedule.json").read_text())
rules=json.loads((ROOT/"config/policies/planning_rules_v7.json").read_text())
city={x["code"]:x for x in base["cities"]}
profiles={x["fleet"]:x for x in rules["frequencyAllocation"]["fleetProfiles"]}
out=ROOT/"outputs/schedule_7_v1_3_3_bhm_minibanks";out.mkdir(parents=True,exist_ok=True)
# BHM local is Central; all candidate endpoints are in Eastern Time.
def block(a,b,fleet):return _block_minutes(a,b,profiles[fleet],city)
def add(route,fleet,north,south,first,mid_south,return_south,even_north,north_turn=40):
 bN=block("BHM",north,fleet);bS=block("BHM",south,fleet)
 # Times here are absolute minutes in Central Time, local clock at origin/dest
 # is converted on construction.
 morning_back=first+2*bN+north_turn
 sout_arr=mid_south+bS
 sout_depart=return_south-bS
 if mid_south-morning_back<40 or sout_depart-sout_arr<40 or even_north-return_south<40:
  raise ValueError(f"turn short: {route} BHM morning {morning_back} south {sout_arr, sout_depart} back {return_south} north {even_north}")
 last_arr=even_north+2*bN+40
 if last_arr>1410:raise ValueError(f"terminator beyond 23:30 CT {route}: {last_arr}")
 stages=[("BHM",north,first,first+bN), (north,"BHM",first+bN+north_turn,morning_back),
         ("BHM",south,mid_south,sout_arr),(south,"BHM",sout_depart,return_south),
         ("BHM",north,even_north,even_north+bN),(north,"BHM",even_north+bN+40,last_arr)]
 rows=[]
 for j,(orig,dest,depct,arrct) in enumerate(stages,1):
  od=60 if city[orig]["timezone"]=="Eastern" else 0
  ad=60 if city[dest]["timezone"]=="Eastern" else 0
  dep=depct+od;arr=arrct+ad
  if not (270<=dep<=1260 if orig!="BHM" else 270<=dep<=1410):raise ValueError(f"curfew {route} {orig} dep {dep}")
  rows.append({"id":f"V133-BHM-{route}-{j}-{orig}-{dest}","origin":orig,"destination":dest,"departureMinute":dep,"arrivalMinute":arr})
 return {"route":route,"line":{801:"BA",802:"BB",803:"BC",804:"BD"}[route],"day":1,"fleet":fleet,"legs":rows}
# The last southern market PGD was chosen because CAK→PGD has no reasonable
# existing one-stop, and its four-northern-city demand exceeds DAB/EYW/MLB.
def make(name,shift=0,pattern=0):
 fleet_by={801:"CRJ900",802:"CRJ900",803:"CRJ700",804:"CRJ700"}
 ns={801:"ALB",802:"CAK",803:"ISP",804:"HVN"}
 ss={801:"SRQ",802:"PGD",803:"MYR",804:"CHS"}
 # North arrivals at BHM cluster near 10:00 CT for 10:50–11:00 departures south.
 targets={801:606,802:606,803:610,804:611}
 # Afternoon split reflects only two available gates between 15:00 and 16:00.
 sc={801:888,802:890,803:950,804:952}
 nc={801:928,802:930,803:990,804:992}
 if pattern==1: # flip southerners within each fleet for gate-demand experiment
  ss[801],ss[802]=ss[802],ss[801]
  ss[803],ss[804]=ss[804],ss[803]
 if pattern==2: # evening BHM bank stagger refinement
  sc[801]-=10;sc[802]-=10;nc[801]-=10;nc[802]-=10
 if pattern==3:
  sc[803]-=10;sc[804]-=10;nc[803]-=10;nc[804]-=10
 result={"schemaVersion":"1.0.0","id":"schedule-7-v1.3.3-bhm-mini-bank-"+name,
  "baseSchedule":{"scheduleId":base["schedule"]["id"]},
  "schedule":{**base["schedule"]},"addRoutes":[]}
 for k in (801,802,803,804):
  fleet=fleet_by[k];n=ns[k]
  start=targets[k]-(2*block("BHM",n,fleet)+40)
  result["addRoutes"].append(add(k,fleet,n,ss[k],start,650+2*(k-801)+shift,sc[k]+shift,nc[k]+shift))
 return result
results={}
for name,shift,pattern in [("base",0,0),("early",-10,0),("late",10,0),
                            ("flipped",0,1),("south_early",0,2),("south_late",0,3)]:
 try:
  overlay=make(name,shift,pattern)
  c=apply_optimization_overlay(base,overlay)
  s=validate_schedule(c);v=validate_operating_rules(c);n=validate_overnight_turns(c)
  p=validate_planning_snapshot(reconstruct_planning_snapshot(c),c)
  try:g=export_gate_schedule(c);gate="pass"
  except Exception as e:gate=repr(e);g=None
  error=v["summary"]["effectiveErrorFindings"]
  passes=s["status"]==n["status"]==p["status"]=="pass" and error==0 and gate=="pass"
  stands=[x for cityx in g["cities"] for x in cityx["claims"] if x["rowType"]=="stand"] if g else []
  results[name]={"pass":passes,"structural":s["status"],"overnight":n["status"],"planning":p["status"],
    "gate":gate,"operatingSummary":v["summary"],"fleet":next(x for x in v["checks"] if x["id"]=="fleet_capacity")["metrics"],
    "failed":[{"id":x["id"],"count":len(x["findings"]),"examples":x["findings"][:5]} for x in v["checks"] if x["status"]=="fail"],
    "warningLineCount":next(x for x in v["checks"] if x["id"]=="line_route_count")["findings"],
    "routes":overlay["addRoutes"],"standClaims":len(stands)}
  if passes:
   (out/(name+"_overlay.json")).write_text(json.dumps(overlay,indent=2)+"\n")
   (out/(name+"_canonical.json")).write_text(json.dumps(c,indent=2)+"\n")
  print(name,"PASS"if passes else"FAIL","errors",error,"gate",gate,"failed",[(x["id"],x["count"])for x in results[name]["failed"]],flush=True)
 except Exception as e:
  results[name]={"pass":False,"exception":repr(e),"traceback":traceback.format_exc()[-1800:]}
  print(name,"ERROR",repr(e),flush=True)
 (out/"physical_screen.json").write_text(json.dumps(results,indent=2)+"\n")
