import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis,parseAirportDemand,compareServiceAnalyses} from '../web/opportunity-analysis.mjs';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const root='outputs/schedule_7_v1_4_1_utilization';
const base=read('data/schedules/schedule_7_v1_4_0/canonical_schedule.json');
const demand=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const baseline=buildServiceAnalysis(base,demand,buildItineraries);
const screens=read(root+'/supplemental_screen.json');
const results=[];
for(let i=0;i<screens.length;i++){
 const x=screens[i];
 if(!x.pass)continue;
 const candidate=read(root+'/extra_'+i+'_canonical.json');
 const comparison=compareServiceAnalyses(baseline,buildServiceAnalysis(candidate,demand,buildItineraries),true);
 const faster=comparison.faster.reduce((v,x)=>v+x.demand*(x.beforeMinutes-x.afterMinutes),0);
 const slower=comparison.slower.reduce((v,x)=>v+x.demand*(x.afterMinutes-x.beforeMinutes),0);
 results.push({name:x.name,route:x.route,newFlights:candidate.legs.length-base.legs.length,
  gains:comparison.gained,losses:comparison.lost,
  faster:comparison.faster.length,slower:comparison.slower.length,
  weightedNet:faster-slower,weightedFaster:faster,weightedSlower:slower,
  worstSlower:comparison.slower.map(x=>({market:x.market,demand:x.demand,
     extraMinutes:x.afterMinutes-x.beforeMinutes,
     weighted:x.demand*(x.afterMinutes-x.beforeMinutes)})).sort((a,b)=>b.weighted-a.weighted).slice(0,8)});
}
fs.writeFileSync(root+'/supplemental_network.json',JSON.stringify(results,null,2)+'\n');
console.log(JSON.stringify(results.map(x=>({name:x.name,flights:x.newFlights,
 gains:x.gains.length,losses:x.losses.length,faster:x.faster,slower:x.slower,net:Math.round(x.weightedNet),
 lost:x.losses.map(y=>({market:y.market,demand:y.demand})),gained:x.gains.map(y=>({market:y.market,demand:y.demand})),
worst:x.worstSlower.slice(0,3)})),null,2));
