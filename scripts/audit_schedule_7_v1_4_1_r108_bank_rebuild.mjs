import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis,parseAirportDemand,compareServiceAnalyses} from '../web/opportunity-analysis.mjs';
const dir='outputs/schedule_7_v1_4_1_utilization',read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const base=read('data/schedules/schedule_7_v1_4_1_draft/canonical_schedule.json');
const demand=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const a=buildServiceAnalysis(base,demand,buildItineraries);
const tests=read(dir+'/r108_bank_rebuild_screen.json');
const result=[];
for(let i=0;i<tests.length;i++){
 const test=tests[i];if(!test.pass){result.push({name:test.name,pass:false});continue;}
 const can=read(dir+'/r108_bank_'+i+'_canonical.json');
 const geo=compareServiceAnalyses(a,buildServiceAnalysis(can,demand,buildItineraries),true);
 const good=geo.faster.reduce((v,z)=>v+z.demand*(z.beforeMinutes-z.afterMinutes),0);
 const bad=geo.slower.reduce((v,z)=>v+z.demand*(z.afterMinutes-z.beforeMinutes),0);
 result.push({name:test.name,pass:true,flights:can.legs.length,gains:geo.gained,losses:geo.lost,
 faster:geo.faster.length,slower:geo.slower.length,weightedNet:good-bad,
 topSlower:geo.slower.map(z=>({market:z.market,demand:z.demand,delay:z.afterMinutes-z.beforeMinutes,weight:z.demand*(z.afterMinutes-z.beforeMinutes)})).sort((a,b)=>b.weight-a.weight).slice(0,10)});
}
fs.writeFileSync(dir+'/r108_bank_rebuild_network.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result.map(x=>({name:x.name,pass:x.pass,gains:x.gains?.length,losses:x.losses?.length,
 faster:x.faster,slower:x.slower,net:Math.round(x.weightedNet||0),lost:x.losses?.map(z=>({market:z.market,demand:z.demand})),worst:x.topSlower?.slice(0,4)})),null,2));
