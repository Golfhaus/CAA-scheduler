"""Build every individually passing SYR mini-bank arrival+outbound candidate for O-D audits."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
out=ROOT/"outputs/schedule_7_v1_4_0_utilization"
base=json.loads((ROOT/"data/schedules/schedule_7_v1_4_0_draft/canonical_schedule.json").read_text())
samples=json.loads((out/"syr_outbound_continuations.json").read_text())
names=[]
for r in samples:
 if not r.get("pass"):continue
 name=f"R{r['route']}_{r['station']}_{r['bank']}"
 cand=apply_optimization_overlay(base,r["overlay"])
 assert len(cand["legs"])==1257
 (out/f"syr_single_paired_{name}.json").write_text(json.dumps(cand)+"\n")
 names.append({"name":name,"route":r["route"],"bank":r["bank"],"station":r["station"],"next":r["outboundDestination"]})
(out/"syr_single_paired_manifest.json").write_text(json.dumps(names,indent=2)+"\n")
print(json.dumps({"individualNativePassing":len(names),"names":[x["name"] for x in names]}))
