import fs from 'node:fs';
import {buildItineraries}from'../web/app.mjs';
import {buildServiceAnalysis,parseAirportDemand,compareServiceAnalyses,coverageView}from'../web/opportunity-analysis.mjs';
import path from 'node:path';import {fileURLToPath}from'node:url';import {createHash}from'node:crypto';
const project=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');process.chdir(project);
const root='outputs/schedule_7_v1_3_2_r144',read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const base=read('data/schedules/schedule_7_v1_3_2_draft/canonical_schedule.json'),od=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8')),before=buildServiceAnalysis(base,od,buildItineraries),native=read(root+'/native.json');
let results=process.argv.length>2&&fs.existsSync(root+'/network.json')?read(root+'/network.json'):{};
const picked=process.argv.slice(2);
for(const[name,n]of Object.entries(native)){
 if(!n.valid||picked.length&&!picked.includes(name))continue;
 const c=read(root+'/'+name+'_canonical.json'),after=buildServiceAnalysis(c,od,buildItineraries),geo=compareServiceAnalyses(before,after,true);
 const changed=c.legs.filter(l=>l.route===144||base.legs.some(b=>b.id===l.id&&b.departureMinute!==l.departureMinute));
function flightProfiles(analysis,legs){return legs.map(l=>{
  const markets=new Map();
  for(const [key,p]of analysis.paths){
   if(!p.reasonable||p.stops>1||!key.split('-').includes(String(l.flight)))continue;
   const r=analysis.records.get(p.market),old=before.records.get(p.market),fast=coverageView(r,true).fastest;
   if(p.stops&&r.counts[0])continue;
   if(markets.has(p.market)&&markets.get(p.market).minutes<=p.minutes)continue;
   const options=[...analysis.paths].filter(([,s])=>s.market===p.market&&s.reasonable&&s.stops===p.stops&&s.minutes<=fast.totalMinutes+30),using=options.filter(([k])=>k.split('-').includes(String(l.flight)));
   markets.set(p.market,{market:p.market,demand:r.demand,minutes:p.minutes,stops:p.stops,newOneStop:coverageView(old,true).gap,competitive:p.minutes<=fast.totalMinutes+30,choiceShare:using.length/(options.length||1)});
  }
  const mm=[...markets.values()];return{flight:l.flight,market:l.origin+'-'+l.destination,departure:l.departure,arrival:l.arrival,localOd:od[l.origin][l.destination],competitiveIndex:mm.filter(m=>m.competitive).reduce((s,m)=>s+m.demand*m.choiceShare,0),markets:mm.sort((a,b)=>b.demand-a.demand)};
 });}
 const profiles=flightProfiles(after,changed),baselineProfiles=flightProfiles(before,base.legs.filter(l=>l.route===144));
 const downgrades=[];for(const[k,old]of before.records){const now=after.records.get(k),a=coverageView(old,true),b=coverageView(now,true);if(a.stops<b.stops&&a.stops!==null&&b.stops!==null)downgrades.push({market:k,demand:old.demand,beforeStops:a.stops,afterStops:b.stops});}
 const raw=compareServiceAnalyses(before,after,false); const lostChoices=[...before.paths].filter(([k,p])=>!after.paths.has(k)).map(([k,p])=>({key:k,market:p.market,stops:p.stops,minutes:p.minutes,reasonable:p.reasonable}));
 const r={geo,raw,lostChoices,downgrades,profiles,baselineProfiles,flights:c.legs.length};results[name]=r;
 console.log(name,JSON.stringify({flights:r.flights,gained:geo.gained.length,lost:geo.lost.length,stopDowngrades:downgrades.length,faster:geo.faster.length,slower:geo.slower.length,lostPaths:geo.lostPaths}));
}
fs.writeFileSync(root+'/network.json',JSON.stringify(results,null,2)+'\n');

const sha=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex');
fs.writeFileSync(root+'/provenance.json',JSON.stringify({baseCommit:'4d72b3eaea5d3659e09e7c8b252ca889f2ac21a9',baseConfiguration:'config/optimizations/schedule_7_v1_3_2_round_5.json',baseConfigurationSha256:sha('config/optimizations/schedule_7_v1_3_2_round_5.json'),baseSha256:sha('data/schedules/schedule_7_v1_3_2_draft/canonical_schedule.json'),demandSha256:sha('data/reference/airport_od_matrix_consolidated_v2.csv'),method:'Same app enumeration, 30–240 minute connections, 2.25x geographic screen. Competitive opportunity indices split underlying OD over choices within 30 minutes of fastest at the same stop count and exclude connections when a nonstop exists; they are not passenger-load forecasts.'},null,2)+'\n');
