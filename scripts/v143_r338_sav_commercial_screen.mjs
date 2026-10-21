import {readFileSync} from "node:fs";
import {buildItineraries} from "../web/app.mjs";
import {parseAirportDemand,buildServiceAnalysis,compareServiceAnalyses} from "../web/opportunity-analysis.mjs";
const s=JSON.parse(readFileSync("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json")),d=parseAirportDemand(readFileSync("data/reference/airport_od_matrix_consolidated_v2.csv","utf8")),before=buildServiceAnalysis(s,d,buildItineraries);
for(const [city,dep,block] of [["CHS",1005,45],["CHS",1020,45],["ILM",1005,55],["CAE",1005,55]]){
 const after=structuredClone(s),r=after.legs.find(x=>x.flight===1493);r.departureMinute=870;r.arrivalMinute=956;r.departure="14:30";r.arrival="15:56";
 const newlegs=[["SAV",city,dep,dep+block],[city,"SAV",dep+block+40,dep+block*2+40]].map(([origin,destination,t,u],i)=>({id:"V143-SAV-"+city+"-"+i,flight:4400+i,origin,destination,departure:String(Math.floor(t/60)).padStart(2,"0")+":"+String(t%60).padStart(2,"0"),arrival:String(Math.floor(u/60)).padStart(2,"0")+":"+String(u%60).padStart(2,"0")}));
 after.legs.push(...newlegs);let v=compareServiceAnalyses(before,buildServiceAnalysis(after,d,buildItineraries),true);
 const summarize=x=>x.slice().sort((a,b)=>(b.demand||0)-(a.demand||0)).slice(0,14).map(y=>({market:y.market,demand:y.demand,before:y.beforeMinutes,after:y.afterMinutes}));
 console.log(JSON.stringify({city,dep,gained:v.gained.length,lost:v.lost.length,faster:v.faster.length,slower:v.slower.length,topGains:summarize(v.gained),topFaster:summarize(v.faster),topSlower:summarize(v.slower),topLost:summarize(v.lost)}));
}
