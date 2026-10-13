import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis,parseAirportDemand,coverageView,compareServiceAnalyses} from '../web/opportunity-analysis.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),out=root+'/outputs/schedule_7_v1_3_1_dsm';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const checkpoint=out+'/base_round_3_canonical.json';
const base=read(fs.existsSync(checkpoint)?checkpoint:root+'/data/schedules/schedule_7_v1_3_1_draft/canonical_schedule.json');
const od=parseAirportDemand(fs.readFileSync(root+'/data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const before=buildServiceAnalysis(base,od,buildItineraries),native=read(out+'/native_screen.json'),results={};
const accepted=process.argv.includes('--accepted');
const picked=accepted?['combined_basic']:process.argv.slice(2);
for(const [name,n]of Object.entries(native)){
 if(!n.valid||picked.length&&!picked.includes(name))continue;
 const c=read(accepted?root+'/data/schedules/schedule_7_v1_3_1_draft/canonical_schedule.json':out+'/'+name+'_canonical.json'),after=buildServiceAnalysis(c,od,buildItineraries),raw=compareServiceAnalyses(before,after),geo=compareServiceAnalyses(before,after,true);
 const flights=c.legs.filter(l=>!base.legs.some(b=>b.id===l.id)||base.legs.some(b=>b.id===l.id&&(b.departure!==l.departure||b.arrival!==l.arrival)));
 const profiles=flights.map(l=>{
  const markets=new Map();
  for(const [key,p]of after.paths){
   if(!p.reasonable||p.stops>1||!key.split('-').includes(String(l.flight)))continue;
   const r=after.records.get(p.market),old=before.records.get(p.market);if(p.stops&&old.counts[0])continue;
   const a=coverageView(old,true),options=[...after.paths].filter(([,s])=>s.market===p.market&&s.reasonable&&s.stops===p.stops),using=options.filter(([k])=>k.split('-').includes(String(l.flight)));
   if(markets.has(p.market)&&markets.get(p.market).minutes<=p.minutes)continue;
   markets.set(p.market,{market:p.market,demand:r.demand,minutes:p.minutes,stops:p.stops,newOneStop:a.gap,share:using.length/options.length,oldFastest:a.fastest?.totalMinutes??null});
  }
  const mm=[...markets.values()],competitive=mm.filter(m=>!m.stops||m.newOneStop||m.oldFastest!=null&&m.minutes<=m.oldFastest+30);
  return {flight:l.flight,market:l.origin+'-'+l.destination,departure:l.departure,arrival:l.arrival,localOd:od[l.origin][l.destination],eligibleMarketOd:mm.reduce((s,m)=>s+m.demand,0),competitiveIndex:competitive.reduce((s,m)=>s+m.demand*m.share,0),competitiveMarkets:competitive.sort((a,b)=>b.demand-a.demand)};
 });
 const dsm=[];for(const[k,r]of after.records)if([r.origin,r.destination].includes('DSM')){const old=before.records.get(k),a=coverageView(old,true),b=coverageView(r,true);if(a.stops!==b.stops||a.fastest?.totalMinutes!==b.fastest?.totalMinutes)dsm.push({market:k,demand:r.demand,beforeStops:a.stops,afterStops:b.stops,beforeMinutes:a.fastest?.totalMinutes,afterMinutes:b.fastest?.totalMinutes});}
 results[name]={raw,geo,profiles,dsm:dsm.sort((a,b)=>b.demand-a.demand)};
 if(accepted){
  const decision=read(root+'/config/optimizations/schedule_7_v1_3_1_round_4.json').acceptedDsmOptimization;
  assert.deepEqual(geo.gained.map(x=>x.market).sort(),decision.reviewedOneStopGains.slice().sort());
  assert.equal(raw.lostPaths,0);assert.equal(geo.lostPaths,0);assert.equal(raw.lost.length,0);assert.equal(geo.lost.length,0);assert.equal(geo.faster.length,19);assert.equal(raw.slower.length,0);assert.equal(geo.slower.length,0);
  for(const ne of ['HPN','HVN','ISP','BTV','ORH'])for(const fl of ['PGD','DAB','FLL','PIE','SFB','SRQ'])for(const[a,b]of[[ne,fl],[fl,ne]]){const v=coverageView(after.records.get(a+'-'+b),true);assert.ok(v.stops!=null&&v.stops<=1);}
  const sha=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex');
  results[name].provenance={baselineSha256:sha(checkpoint),canonicalSha256:sha(root+'/data/schedules/schedule_7_v1_3_1_draft/canonical_schedule.json'),demandSha256:sha(root+'/data/reference/airport_od_matrix_consolidated_v2.csv'),status:'Accepted in unpublished draft'};
 }

 console.log(name,JSON.stringify({gains:geo.gained.length,losses:geo.lost.length,faster:geo.faster.length,slower:geo.slower.length,lostOd:geo.lost.reduce((s,m)=>s+m.demand,0),dsmFaster:dsm.filter(m=>m.afterMinutes<m.beforeMinutes).length,dsmSlower:dsm.filter(m=>m.afterMinutes>m.beforeMinutes).length,profiles:profiles.map(p=>({flight:p.flight,index:p.competitiveIndex,local:p.localOd}))}));
 console.log('DSM',JSON.stringify(dsm.slice(0,12)));console.log('LOST',JSON.stringify(geo.lost));
}
fs.writeFileSync(out+(accepted?'/accepted_review.json':'/network_screen'+(picked.length?'_'+picked.join('_'):'')+'.json'),JSON.stringify(results,null,2)+'\n');
