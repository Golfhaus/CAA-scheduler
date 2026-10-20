import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis,parseAirportDemand,compareServiceAnalyses} from '../web/opportunity-analysis.mjs';
const get=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const root='outputs/schedule_7_v1_4_1_utilization';
const base=get('data/schedules/schedule_7_v1_4_1_draft/canonical_schedule.json');
const demand=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const initial=buildServiceAnalysis(base,demand,buildItineraries);
const results=[];
for(let i=0;i<2;i++){
 const p=root+'/r107_phf_noon_'+i+'_canonical.json';
 if(!fs.existsSync(p))continue;
 const candidate=get(p),comparison=compareServiceAnalyses(initial,buildServiceAnalysis(candidate,demand,buildItineraries),true);
 const better=comparison.faster.reduce((s,x)=>s+x.demand*(x.beforeMinutes-x.afterMinutes),0);
 const worse=comparison.slower.reduce((s,x)=>s+x.demand*(x.afterMinutes-x.beforeMinutes),0);
 results.push({case:i,flights:candidate.legs.length,gains:comparison.gained,
 losses:comparison.lost,faster:comparison.faster.length,slower:comparison.slower.length,
 weightedNet:better-worse,
 notableWorse:comparison.slower.map(x=>({market:x.market,demand:x.demand,minutes:x.afterMinutes-x.beforeMinutes,
 weighted:x.demand*(x.afterMinutes-x.beforeMinutes)})).sort((a,b)=>b.weighted-a.weighted).slice(0,15)});
}
fs.writeFileSync(root+'/r107_phf_noon_network.json',JSON.stringify(results,null,2)+'\n');
console.log(JSON.stringify(results.map(x=>({case:x.case,gains:x.gains.length,losses:x.losses.length,
 faster:x.faster,slower:x.slower,weightedNet:Math.round(x.weightedNet),
lost:x.losses.map(z=>({market:z.market,demand:z.demand})),gained:x.gains.map(z=>({market:z.market,demand:z.demand})),
worst:x.notableWorse.slice(0,6)})),null,2));
