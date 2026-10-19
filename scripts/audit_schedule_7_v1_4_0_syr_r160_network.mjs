import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis,parseAirportDemand,compareServiceAnalyses} from '../web/opportunity-analysis.mjs';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const folder='outputs/schedule_7_v1_4_0_utilization';
const baseline=read('data/schedules/schedule_7_v1_4_0_draft/canonical_schedule.json');
const candidate=read(folder+'/syr_r160_extended_network_candidate.json');
const demand=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const a=buildServiceAnalysis(baseline,demand,buildItineraries);
const b=buildServiceAnalysis(candidate,demand,buildItineraries);
const geo=compareServiceAnalyses(a,b,true),raw=compareServiceAnalyses(a,b,false);
const report={name:'SYR M15 R160 PWM-PHF-PWM extension, no other changed routes',
 flightsBefore:baseline.legs.length,flightsAfter:candidate.legs.length,
 gains:geo.gained,losses:geo.lost,faster:geo.faster,slower:geo.slower,
 rawGains:raw.gained.length,rawLosses:raw.lost.length};
fs.writeFileSync(folder+'/syr_r160_extended_network_audit.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({flights:[report.flightsBefore,report.flightsAfter],
 coverageGains:geo.gained.length,coverageLosses:geo.lost.length,
 faster:geo.faster.length,slower:geo.slower.length,
 losses:geo.lost.slice(0,25).map(x=>({market:x.market,demand:x.demand})),
 gains:geo.gained.slice(0,25).map(x=>({market:x.market,demand:x.demand}))},null,2));
