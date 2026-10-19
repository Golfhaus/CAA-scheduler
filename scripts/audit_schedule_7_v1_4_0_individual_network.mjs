import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis, parseAirportDemand, compareServiceAnalyses} from '../web/opportunity-analysis.mjs';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const out='outputs/schedule_7_v1_4_0_utilization';
const base=read('data/schedules/schedule_7_v1_4_0_draft/canonical_schedule.json');
const demand=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const baseline=buildServiceAnalysis(base,demand,buildItineraries);
const plans=['R160_BTV_PHF','R160_BTV_PWM','R107_BDL_BUF','R107_BDL_ROC','R107_BDL_PVD'];
const result=[];
for(const name of plans){
 const candidate=read(out+'/net_'+name+'.json');
 const analysis=buildServiceAnalysis(candidate,demand,buildItineraries);
 const geo=compareServiceAnalyses(baseline,analysis,true);
 const raw=compareServiceAnalyses(baseline,analysis,false);
 const item={name,flights: candidate.legs.length,coverageGains:geo.gained.length,
  coverageLosses:geo.lost.length,faster:geo.faster.length,slower:geo.slower.length,
  gains:geo.gained,losses:geo.lost,improved:geo.faster,regressed:geo.slower,
  rawGains:raw.gained.length,rawLosses:raw.lost.length};
 result.push(item);
}
fs.writeFileSync(out+'/individual_network_comparisons.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result.map(x=>({name:x.name,gains:x.coverageGains,losses:x.coverageLosses,
 faster:x.faster,slower:x.slower,lostMarkets:x.losses.map(z=>({market:z.market,demand:z.demand})),
 gainedMarkets:x.gains.map(z=>({market:z.market,demand:z.demand}))})),null,2));
