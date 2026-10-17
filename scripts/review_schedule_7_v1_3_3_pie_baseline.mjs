import fs from 'node:fs';
import {buildItineraries,selectItineraries} from '../web/app.mjs';
import {buildServiceAnalysis,parseAirportDemand,coverageView} from '../web/opportunity-analysis.mjs';
const c=JSON.parse(fs.readFileSync('data/schedules/schedule_7_v1_3_2/canonical_schedule.json','utf8'));
const od=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const a=buildServiceAnalysis(c,od,buildItineraries);
const t={flights:c.legs.map(x=>({origin:x.origin,dest:x.destination,dep:x.departure,arr:x.arrival,flight:x.flight,fleet:x.fleet})),minConnect:c.schedule.connectionWindowMinutes.minimum,maxConnect:c.schedule.connectionWindowMinutes.maximum};
const tz=Object.fromEntries(c.cities.map(x=>[x.code,x.timezone]));
const hs=new Set([...c.operatingPolicy.hubs,...c.operatingPolicy.focusCities]);
const endpoints=['IND','AUS','BLV','GRR'];
const describe=x=>({flights:x.legs.map(y=>y.flight),route:x.legs.map(y=>y.origin).join('→')+'→'+x.dest,dep:x.legs[0].dep,arr:x.legs.at(-1).arr,waits:x.waits,minutes:x.totalMinutes,stops:x.stops});
const result={release:'schedule_7_v1_3_2',pairs:{},nearMisses:[]};
for(const [from,to] of endpoints.flatMap(to=>[['PIE',to],[to,'PIE']])){
 const rec=a.records.get(from+'-'+to);
 const opts=buildItineraries(t,from,hs,tz).filter(x=>x.dest===to).sort((x,y)=>x.stops-y.stops||x.totalMinutes-y.totalMinutes);
 const shortestStop=Math.min(...opts.map(x=>x.stops));
 const reasonable=opts.filter(x=>a.paths.get(x.legs.map(l=>l.flight).join('-'))?.reasonable);
 result.pairs[from+'-'+to]={demand:od[from][to],coverage:coverageView(rec,true),rawCoverage:coverageView(rec,false),shortestStop:Number.isFinite(shortestStop)?shortestStop:null,options:opts.slice(0,20).map(describe),reasonable:reasonable.slice(0,14).map(describe)};
}
result.nearMisses=a.nearMisses.filter(x=>x.origin==='PIE'&&endpoints.includes(x.destination)).map(x=>({market:x.market,demand:x.demand,hub:x.hub,first:{flight:x.first.flight,arrival:x.first.arrival},second:{flight:x.second.flight,departure:x.second.departure},transfer:x.transfer,delta:x.delta,preferred:x.preferred}));
const mciOut=c.legs.filter(l=>l.origin==='MCI'&&endpoints.includes(l.destination)).map(l=>({flight:l.flight,route:l.route,dest:l.destination,dep:l.departure}));
const jaxOut=c.legs.filter(l=>l.origin==='JAX'&&endpoints.includes(l.destination)).map(l=>({flight:l.flight,route:l.route,dest:l.destination,dep:l.departure}));
result.mciOut=mciOut;result.jaxOut=jaxOut;
fs.mkdirSync('outputs/schedule_7_v1_3_3_pie_review',{recursive:true});
fs.writeFileSync('outputs/schedule_7_v1_3_3_pie_review/baseline.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({pairs:Object.fromEntries(Object.entries(result.pairs).map(([k,v])=>[k,{od:v.demand,coverage:{stops:v.coverage.stops,counts:v.coverage.counts},raw:{stops:v.rawCoverage.stops,counts:v.rawCoverage.counts},examples:v.options.slice(0,4),reasonable:v.reasonable.slice(0,3)}])),nearMisses:result.nearMisses,mciOut,jaxOut},null,2));
