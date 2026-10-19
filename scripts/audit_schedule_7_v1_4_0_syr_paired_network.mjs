import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis, parseAirportDemand, compareServiceAnalyses} from '../web/opportunity-analysis.mjs';
const root='outputs/schedule_7_v1_4_0_utilization';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const base=read('data/schedules/schedule_7_v1_4_0_draft/canonical_schedule.json');
const demand=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const a=buildServiceAnalysis(base,demand,buildItineraries);
const options=['paired_M12','paired_M15','paired_M17','paired_core','paired_core_plus_R107_M12','paired_all_five'];
const output=[];
for(const name of options){
 const path=root+'/syr_paired_'+name+'_canonical.json';
 if(!fs.existsSync(path)){output.push({name,status:'native feasibility failed; not audited'});continue;}
 const after=read(path),b=buildServiceAnalysis(after,demand,buildItineraries);
 const geo=compareServiceAnalyses(a,b,true),raw=compareServiceAnalyses(a,b,false);
 output.push({name,status:'analyzed',gains:geo.gained,losses:geo.lost,faster:geo.faster,slower:geo.slower,
  rawGains:raw.gained.length,rawLosses:raw.lost.length});
}
fs.writeFileSync(root+'/syr_paired_bank_network.json',JSON.stringify(output,null,2)+'\n');
console.log(JSON.stringify(output.map(x=>({
 name:x.name,status:x.status,gains:x.gains?.length,losses:x.losses?.length,
 faster:x.faster?.length,slower:x.slower?.length,
 lostMarkets:x.losses?.slice(0,25).map(y=>({market:y.market,demand:y.demand})),
 gainedMarkets:x.gains?.slice(0,25).map(y=>({market:y.market,demand:y.demand}))
})),null,2));
