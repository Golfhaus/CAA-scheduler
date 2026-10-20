import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis,parseAirportDemand,compareServiceAnalyses} from '../web/opportunity-analysis.mjs';
const load=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const d='outputs/schedule_7_v1_4_1_utilization';
const base=load('data/schedules/schedule_7_v1_4_1_draft/canonical_schedule.json');
const candidate=load(d+'/holistic_0_canonical.json');
const demand=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const before=buildServiceAnalysis(base,demand,buildItineraries),after=buildServiceAnalysis(candidate,demand,buildItineraries);
const geo=compareServiceAnalyses(before,after,true);
const fast=geo.faster.reduce((v,x)=>v+x.demand*(x.beforeMinutes-x.afterMinutes),0);
const slow=geo.slower.reduce((v,x)=>v+x.demand*(x.afterMinutes-x.beforeMinutes),0);
const report={name:'R167 ALB-BWI-ALB morning turn',comparison:'provisional R105/R162 draft',
 flightsBefore:base.legs.length,flightsAfter:candidate.legs.length,
 gains:geo.gained,losses:geo.lost,faster:geo.faster,slower:geo.slower,
 weightedFast:fast,weightedSlow:slow,weightedNet:fast-slow};
fs.writeFileSync(d+'/holistic_network.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({newFlights:2,gains:geo.gained.length,losses:geo.lost.length,
 faster:geo.faster.length,slower:geo.slower.length,weightedNet:Math.round(report.weightedNet),
 gained:geo.gained.map(x=>({market:x.market,od:x.demand})),
 lost:geo.lost.map(x=>({market:x.market,od:x.demand})),
 worse:geo.slower.map(x=>({market:x.market,od:x.demand,minutes:x.afterMinutes-x.beforeMinutes,
 weight:x.demand*(x.afterMinutes-x.beforeMinutes)})).sort((a,b)=>b.weight-a.weight).slice(0,12)},null,2));
