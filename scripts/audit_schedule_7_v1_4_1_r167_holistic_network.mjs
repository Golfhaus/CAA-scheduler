import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis,parseAirportDemand,compareServiceAnalyses} from '../web/opportunity-analysis.mjs';
const dir='outputs/schedule_7_v1_4_1_utilization';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const baseline=read('data/schedules/schedule_7_v1_4_1_draft/canonical_schedule.json');
const demand=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const before=buildServiceAnalysis(baseline,demand,buildItineraries);
const cases=read(dir+'/r167_holistic_native.json');
const result=[];
for(let i=0;i<cases.length;i++){
 const x=cases[i];if(!x.pass){result.push({name:x.name,pass:false});continue;}
 const candidate=read(dir+'/r167_holistic_'+i+'_canonical.json');
 const geo=compareServiceAnalyses(before,buildServiceAnalysis(candidate,demand,buildItineraries),true);
 const faster=geo.faster.reduce((v,z)=>v+z.demand*(z.beforeMinutes-z.afterMinutes),0);
 const slower=geo.slower.reduce((v,z)=>v+z.demand*(z.afterMinutes-z.beforeMinutes),0);
 result.push({name:x.name,pass:true,addedFlights:candidate.legs.length-baseline.legs.length,
  gains:geo.gained,losses:geo.lost,faster:geo.faster.length,slower:geo.slower.length,
  weightedNet:faster-slower,
  topSlow:geo.slower.map(z=>({market:z.market,demand:z.demand,extra:z.afterMinutes-z.beforeMinutes,
   weight:z.demand*(z.afterMinutes-z.beforeMinutes)})).sort((a,b)=>b.weight-a.weight).slice(0,8)});
}
fs.writeFileSync(dir+'/r167_holistic_network.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result.map(x=>({name:x.name,pass:x.pass,added:x.addedFlights,gains:x.gains?.length,
 losses:x.losses?.length,faster:x.faster,slower:x.slower,weighted:Math.round(x.weightedNet||0),
 lost:x.losses?.map(z=>({market:z.market,demand:z.demand})),topSlow:x.topSlow?.slice(0,3)})),null,2));
