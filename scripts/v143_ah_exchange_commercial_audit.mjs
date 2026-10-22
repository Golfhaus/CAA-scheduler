import {readFileSync} from "node:fs";
import {buildItineraries} from "../web/app.mjs";
import {parseAirportDemand,buildServiceAnalysis,compareServiceAnalyses} from "../web/opportunity-analysis.mjs";
const base=JSON.parse(readFileSync("data/schedules/schedule_7_v1_4_3_rebuild_candidate/canonical_schedule.json"));
const candidate=JSON.parse(readFileSync("data/schedules/schedule_7_v1_4_3_ah_exchange_candidate/canonical_schedule.json"));
const demand=parseAirportDemand(readFileSync("data/reference/airport_od_matrix_consolidated_v2.csv","utf8"));
const a=buildServiceAnalysis(base,demand,buildItineraries),b=buildServiceAnalysis(candidate,demand,buildItineraries);
const top=rows=>rows.slice().sort((x,y)=>(y.demand||0)-(x.demand||0)).slice(0,25).map(x=>({market:x.market,demand:x.demand,before:x.beforeMinutes,after:x.afterMinutes}));
for(const reasonable of [true,false]){const x=compareServiceAnalyses(a,b,reasonable);console.log(JSON.stringify({reasonable,gained:x.gained.length,lost:x.lost.length,faster:x.faster.length,slower:x.slower.length,topGained:top(x.gained),topLost:top(x.lost),topFaster:top(x.faster),topSlower:top(x.slower)},null,2));}
for(const route of [317,319]){for(const [label,canonical] of [["before",base],["after",candidate]]){let l=canonical.legs.filter(x=>x.route===route),sum=l.reduce((z,x)=>z+((x.arrivalMinute-x.departureMinute+1440)%1440),0);console.log(JSON.stringify({route,label,flightCount:l.length,localClockMinutesNotTZNormalized:sum,flights:l.map(x=>({number:x.flight,from:x.origin,to:x.destination,dep:x.departure,arr:x.arrival})).sort((a,b)=>a.dep.localeCompare(b.dep))}));}}
