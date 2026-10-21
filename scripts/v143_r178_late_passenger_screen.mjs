import {readFileSync} from "node:fs";
import {buildItineraries} from "../web/app.mjs";
import {parseAirportDemand,buildServiceAnalysis,compareServiceAnalyses} from "../web/opportunity-analysis.mjs";
const schedule=JSON.parse(readFileSync("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json"));
const demand=parseAirportDemand(readFileSync("data/reference/airport_od_matrix_consolidated_v2.csv","utf8"));
const baseline=buildServiceAnalysis(schedule,demand,buildItineraries);
for(const [city,depart,block] of [["ALB",1170,50],["PWM",1140,65],["PVD",1140,65],["BDL",1170,50],["HPN",1140,60],["PIT",1140,65],["ORH",1140,60]]){
 const added=[["SYR",city,depart,depart+block],[city,"SYR",depart+block+40,depart+block*2+40]].map(([origin,destination,d,a],i)=>({id:"SC143-"+city+"-"+i,origin,destination,departureMinute:d,arrivalMinute:a,departure:`${String(Math.floor(d/60)).padStart(2,"0")}:${String(d%60).padStart(2,"0")}`,arrival:`${String(Math.floor(a/60)).padStart(2,"0")}:${String(a%60).padStart(2,"0")}`,flight:3990+i}));
 const candidate=buildServiceAnalysis({...schedule,legs:[...schedule.legs,...added]},demand,buildItineraries);
 const delta=compareServiceAnalyses(baseline,candidate,true);
 const row=x=>({market:x.market,demand:x.demand,before:x.beforeMinutes,after:x.afterMinutes});
 const gains=delta.gained.filter(x=>(x.demand||0)>=10),faster=delta.faster.filter(x=>(x.demand||0)>=10);
 console.log(JSON.stringify({city,depart,back:depart+block*2+40,gained:delta.gained.length,lost:delta.lost.length,faster:delta.faster.length,slower:delta.slower.length,meaningfulGains:gains.map(row).slice(0,15),highestDemandFaster:faster.sort((a,b)=>b.demand-a.demand).map(row).slice(0,8)},null,2));
}
