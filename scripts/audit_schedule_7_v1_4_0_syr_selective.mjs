import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis,parseAirportDemand,compareServiceAnalyses} from '../web/opportunity-analysis.mjs';
const folder='outputs/schedule_7_v1_4_0_utilization';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const baseline=read('data/schedules/schedule_7_v1_4_0_draft/canonical_schedule.json');
const demand=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const a=buildServiceAnalysis(baseline,demand,buildItineraries);
const plans=['selective_six','selective_seven_HVN','selective_six_plus_R160_extension'];
const out=[];
for(const name of plans){
 const path=folder+'/syr_selective_'+name+'_canonical.json';
 if(!fs.existsSync(path)){out.push({name,status:'not native valid'});continue;}
 const x=read(path),b=buildServiceAnalysis(x,demand,buildItineraries),geo=compareServiceAnalyses(a,b,true);
 out.push({name,flights:x.legs.length,gains:geo.gained,losses:geo.lost,faster:geo.faster,slower:geo.slower});
}
fs.writeFileSync(folder+'/syr_selective_network.json',JSON.stringify(out,null,2)+'\n');
console.log(JSON.stringify(out.map(x=>({name:x.name,flights:x.flights,gains:x.gains?.length,losses:x.losses?.length,
faster:x.faster?.length,slower:x.slower?.length,lossMarkets:x.losses?.map(y=>({market:y.market,od:y.demand})),
gainMarkets:x.gains?.map(y=>({market:y.market,od:y.demand}))})),null,2));
