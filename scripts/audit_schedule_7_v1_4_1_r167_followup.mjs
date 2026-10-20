import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis, parseAirportDemand, compareServiceAnalyses} from '../web/opportunity-analysis.mjs';
const dir='outputs/schedule_7_v1_4_1_utilization';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const base=read('data/schedules/schedule_7_v1_4_1_draft/canonical_schedule.json');
const demand=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const baseline=buildServiceAnalysis(base,demand,buildItineraries);
const screens=read(dir+'/r167_followup_native.json');
const results=[];
for(let i=0;i<screens.length;i++){
 const z=screens[i];if(!z.pass)continue;
 const path=dir+'/r167_followup_'+i+'_canonical.json';
 const c=read(path);
 const geo=compareServiceAnalyses(baseline,buildServiceAnalysis(c,demand,buildItineraries),true);
 const positive=geo.faster.reduce((v,x)=>v+x.demand*(x.beforeMinutes-x.afterMinutes),0);
 const negative=geo.slower.reduce((v,x)=>v+x.demand*(x.afterMinutes-x.beforeMinutes),0);
 results.push({name:z.name,addedFlights:c.legs.length-base.legs.length,
 gains:geo.gained,losses:geo.lost,faster:geo.faster.length,slower:geo.slower.length,
 weightedFast:positive,weightedSlow:negative,weightedNet:positive-negative,
 topSlower:geo.slower.map(x=>({market:x.market,demand:x.demand,
 delay:x.afterMinutes-x.beforeMinutes,impact:x.demand*(x.afterMinutes-x.beforeMinutes)}))
 .sort((a,b)=>b.impact-a.impact).slice(0,12)});
}
fs.writeFileSync(dir+'/r167_followup_network.json',JSON.stringify(results,null,2)+'\n');
console.log(JSON.stringify(results.map(x=>({name:x.name,added:x.addedFlights,gains:x.gains.length,
 losses:x.losses.length,faster:x.faster,slower:x.slower,net:Math.round(x.weightedNet),
 gained:x.gains.map(y=>({market:y.market,od:y.demand})),
 lost:x.losses.map(y=>({market:y.market,od:y.demand})),
 worst:x.topSlower.slice(0,5)})),null,2));
