import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis,parseAirportDemand,compareServiceAnalyses} from '../web/opportunity-analysis.mjs';
const root='outputs/schedule_7_v1_4_1_utilization';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const before=read('data/schedules/schedule_7_v1_4_1_draft/canonical_schedule.json');
const demand=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const analysis=buildServiceAnalysis(before,demand,buildItineraries);
const tests=read(root+'/new_holistic_screen.json');
const report=[];
for(let i=0;i<tests.length;i++){
 const x=tests[i];if(!x.pass){report.push({name:x.name,pass:false});continue;}
 const after=read(root+'/new_holistic_'+i+'_canonical.json');
 const geo=compareServiceAnalyses(analysis,buildServiceAnalysis(after,demand,buildItineraries),true);
 let fast=geo.faster.reduce((a,z)=>a+z.demand*(z.beforeMinutes-z.afterMinutes),0);
 let slow=geo.slower.reduce((a,z)=>a+z.demand*(z.afterMinutes-z.beforeMinutes),0);
 report.push({name:x.name,pass:true,addedFlights:after.legs.length-before.legs.length,
 gains:geo.gained,losses:geo.lost,faster:geo.faster.length,slower:geo.slower.length,
 weightedNet:fast-slow,topSlower:geo.slower.map(z=>({market:z.market,demand:z.demand,delay:z.afterMinutes-z.beforeMinutes,
 weight:z.demand*(z.afterMinutes-z.beforeMinutes)})).sort((a,b)=>b.weight-a.weight).slice(0,10)});
}
fs.writeFileSync(root+'/new_holistic_network.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report.map(x=>({name:x.name,pass:x.pass,added:x.addedFlights,gains:x.gains?.length,losses:x.losses?.length,faster:x.faster,slower:x.slower,
 weightedNet:Math.round(x.weightedNet||0),lost:x.losses?.map(y=>({market:y.market,demand:y.demand})),
 gained:x.gains?.slice(0,12).map(y=>({market:y.market,demand:y.demand})),worst:x.topSlower?.slice(0,4)})),null,2));
