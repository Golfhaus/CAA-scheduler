import {readFileSync} from "node:fs";
import {buildItineraries} from "../web/app.mjs";
import {parseAirportDemand,buildServiceAnalysis,compareServiceAnalyses} from "../web/opportunity-analysis.mjs";
const canonical=JSON.parse(readFileSync("data/schedules/schedule_7_v1_4_2/canonical_schedule.json"));
const od=parseAirportDemand(readFileSync("data/reference/airport_od_matrix_consolidated_v2.csv","utf8"));
const cities=Object.fromEntries(canonical.cities.map(c=>[c.code,c]));
const base=buildServiceAnalysis(canonical,od,buildItineraries);
const rad=x=>x*Math.PI/180;
function nm(a,b){let x=cities[a],y=cities[b],lat=rad(y.latitude-x.latitude),lng=rad(y.longitude-x.longitude),h=Math.sin(lat/2)**2+Math.cos(rad(x.latitude))*Math.cos(rad(y.latitude))*Math.sin(lng/2)**2;return 3440.065*2*Math.asin(Math.min(1,Math.sqrt(h)));}
const tz={Eastern:-4,Central:-5,Mountain:-6,Pacific:-7};
function trip(from,to,departure){let block=Math.round((28+nm(from,to)*60/420)/5)*5,arrival=departure+block+(tz[cities[to].timezone]-tz[cities[from].timezone])*60;return {from,to,departure,arrival,block};}
function test(route,city,destination,window){
 const begin=window==="morning"?(route===359?360:310):(route===177?975:route===178?930:route===359?780:900);
 const first=trip(city,destination,begin);
 const second=trip(destination,city,first.arrival+45);
 if(second.arrival>(route===177&&window==="morning"?560:route===178&&window==="morning"?610:route===359?1170:1410))return null;
 if(first.arrival>=1440||second.departure>1260||second.arrival<0)return null;
 const added=[first,second].map((t,i)=>({id:`V143-SCREEN-${route}-${destination}-${i}`,route,flight:4000+i,origin:t.from,destination:t.to,departureMinute:t.departure,arrivalMinute:t.arrival,departure:String(Math.floor((t.departure+1440)%1440/60)).padStart(2,"0")+":"+String((t.departure+1440)%60).padStart(2,"0"),arrival:String(Math.floor((t.arrival+1440)%1440/60)).padStart(2,"0")+":"+String((t.arrival+1440)%60).padStart(2,"0")}));
 const schedule={...canonical,legs:[...canonical.legs,...added]};
 const after=buildServiceAnalysis(schedule,od,buildItineraries);
 const delta=compareServiceAnalyses(base,after,true);
 const sum=rows=>rows.reduce((a,v)=>a+Math.max(0,v.demand||0),0);
 const gain=delta.gained.filter(x=>(x.demand||0)>=10), faster=delta.faster.filter(x=>(x.demand||0)>=10);
 return {route,city,destination,window,depart:first.departure,back:second.arrival,blockMinutes:first.block+second.block,odRound:Math.round(((od[city]?.[destination]||0)+(od[destination]?.[city]||0))*10)/10,coverageGained:delta.gained.length,lost:delta.lost.length,faster:delta.faster.length,slower:delta.slower.length,meaningfulDemand:Math.round(sum(gain)*10)/10,travelValue:Math.round(faster.reduce((s,x)=>s+(x.demand||0)*Math.max(0,(x.beforeMinutes||0)-(x.afterMinutes||0)),0)),topGains:gain.slice(0,7).map(x=>({market:x.market,demand:x.demand,before:x.beforeMinutes,after:x.afterMinutes}))};
}
const cases={177:["SFB","PIE","PGD","SAT","CLT","FLL","BDL","OMA","BNA","PVD","CMH"],178:["PVD","BDL","DAL","CHS","IND","BTV","PWM","ISP","ALB","ROC","CMH","BUF"],359:["RFD","SFB","FLL","AUS","DAL","PIE","CLT","RDU","PIT","HOU","JAX","MSY","OMA","PGD","SRQ"]};
for(const route of [177,178,359]){
 let city=route===177?"DAY":route===178?"SYR":"BNA";
 let results=[];
 for(const dest of cases[route])for(const window of ["morning","evening"]){
  const r=test(route,city,dest,window);if(r)results.push(r);
 }
 results.sort((a,b)=>b.travelValue-a.travelValue);
 console.log(JSON.stringify({route,anchor:city,options:results.slice(0,16)},null,2));
}
