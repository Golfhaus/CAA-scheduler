import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis,parseAirportDemand,compareServiceAnalyses} from '../web/opportunity-analysis.mjs';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const dir='outputs/schedule_7_v1_4_0_utilization';
const old=read('data/schedules/schedule_7_v1_4_0_draft/canonical_schedule.json');
const demand=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const base=buildServiceAnalysis(old,demand,buildItineraries);
const reports=[];
for(const [name,file] of [['R107_BWI_BDL','r107_bwi_bdl_loop_canonical.json'],['R160_PHF_plus_R107_BWI_BDL','r160_r107_bwi_combined_canonical.json']]){
 const c=read(dir+'/'+file);
 const b=buildServiceAnalysis(c,demand,buildItineraries);
 const geo=compareServiceAnalyses(base,b,true),raw=compareServiceAnalyses(base,b,false);
 reports.push({name,flights:c.legs.length,gains:geo.gained,losses:geo.lost,
 faster:geo.faster,slower:geo.slower,rawGains:raw.gained.length,rawLosses:raw.lost.length});
}
fs.writeFileSync(dir+'/bwi_bdl_network_comparisons.json',JSON.stringify(reports,null,2)+'\n');
console.log(JSON.stringify(reports.map(x=>({name:x.name,flights:x.flights,gains:x.gains.length,losses:x.losses.length,
 faster:x.faster.length,slower:x.slower.length,
 lostMarkets:x.losses.map(y=>({market:y.market,demand:y.demand})),
 gainedMarkets:x.gains.map(y=>({market:y.market,demand:y.demand}))})),null,2));
