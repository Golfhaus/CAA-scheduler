import {readFileSync} from "node:fs";
import {buildItineraries} from "../web/app.mjs";
import {parseAirportDemand,buildServiceAnalysis,compareServiceAnalyses} from "../web/opportunity-analysis.mjs";
const baseline=JSON.parse(readFileSync("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json"));
const od=parseAirportDemand(readFileSync("data/reference/airport_od_matrix_consolidated_v2.csv","utf8"));
const after=structuredClone(baseline);
const old=after.legs.find(l=>l.flight===1379);
old.departureMinute=650;old.arrivalMinute=716;old.departure="10:50";old.arrival="11:56";
for(const [i,o,d,t,u] of [[0,"CLT","JAX",422,493],[1,"JAX","CLT",533,604]]){
 after.legs.push({id:"V143-R313-JAX-"+i,route:313,line:"AH",day:2,flight:3200+i,origin:o,destination:d,departureMinute:t,arrivalMinute:u,departure:String(Math.floor(t/60)).padStart(2,"0")+":"+String(t%60).padStart(2,"0"),arrival:String(Math.floor(u/60)).padStart(2,"0")+":"+String(u%60).padStart(2,"0")});
}
const avp=after.legs.find(l=>l.flight===1745); avp.departureMinute+=55; avp.arrivalMinute+=55; avp.departure="12:30"; avp.arrival="13:38";
const a=buildServiceAnalysis(baseline,od,buildItineraries),b=buildServiceAnalysis(after,od,buildItineraries);
for(const reasonable of [true,false]){
 const v=compareServiceAnalyses(a,b,reasonable);
 const row=x=>({market:x.market,demand:x.demand,before:x.beforeMinutes,after:x.afterMinutes});
 const sort=arr=>arr.slice().sort((x,y)=>y.demand-x.demand).slice(0,20).map(row);
 console.log(JSON.stringify({reasonable,gained:v.gained.length,lost:v.lost.length,faster:v.faster.length,slower:v.slower.length,topGained:sort(v.gained),topLost:sort(v.lost),topSlower:sort(v.slower),topFaster:sort(v.faster)},null,2));
}
