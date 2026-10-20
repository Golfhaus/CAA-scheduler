import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis,parseAirportDemand,compareServiceAnalyses} from '../web/opportunity-analysis.mjs';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const root='outputs/schedule_7_v1_4_1_utilization';
const base=read('data/schedules/schedule_7_v1_4_0/canonical_schedule.json');
const demand=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const before=buildServiceAnalysis(base,demand,buildItineraries);
const cases=read(root+'/additional_screen.json');
const result=[];
for(let i=0;i<cases.length;i++){
 const c=cases[i];if(!c.pass)continue;
 const canonical=read(root+'/additional_'+i+'_canonical.json');
 const geo=compareServiceAnalyses(before,buildServiceAnalysis(canonical,demand,buildItineraries),true);
 const fast=geo.faster.reduce((s,x)=>s+x.demand*(x.beforeMinutes-x.afterMinutes),0);
 const slow=geo.slower.reduce((s,x)=>s+x.demand*(x.afterMinutes-x.beforeMinutes),0);
 result.push({name:c.name,addedFlights:canonical.legs.length-base.legs.length,
  gains:geo.gained,losses:geo.lost,faster:geo.faster.length,slower:geo.slower.length,
  weightedNet:fast-slow,
  worst:geo.slower.map(x=>({market:x.market,od:x.demand,extraMinutes:x.afterMinutes-x.beforeMinutes,
   weighted:x.demand*(x.afterMinutes-x.beforeMinutes)})).sort((a,b)=>b.weighted-a.weighted).slice(0,10)});
}
fs.writeFileSync(root+'/additional_network.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result.map(x=>({name:x.name,added:x.addedFlights,gains:x.gains.length,losses:x.losses.length,
faster:x.faster,slower:x.slower,net:Math.round(x.weightedNet),
lost:x.losses.map(y=>({market:y.market,demand:y.demand})),gained:x.gains.map(y=>({market:y.market,demand:y.demand})),
worst:x.worst.slice(0,3)})),null,2));
