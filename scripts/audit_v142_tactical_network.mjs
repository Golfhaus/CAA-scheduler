import {readFileSync,writeFileSync,mkdirSync} from "node:fs";
import {buildItineraries} from "../web/app.mjs";
import {parseAirportDemand,buildServiceAnalysis,compareServiceAnalyses,coverageView} from "../web/opportunity-analysis.mjs";
const base=JSON.parse(readFileSync("data/schedules/schedule_7_v1_4_1/canonical_schedule.json"));
const draft=JSON.parse(readFileSync("data/schedules/schedule_7_v1_4_2_draft/canonical_schedule.json"));
const demand=parseAirportDemand(readFileSync("data/reference/airport_od_matrix_consolidated_v2.csv","utf8"));
const before=buildServiceAnalysis(base,demand,buildItineraries);
const after=buildServiceAnalysis(draft,demand,buildItineraries);
const comparison=compareServiceAnalyses(before,after,true);
const targets=["BLV-HOU","HOU-BLV","OMA-BNA","BNA-OMA","HVN-RDU","RDU-HVN","BNA-ECP","ECP-BNA","GRR-SRQ","SRQ-GRR"];
const markets=Object.fromEntries(targets.map(x=>{
 const b=before.records.get(x),a=after.records.get(x);
 return [x,{demand:b.demand,before:coverageView(b,true),after:coverageView(a,true)}];
}));
const result={counts:Object.fromEntries(["gained","lost","faster","slower"].map(k=>[k,comparison[k].length])),gained:comparison.gained,lost:comparison.lost,slowestHighDemand:comparison.slower.slice(0,25),markets};
mkdirSync("outputs/schedule_7_v1_4_2",{recursive:true});
writeFileSync("outputs/schedule_7_v1_4_2/tactical_network.json",JSON.stringify(result,null,2)+"\n");
console.log(JSON.stringify({counts:result.counts,gained:result.gained,lost:result.lost,markets:Object.fromEntries(Object.entries(markets).map(([k,v])=>[k,{demand:v.demand,beforeReasonableOneStops:v.before.stops,afterReasonableOneStops:v.after.stops}]))},null,2));
