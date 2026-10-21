import {readFileSync} from "node:fs";
import {buildItineraries} from "../web/app.mjs";
import {parseAirportDemand,buildServiceAnalysis,compareServiceAnalyses} from "../web/opportunity-analysis.mjs";
const s=JSON.parse(readFileSync("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json")),d=parseAirportDemand(readFileSync("data/reference/airport_od_matrix_consolidated_v2.csv","utf8")),baseline=buildServiceAnalysis(s,d,buildItineraries);
for(const [city,block] of [["TYS",55],["GSO",45],["GSP",40],["AVL",45],["CAE",45]]){
 const dep=840,arr=dep+block,ret=arr+40,end=ret+block;
 const legs=[["CLT",city,dep,arr],[city,"CLT",ret,end]].map(([origin,destination,t,u],i)=>({origin,destination,departure:String(Math.floor(t/60)).padStart(2,"0")+":"+String(t%60).padStart(2,"0"),arrival:String(Math.floor(u/60)).padStart(2,"0")+":"+String(u%60).padStart(2,"0"),flight:4300+i}));
 const after=buildServiceAnalysis({...s,legs:[...s.legs,...legs]},d,buildItineraries);
 const v=compareServiceAnalyses(baseline,after,true);
 const summary=xs=>xs.slice().sort((a,b)=>(b.demand||0)-(a.demand||0)).slice(0,12).map(x=>({market:x.market,demand:x.demand,before:x.beforeMinutes,after:x.afterMinutes}));
 console.log(JSON.stringify({city,flightMinutes:block*2,gained:v.gained.length,lost:v.lost.length,faster:v.faster.length,slower:v.slower.length,topNew:summary(v.gained),topFaster:summary(v.faster),topSlower:summary(v.slower)}));
}
