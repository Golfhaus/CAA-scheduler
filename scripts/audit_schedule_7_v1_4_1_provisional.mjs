import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis,parseAirportDemand,compareServiceAnalyses} from '../web/opportunity-analysis.mjs';
const load=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const base=load('data/schedules/schedule_7_v1_4_0/canonical_schedule.json');
const after=load('data/schedules/schedule_7_v1_4_1_draft/canonical_schedule.json');
const demand=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const a=buildServiceAnalysis(base,demand,buildItineraries),b=buildServiceAnalysis(after,demand,buildItineraries);
const c=compareServiceAnalyses(a,b,true);
const up=c.faster.reduce((n,x)=>n+x.demand*(x.beforeMinutes-x.afterMinutes),0);
const down=c.slower.reduce((n,x)=>n+x.demand*(x.afterMinutes-x.beforeMinutes),0);
const report={scope:'unpublished v1.4.1 provisional vs published v1.4.0',beforeFlights:base.legs.length,afterFlights:after.legs.length,
  gains:c.gained,losses:c.lost,faster:c.faster,slower:c.slower,
  weightedFaster:up,weightedSlower:down,weightedNet:up-down};
fs.mkdirSync('outputs/schedule_7_v1_4_1_utilization',{recursive:true});
fs.writeFileSync('outputs/schedule_7_v1_4_1_utilization/provisional_network.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({before:report.beforeFlights,after:report.afterFlights,gains:c.gained.length,losses:c.lost.length,
  faster:c.faster.length,slower:c.slower.length,weightedNet:Math.round(up-down),
  losses:c.lost.map(x=>({market:x.market,od:x.demand})),gainsSample:c.gained.slice(0,30).map(x=>({market:x.market,od:x.demand})),
  worstSlower:c.slower.map(x=>({market:x.market,od:x.demand,extra:x.afterMinutes-x.beforeMinutes,weighted:x.demand*(x.afterMinutes-x.beforeMinutes)})).sort((x,y)=>y.weighted-x.weighted).slice(0,12)},null,2));
