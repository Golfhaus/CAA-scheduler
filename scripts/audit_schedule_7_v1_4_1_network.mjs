import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis,parseAirportDemand,compareServiceAnalyses} from '../web/opportunity-analysis.mjs';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const root='outputs/schedule_7_v1_4_1_utilization';
const base=read('data/schedules/schedule_7_v1_4_0/canonical_schedule.json');
const demand=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const baseline=buildServiceAnalysis(base,demand,buildItineraries);
const screens=read(root+'/initial_screen.json');
const results=[];
for(let i=0;i<screens.length;i++){
 const x=screens[i];
 if(!x.pass)continue;
 const candidate=read(root+'/screen_'+i+'_canonical.json');
 const comparison=compareServiceAnalyses(baseline,buildServiceAnalysis(candidate,demand,buildItineraries),true);
 const score=(a,sign)=>a.reduce((acc,x)=>acc+x.demand*(sign?(x.beforeMinutes-x.afterMinutes):(x.afterMinutes-x.beforeMinutes)),0);
 const improved=score(comparison.faster,true),worsened=score(comparison.slower,false);
 results.push({name:x.name,route:x.route,addedFlights:candidate.legs.length-base.legs.length,
  gains:comparison.gained,losses:comparison.lost,
  faster:comparison.faster.length,slower:comparison.slower.length,
  weightedFast:improved,weightedSlow:worsened,weightedNet:improved-worsened,
  worstSlow:comparison.slower.map(x=>({market:x.market,demand:x.demand,
     extraMinutes:x.afterMinutes-x.beforeMinutes,
     weight:x.demand*(x.afterMinutes-x.beforeMinutes)})).sort((a,b)=>b.weight-a.weight).slice(0,12)});
}
fs.writeFileSync(root+'/network_screen.json',JSON.stringify(results,null,2)+'\n');
console.log(JSON.stringify(results.map(x=>({name:x.name,flights:x.addedFlights,gains:x.gains.length,
 losses:x.losses.length,fast:x.faster,slow:x.slower,weightedNet:Math.round(x.weightedNet),
 lost:x.losses.map(y=>({market:y.market,demand:y.demand})),
 gained:x.gains.map(y=>({market:y.market,demand:y.demand})),worst:x.worstSlow.slice(0,4)})),null,2));
