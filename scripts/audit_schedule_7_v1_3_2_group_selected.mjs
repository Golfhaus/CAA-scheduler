import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis,parseAirportDemand,compareServiceAnalyses,coverageView} from '../web/opportunity-analysis.mjs';
const load=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const root='outputs/schedule_7_v1_3_2_group_selected';
const before=load('outputs/schedule_7_v1_3_2_selected/canonical_schedule.json');
const after=load(root+'/canonical_schedule.json');
const od=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const old=buildServiceAnalysis(before,od,buildItineraries);
const now=buildServiceAnalysis(after,od,buildItineraries);
const geo=compareServiceAnalyses(old,now,true),raw=compareServiceAnalyses(old,now,false);
const downgrades=[],changedFlights=[];
for(const [key,record] of old.records){
 const a=coverageView(record,true),b=coverageView(now.records.get(key),true);
 if(a.stops!==null&&(b.stops===null||b.stops>a.stops))downgrades.push({market:key,od:record.demand,beforeStops:a.stops,afterStops:b.stops});
}
const prior=new Map(before.legs.map(x=>[x.id,x]));
for(const l of after.legs){
 const p=prior.get(l.id);
 if(!p||p.departureMinute!==l.departureMinute||p.arrivalMinute!==l.arrivalMinute)changedFlights.push({flight:l.flight,route:l.route,from:l.origin,to:l.destination,departure:l.departure,arrival:l.arrival,new:!p});
}
const removed=before.legs.filter(x=>!after.legs.some(l=>l.id===x.id)).map(l=>({route:l.route,flight:l.flight,from:l.origin,to:l.destination}));
const offsets={Eastern:0,Central:-60,Mountain:-120,Pacific:-180};
const zones=new Map(after.cities.map(x=>[x.code,offsets[x.timezone]??0]));
const minutes=l=>(l.arrivalMinute-l.departureMinute+zones.get(l.origin)-zones.get(l.destination)+1440)%1440;
function blocks(c,route){const x=c.legs.filter(l=>l.route===route);return {flights:x.length,total:x.reduce((a,l)=>a+minutes(l),0),critical:x.reduce((a,l)=>{const d=l.departureMinute,b=minutes(l);return a+Math.max(0,Math.min(1320,d+b)-Math.max(360,d))},0)};}
const routes=Object.fromEntries([107,125,146,158,160,176].map(r=>[r,{before:blocks(before,r),after:blocks(after,r)}]));
const evidence={status:'unpublished reviewed working draft; NOT APP DEFAULT',flights:after.legs.length,network:{geographic:{gains:geo.gained,losses:geo.lost,faster:geo.faster,slower:geo.slower,lostPaths:geo.lostPaths},raw:{gains:raw.gained,losses:raw.lost,faster:raw.faster,slower:raw.slower},downgrades},changedFlights,removed,routes};
fs.writeFileSync(root+'/network_review.json',JSON.stringify(evidence,null,2)+'\n');
console.log(JSON.stringify({flights:evidence.flights,routes,geographic:{gains:geo.gained.length,losses:geo.lost.length,faster:geo.faster.length,slower:geo.slower.length,lostPaths:geo.lostPaths},downgrades,removed,changedFlights}));
