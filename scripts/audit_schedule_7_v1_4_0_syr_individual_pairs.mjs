import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis, parseAirportDemand, compareServiceAnalyses} from '../web/opportunity-analysis.mjs';
const root='outputs/schedule_7_v1_4_0_utilization';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const base=read('data/schedules/schedule_7_v1_4_0_draft/canonical_schedule.json');
const demand=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const original=buildServiceAnalysis(base,demand,buildItineraries);
const manifest=read(root+'/syr_single_paired_manifest.json');
const output=[];
for(const meta of manifest){
 const candidate=read(root+'/syr_single_paired_'+meta.name+'.json');
 const analysis=buildServiceAnalysis(candidate,demand,buildItineraries);
 const geo=compareServiceAnalyses(original,analysis,true);
 output.push({...meta,gains:geo.gained.length,losses:geo.lost.length,faster:geo.faster.length,
 slower:geo.slower.length,marketsGained:geo.gained,marketsLost:geo.lost});
}
fs.writeFileSync(root+'/syr_single_paired_network.json',JSON.stringify(output,null,2)+'\n');
console.log(JSON.stringify(output.map(x=>({name:x.name,route:x.route,bank:x.bank,
 gains:x.gains,losses:x.losses,faster:x.faster,slower:x.slower,
 lost:x.marketsLost.map(y=>({market:y.market,demand:y.demand})),
 gained:x.marketsGained.map(y=>({market:y.market,demand:y.demand}))})),null,2));
