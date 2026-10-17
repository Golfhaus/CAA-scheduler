import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis, parseAirportDemand, coverageView, compareServiceAnalyses} from '../web/opportunity-analysis.mjs';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const root='outputs/schedule_7_v1_3_3_bhm_minibanks_mx5';
const before=read('data/schedules/schedule_7_v1_3_3_draft/canonical_schedule.json');
const after=read(root+'/day_day_canonical.json');
const demand=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const a=buildServiceAnalysis(before,demand,buildItineraries);
const b=buildServiceAnalysis(after,demand,buildItineraries);
const geo=compareServiceAnalyses(a,b,true),raw=compareServiceAnalyses(a,b,false);
const north=['ISP','HVN','ALB','CAK'],south=['MYR','SRQ','CHS','PGD'];
const pairs=[];
for(const n of north)for(const s of south)for(const [o,d] of [[n,s],[s,n]]){
 const x=coverageView(a.records.get(o+'-'+d),true),y=coverageView(b.records.get(o+'-'+d),true);
 const matching=[...b.paths].filter(([flights,p])=>p.market===o+'-'+d&&p.stops===1&&p.reasonable&&
  flights.split('-').every(f=>after.legs.some(l=>l.flight===Number(f)&&[o,d,'BHM'].includes(l.origin)&&[o,d,'BHM'].includes(l.destination))));
 pairs.push({from:o,to:d,direction:n===o?'northToSouth':'southToNorth',
 od:demand[o][d],beforeStops:x.stops,afterStops:y.stops,beforeFastest:x.fastest?.totalMinutes??null,afterFastest:y.fastest?.totalMinutes??null,
 beforeOneStops:x.counts[1],afterOneStops:y.counts[1],bhmOneStopExamples:matching.slice(0,4).map(([ids,p])=>({flights:ids,minutes:p.minutes}))});
}
const changes=after.legs.filter(l=>!before.legs.some(z=>z.id===l.id));
const newRoutes=Object.fromEntries([529,530,357,358].map(id=>[id,{
 fleet:changes.find(l=>l.route===id).fleet,
 flights:changes.filter(l=>l.route===id).map(l=>({flight:l.flight,origin:l.origin,dest:l.destination,departure:l.departure,arrival:l.arrival})),
 routeMinutes:changes.filter(l=>l.route===id).reduce((total,l)=>{
   const zones=Object.fromEntries(after.cities.map(x=>[x.code,{Eastern:60,Central:0,Mountain:-60,Pacific:-120}[x.timezone]??0]));
   return total+(l.arrivalMinute-l.departureMinute-zones[l.destination]+zones[l.origin]+1440)%1440;
 },0)
}]));
const results={
 source:'schedule_7_v1_3_3_draft',proposal:'four spare aircraft through BHM',
 newFlights:changes.length,flightsBefore:before.legs.length,flightsAfter:after.legs.length,
 fleetUseBefore:{CRJ900:28,CRJ700:56},fleetUseAfter:{CRJ900:30,CRJ700:58},
 geography:{gains:geo.gained,losses:geo.lost,faster:geo.faster,slower:geo.slower,lostPaths:geo.lostPaths},
 raw:{gains:raw.gained,losses:raw.lost},
 pairs,newRoutes,
 summary:{coverageGains:geo.gained.length,coverageLosses:geo.lost.length,
 faster:geo.faster.length,slower:geo.slower.length,
 northToSouthServed:pairs.filter(p=>p.direction==='northToSouth'&&p.bhmOneStopExamples.length>0).length,
 southToNorthServed:pairs.filter(p=>p.direction==='southToNorth'&&p.bhmOneStopExamples.length>0).length,
 newlyOneStop:pairs.filter(p=>(p.beforeStops===null||p.beforeStops>1)&&p.afterStops===1).map(p=>p.from+'-'+p.to)}
};
fs.writeFileSync(root+'/network_screen.json',JSON.stringify(results,null,2)+'\n');
console.log(JSON.stringify({summary:results.summary,flights:results.newFlights,routeMinutes:Object.fromEntries(Object.entries(newRoutes).map(([k,v])=>[k,v.routeMinutes])),
 pairSummary:pairs.map(p=>({market:p.from+'-'+p.to,before:p.beforeStops,after:p.afterStops,viaBHM:p.bhmOneStopExamples.length,od:p.od})),lost:geo.lost},null,2));
