import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis,parseAirportDemand,compareServiceAnalyses} from '../web/opportunity-analysis.mjs';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const root='outputs/schedule_7_v1_4_1_utilization';
const current=read('data/schedules/schedule_7_v1_4_1_draft/canonical_schedule.json');
const proposed=read(root+'/r356_connection_protection_canonical.json');
const demand=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const c=compareServiceAnalyses(buildServiceAnalysis(current,demand,buildItineraries),buildServiceAnalysis(proposed,demand,buildItineraries),true);
const fast=c.faster.reduce((s,x)=>s+x.demand*(x.beforeMinutes-x.afterMinutes),0);
const slow=c.slower.reduce((s,x)=>s+x.demand*(x.afterMinutes-x.beforeMinutes),0);
const record={scope:'R356 flight 2209 moved earlier, vs 1264-flight provisional',
gains:c.gained,losses:c.lost,faster:c.faster,slower:c.slower,
weightedNet:fast-slow};
fs.writeFileSync(root+'/r356_connection_protection_network.json',JSON.stringify(record,null,2)+'\n');
console.log(JSON.stringify({gains:c.gained.length,losses:c.lost.length,faster:c.faster.length,slower:c.slower.length,
net:Math.round(record.weightedNet),gained:c.gained.map(x=>({market:x.market,od:x.demand})),
lost:c.lost.map(x=>({market:x.market,od:x.demand})),
topFaster:c.faster.map(x=>({market:x.market,od:x.demand,improvement:x.beforeMinutes-x.afterMinutes,
weight:x.demand*(x.beforeMinutes-x.afterMinutes)})).sort((a,b)=>b.weight-a.weight).slice(0,12),
topSlower:c.slower.map(x=>({market:x.market,od:x.demand,loss:x.afterMinutes-x.beforeMinutes,
weight:x.demand*(x.afterMinutes-x.beforeMinutes)})).sort((a,b)=>b.weight-a.weight).slice(0,12)},null,2));
