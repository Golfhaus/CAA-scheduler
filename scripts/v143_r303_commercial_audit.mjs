import {readFileSync} from "node:fs";
import {buildItineraries} from "../web/app.mjs";
import {parseAirportDemand,buildServiceAnalysis,compareServiceAnalyses} from "../web/opportunity-analysis.mjs";
const baseline=JSON.parse(readFileSync("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json"));
const demand=parseAirportDemand(readFileSync("data/reference/airport_od_matrix_consolidated_v2.csv","utf8"));
const old=buildServiceAnalysis(baseline,demand,buildItineraries);
for(const city of ["OMA","DSM"]){
 const next=structuredClone(baseline);
 const p=next.legs.find(x=>x.flight===1346);p.departureMinute=800;p.arrivalMinute=925;p.departure="13:20";p.arrival="15:25";
 const block=city==="OMA"?50:55;
 const added=[["MCI",city,985,985+block],[city,"MCI",985+block+40,985+block*2+40]].map(([origin,destination,dep,arr],i)=>({id:`V143-R303-${city}-${i}`,flight:3100+i,origin,destination,departureMinute:dep,arrivalMinute:arr,departure:`${String(Math.floor(dep/60)).padStart(2,"0")}:${String(dep%60).padStart(2,"0")}`,arrival:`${String(Math.floor(arr/60)).padStart(2,"0")}:${String(arr%60).padStart(2,"0")}`}));
 next.legs.push(...added);
 const result=buildServiceAnalysis(next,demand,buildItineraries);
 for(let geographic of [true,false]){
 const d=compareServiceAnalyses(old,result,geographic);
 const summarize=items=>items.slice().sort((a,b)=>(b.demand||0)-(a.demand||0)).slice(0,18).map(x=>({market:x.market,demand:x.demand,before:x.beforeMinutes,after:x.afterMinutes}));
 console.log(JSON.stringify({city,geographic,gained:d.gained.length,lost:d.lost.length,faster:d.faster.length,slower:d.slower.length,topGains:summarize(d.gained),topLosses:summarize(d.lost),topSlower:summarize(d.slower),topFaster:summarize(d.faster)},null,2));
 }
}
