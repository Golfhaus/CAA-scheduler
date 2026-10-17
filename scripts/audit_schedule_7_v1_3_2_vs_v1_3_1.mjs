import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis,parseAirportDemand,compareServiceAnalyses,coverageView} from '../web/opportunity-analysis.mjs';
const load=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const old=load('data/schedules/schedule_7_v1_3_1/canonical_schedule.json');
const next=load('data/schedules/schedule_7_v1_3_2_draft/canonical_schedule.json');
const od=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const before=buildServiceAnalysis(old,od,buildItineraries),after=buildServiceAnalysis(next,od,buildItineraries);
const geo=compareServiceAnalyses(before,after,true),raw=compareServiceAnalyses(before,after,false);
const downgrades=[];
for(const [market,record] of before.records){
 const a=coverageView(record,true),b=coverageView(after.records.get(market),true);
 if(a.stops!==null&&(b.stops===null||b.stops>a.stops))downgrades.push({market,demand:record.demand,from:a.stops,to:b.stops});
}
const result={baseline:'schedule_7_v1_3_1',draft:'schedule_7_v1_3_2_draft',published:false,flightsBefore:old.legs.length,flightsAfter:next.legs.length,linesBefore:new Set(old.legs.map(l=>l.line)).size,linesAfter:new Set(next.legs.map(l=>l.line)).size,geographic:{gained:geo.gained,lost:geo.lost,faster:geo.faster,slower:geo.slower,lostPaths:geo.lostPaths},raw:{gained:raw.gained,lost:raw.lost,faster:raw.faster,slower:raw.slower},downgrades};
const dest='outputs/schedule_7_v1_3_2_release_readiness';
fs.mkdirSync(dest,{recursive:true});
fs.writeFileSync(dest+'/network_vs_v131.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({flightsBefore:result.flightsBefore,flightsAfter:result.flightsAfter,linesBefore:result.linesBefore,linesAfter:result.linesAfter,geographic:{gains:geo.gained.length,losses:geo.lost.length,faster:geo.faster.length,slower:geo.slower.length},downgrades:downgrades.length}));
