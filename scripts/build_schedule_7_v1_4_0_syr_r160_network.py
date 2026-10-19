"""Build read-only native-passed R160 Syracuse mini-bank extension for network audit."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
folder=ROOT/"outputs/schedule_7_v1_4_0_utilization"
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_0_draft/canonical_schedule.json").read_text())
records=json.loads((folder/"syr_bank_continuations.json").read_text())
r=next(x for x in records if x["name"]=="R160-BTV-SYR-PWM-PHF-PWM")
assert r["pass"] is True
candidate=apply_optimization_overlay(base,r["overlay"])
assert len(candidate["legs"])==1259
(folder/"syr_r160_extended_network_candidate.json").write_text(json.dumps(candidate)+"\n")
print(json.dumps({"route":160,"flights":len(candidate["legs"]),"new":len(candidate["legs"])-len(base["legs"]),"status":"read only"}))
