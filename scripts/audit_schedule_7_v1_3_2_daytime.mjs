import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis,parseAirportDemand,compareServiceAnalyses,coverageView} from '../web/opportunity-analysis.mjs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');process.chdir(root);
const dir='outputs/schedule_7_v1_3_2_daytime_screen';
const load=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const baseline=load('outputs/schedule_7_v1_3_2_selected/canonical_schedule.json');
const results=load(dir+'/physical_screen.json');
const od=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const before=buildServiceAnalysis(baseline,od,buildItineraries);
const out={};
for (const [key,result] of Object.entries(results)) {
 if (!result.pass || !fs.existsSync(dir+'/'+key+'_canonical.json')) continue;
 const candidate=load(dir+'/'+key+'_canonical.json');
 const after=buildServiceAnalysis(candidate,od,buildItineraries);
 const geo=compareServiceAnalyses(before,after,true);
 const raw=compareServiceAnalyses(before,after,false);
 const lost=[...before.paths].filter(([name,p])=>!after.paths.has(name)).map(([key,p])=>({key,market:p.market,reasonable:p.reasonable,stops:p.stops,minutes:p.minutes}));
 const downgrades=[];
 for (const [market,record] of before.records) {
  const next=after.records.get(market);
  const prior=coverageView(record,true),post=coverageView(next,true);
  if (prior.stops!==null && (post.stops===null || post.stops>prior.stops))
   downgrades.push({market,demand:record.demand,oldStops:prior.stops,newStops:post.stops});
 }
 const added=candidate.legs.filter(l=>!baseline.legs.some(k=>k.id===l.id));
 const profiles=added.map(l=>({flight:l.flight,market:l.origin+'-'+l.destination,od:od?.[l.origin]?.[l.destination]??null,departure:l.departure,arrival:l.arrival}));
 out[key]={summary:{added:added.length,gains:geo.gained.length,losses:geo.lost.length,faster:geo.faster.length,slower:geo.slower.length,rawLosses:raw.lost.length,rawGains:raw.gained.length,lostPaths:geo.lostPaths,coverageDowngrades:downgrades.length},addedProfiles:profiles,coverageLosses:geo.lost,coverageGains:geo.gained,slowestJourneys:geo.slower,downgrades,lostChoices:lost};
 console.log(key,JSON.stringify(out[key].summary),JSON.stringify(profiles));
}
fs.writeFileSync(dir+'/network_review.json',JSON.stringify(out,null,2)+'\n');
