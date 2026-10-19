import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis,parseAirportDemand,compareServiceAnalyses} from '../web/opportunity-analysis.mjs';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const out='outputs/schedule_7_v1_4_0_utilization';
const base=read('data/schedules/schedule_7_v1_4_0_draft/canonical_schedule.json');
const groups=['M12_only','M15_only','M17_only','core_M12_M15_M17','all_except_M09','all_five'];
const demand=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const baseline=buildServiceAnalysis(base,demand,buildItineraries);
const results=[];
for(const name of groups){
 const candidate=read(out+'/syr_group_'+name+'_canonical.json');
 const analysis=buildServiceAnalysis(candidate,demand,buildItineraries);
 const geo=compareServiceAnalyses(baseline,analysis,true);
 const raw=compareServiceAnalyses(baseline,analysis,false);
 results.push({name,flightCount:candidate.legs.length,coverageGains:geo.gained.length,
   coverageLosses:geo.lost.length,faster:geo.faster.length,slower:geo.slower.length,
   coverageLost:geo.lost,coverageGained:geo.gained,rawGains:raw.gained.length,rawLosses:raw.lost.length});
}
fs.writeFileSync(out+'/syr_group_network_audit.json',JSON.stringify(results,null,2)+'\n');
console.log(JSON.stringify(results.map(x=>({name:x.name,coverageGains:x.coverageGains,
coverageLosses:x.coverageLosses,faster:x.faster,slower:x.slower,
lost:x.coverageLost.slice(0,25).map(z=>({market:z.market,demand:z.demand})),
gained:x.coverageGained.slice(0,25).map(z=>({market:z.market,demand:z.demand}))})),null,2));
