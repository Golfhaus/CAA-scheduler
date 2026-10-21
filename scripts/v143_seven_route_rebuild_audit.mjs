import {readFileSync} from "node:fs";
import {buildItineraries} from "../web/app.mjs";
import {parseAirportDemand,buildServiceAnalysis,compareServiceAnalyses} from "../web/opportunity-analysis.mjs";
const base=JSON.parse(readFileSync("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json"));
const candidate=JSON.parse(readFileSync("data/schedules/schedule_7_v1_4_3_rebuild_candidate/canonical_schedule.json"));
const od=parseAirportDemand(readFileSync("data/reference/airport_od_matrix_consolidated_v2.csv","utf8"));
const b=buildServiceAnalysis(base,od,buildItineraries),c=buildServiceAnalysis(candidate,od,buildItineraries);
const rows=arr=>arr.filter(x=>(x.demand||0)>8).sort((a,b)=>(b.demand||0)-(a.demand||0)).slice(0,20).map(x=>({market:x.market,demand:x.demand,before:x.beforeMinutes,after:x.afterMinutes}));
for(const reasonable of [true,false]){const r=compareServiceAnalyses(b,c,reasonable);console.log(JSON.stringify({reasonable,gained:r.gained.length,lost:r.lost.length,faster:r.faster.length,slower:r.slower.length,highDemandGained:rows(r.gained),highDemandLost:rows(r.lost),highDemandFaster:rows(r.faster),highDemandSlower:rows(r.slower)},null,2));}
