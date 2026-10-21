import {readFileSync} from "node:fs";
import {buildItineraries} from "../web/app.mjs";
import {parseAirportDemand,buildServiceAnalysis,compareServiceAnalyses} from "../web/opportunity-analysis.mjs";
const s=JSON.parse(readFileSync("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json"));
const d=parseAirportDemand(readFileSync("data/reference/airport_od_matrix_consolidated_v2.csv","utf8"));
const after=structuredClone(s),leg=after.legs.find(x=>x.flight===1493);leg.departureMinute=1020;leg.arrivalMinute=1106;leg.departure="17:00";leg.arrival="18:26";
for(const [i,o,t,dep,arr] of [[0,"PHF","RDU",833,883],[1,"RDU","PHF",923,973]]){after.legs.push({id:"V143-R338-PHF-RDU-"+i,route:338,origin:o,destination:t,flight:4500+i,departureMinute:dep,arrivalMinute:arr,departure:String(Math.floor(dep/60)).padStart(2,"0")+":"+String(dep%60).padStart(2,"0"),arrival:String(Math.floor(arr/60)).padStart(2,"0")+":"+String(arr%60).padStart(2,"0")});}
const a=buildServiceAnalysis(s,d,buildItineraries),b=buildServiceAnalysis(after,d,buildItineraries);
const list=v=>v.slice().sort((x,y)=>(y.demand||0)-(x.demand||0)).slice(0,18).map(x=>({market:x.market,demand:x.demand,before:x.beforeMinutes,after:x.afterMinutes}));
for(const geographic of [true,false]){const v=compareServiceAnalyses(a,b,geographic);console.log(JSON.stringify({geographic,gained:v.gained.length,lost:v.lost.length,faster:v.faster.length,slower:v.slower.length,topGains:list(v.gained),topFaster:list(v.faster),topLosses:list(v.lost),topSlower:list(v.slower)}));}
