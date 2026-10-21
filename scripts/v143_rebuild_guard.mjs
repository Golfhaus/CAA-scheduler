import {readFileSync} from "node:fs";
import {buildItineraries} from "../web/app.mjs";
import {parseAirportDemand,buildServiceAnalysis,coverageView} from "../web/opportunity-analysis.mjs";
const base=JSON.parse(readFileSync("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json"));
const demand=parseAirportDemand(readFileSync("data/reference/airport_od_matrix_consolidated_v2.csv","utf8"));
const marketThreshold=8;
const original=buildServiceAnalysis(base,demand,buildItineraries);
const protectedMarkets=[];
for(const [market,record] of original.records){
 if((record.demand??0)<=marketThreshold)continue;
 const stops=coverageView(record,true).stops;
 if(stops!==1 && stops!==0)continue;
 protectedMarkets.push({market,demand:record.demand,baselineStops:stops});
}
export function auditRebuild(candidate){
 const after=buildServiceAnalysis(candidate,demand,buildItineraries);
 const losses=[];
 for(const {market,demand,baselineStops} of protectedMarkets){
  const r=after.records.get(market);
  const stops=coverageView(r,true).stops;
  if(stops===null || stops>1)losses.push({market,demand,baselineStops,newStops:stops,reason:"one-stop-or-nonstop-coverage-lost"});
 }
 return {protectedMarketCount:protectedMarkets.length,protectedMarketLosses:losses.length,losses};
}
if(process.argv[1]?.endsWith("v143_rebuild_guard.mjs")){
 const candidate=JSON.parse(readFileSync(process.argv[2]||"data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json"));
 const summary=auditRebuild(candidate);
 console.log(JSON.stringify(summary,null,2));
 if(summary.losses.length)process.exitCode=1;
}
