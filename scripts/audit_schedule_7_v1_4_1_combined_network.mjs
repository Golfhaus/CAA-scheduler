import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis,parseAirportDemand,compareServiceAnalyses} from '../web/opportunity-analysis.mjs';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const root='outputs/schedule_7_v1_4_1_utilization';
const base=read('data/schedules/schedule_7_v1_4_0/canonical_schedule.json');
const demand=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const before=buildServiceAnalysis(base,demand,buildItineraries);
const cases=read(root+'/combined_screen.json');
const results=[];
for (const x of cases){
 if(!x.pass){results.push({name:x.name,pass:false});continue;}
 const after=read(root+'/combined_'+x.name+'_canonical.json');
 const geo=compareServiceAnalyses(before,buildServiceAnalysis(after,demand,buildItineraries),true);
 const fast=geo.faster.reduce((n,y)=>n+y.demand*(y.beforeMinutes-y.afterMinutes),0);
 const slow=geo.slower.reduce((n,y)=>n+y.demand*(y.afterMinutes-y.beforeMinutes),0);
 results.push({name:x.name,pass:true,flights:after.legs.length,
  gains:geo.gained,losses:geo.lost,faster:geo.faster.length,slower:geo.slower.length,
  weightedFast:fast,weightedSlow:slow,weightedNet:fast-slow,
  topWorse:geo.slower.map(y=>({market:y.market,od:y.demand,
   extra:y.afterMinutes-y.beforeMinutes,weight:y.demand*(y.afterMinutes-y.beforeMinutes)}))
   .sort((a,b)=>b.weight-a.weight).slice(0,12)});
}
fs.writeFileSync(root+'/combined_network.json',JSON.stringify(results,null,2)+'\n');
console.log(JSON.stringify(results.map(x=>({name:x.name,pass:x.pass,flights:x.flights,
 gains:x.gains?.length,losses:x.losses?.length,faster:x.faster,slower:x.slower,
 weightedNet:Math.round(x.weightedNet??0),
 lost:x.losses?.map(y=>({market:y.market,demand:y.demand})),
 gained:x.gains?.slice(0,12).map(y=>({market:y.market,demand:y.demand})),
 worst:x.topWorse?.slice(0,4)})),null,2));
