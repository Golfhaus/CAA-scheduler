import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis, parseAirportDemand, compareServiceAnalyses} from '../web/opportunity-analysis.mjs';
const read=(p)=>JSON.parse(fs.readFileSync(p,'utf8'));
const root='outputs/schedule_7_v1_4_0_utilization';
const before=read('data/schedules/schedule_7_v1_4_0_draft/canonical_schedule.json');
const after=read(root+'/preferred_combined_canonical.json');
const demand=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const a=buildServiceAnalysis(before,demand,buildItineraries);
const b=buildServiceAnalysis(after,demand,buildItineraries);
const geo=compareServiceAnalyses(a,b,true);
const raw=compareServiceAnalyses(a,b,false);
const markets=['BTV-PHF','BDL-BUF','BTV-SYR','BDL-SYR','PHF-SYR','BUF-SYR'];
const result={
  scope:'commercial audit only, NOT accepted or published',
  baseline:before.schedule.id,
  proposal:'R160 BTV-PHF-SYR and R107 BDL-BUF-SYR',
  beforeFlights:before.legs.length,afterFlights:after.legs.length,
  geographicallyReasonable:{
    gains:geo.gained.length,losses:geo.lost.length,
    faster:geo.faster.length,slower:geo.slower.length,
    lostMarkets:geo.lost,
    gainedMarkets:geo.gained,
    slowerMarkets:geo.slower.slice(0,40),
    fasterMarkets:geo.faster.slice(0,40)
  },
  raw:{gains:raw.gained.length,losses:raw.lost.length},
  marketDemand:Object.fromEntries(markets.map(x=>{const [o,d]=x.split('-');return [x,{forward:demand[o]?.[d]??null,reverse:demand[d]?.[o]??null}]}))
};
fs.writeFileSync(root+'/preferred_combined_network.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({
  beforeFlights:result.beforeFlights,afterFlights:result.afterFlights,
  geography:{gains:geo.gained.length,losses:geo.lost.length,faster:geo.faster.length,slower:geo.slower.length,
  lost:geo.lost.slice(0,30)},raw:result.raw,marketDemand:result.marketDemand
},null,2));
