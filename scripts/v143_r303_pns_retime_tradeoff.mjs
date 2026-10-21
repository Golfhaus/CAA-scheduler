import {readFileSync} from "node:fs";
import {buildItineraries} from "../web/app.mjs";
import {parseAirportDemand,buildServiceAnalysis,compareServiceAnalyses} from "../web/opportunity-analysis.mjs";
const base=JSON.parse(readFileSync("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json")),od=parseAirportDemand(readFileSync("data/reference/airport_od_matrix_consolidated_v2.csv","utf8"));
const before=buildServiceAnalysis(base,od,buildItineraries);
for(const dep of [800,830,860,900]){
 const c=structuredClone(base), l=c.legs.find(x=>x.flight===1346),delta=dep-l.departureMinute;
 l.departureMinute+=delta;l.arrivalMinute+=delta;l.departure=`${String(Math.floor(dep/60)).padStart(2,"0")}:${String(dep%60).padStart(2,"0")}`;l.arrival=`${String(Math.floor(l.arrivalMinute/60)).padStart(2,"0")}:${String(l.arrivalMinute%60).padStart(2,"0")}`;
 const after=buildServiceAnalysis(c,od,buildItineraries);
 for(const geographic of [true,false]){
 const diff=compareServiceAnalyses(before,after,geographic);
 console.log(JSON.stringify({departure:l.departure,geographic,lost:diff.lost.length,slower:diff.slower.length,slowMeaningful:diff.slower.filter(x=>(x.demand||0)>=10).map(x=>({market:x.market,demand:x.demand,before:x.beforeMinutes,after:x.afterMinutes})),gained:diff.gained.length,faster:diff.faster.length}),null,2);
 }
}
