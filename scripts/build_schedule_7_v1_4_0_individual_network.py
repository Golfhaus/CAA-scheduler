"""Generate read-only individual P2P/A-B network candidates from native-passed overlays."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_0_draft/canonical_schedule.json").read_text())
def load(filename):
 return json.loads((ROOT/"outputs/schedule_7_v1_4_0_utilization"/filename).read_text())
tactical=load("tactical_p2p_screen.json")
initial=load("p2p_ab_triangle_screen.json")
choices=[
 ("R160_BTV_PHF",next(x for x in tactical if x["name"].startswith("BTV-PHF"))),
 ("R160_BTV_PWM",next(x for x in initial if x["route"]==160 and x["market"]=="BTV-PWM-SYR")),
 ("R107_BDL_BUF",next(x for x in tactical if x["name"].startswith("BDL-BUF"))),
 ("R107_BDL_ROC",next(x for x in tactical if x["name"].startswith("BDL-ROC"))),
 ("R107_BDL_PVD",next(x for x in initial if x["route"]==107 and x["market"]=="BDL-PVD-SYR")),
]
out=ROOT/"outputs/schedule_7_v1_4_0_utilization"
for name,item in choices:
 assert item["pass"] is True
 overlay=item.get("changes") or item.get("overlay")
 c=apply_optimization_overlay(base,overlay)
 assert len(c["legs"])==1258 and c["schedule"]["id"]=="schedule_7_v1_4_0_draft"
 (out/f"net_{name}.json").write_text(json.dumps(c)+"\n")
print(json.dumps({"separateNetworkCandidates":[x[0] for x in choices],"baselineFlights":len(base["legs"])},indent=2))
