import fs from 'node:fs';import {createHash}from'node:crypto';
import {buildItineraries}from'../web/app.mjs';
import {buildServiceAnalysis,parseAirportDemand,compareServiceAnalyses,coverageView}from'../web/opportunity-analysis.mjs';
import path from 'node:path';import{fileURLToPath}from'node:url';import assert from'node:assert/strict';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),dir=root+'/outputs/schedule_7_v1_3_1_evening';
const raw=fs.readFileSync(root+'/data/schedules/schedule_7_v1_3_1_draft/canonical_schedule.json');const base=JSON.parse(raw),demand=parseAirportDemand(fs.readFileSync(root+'/data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const before=buildServiceAnalysis(base,demand,buildItineraries),results={};
const digest=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex');
assert.equal(digest(root+'/data/reference/airport_od_matrix_consolidated_v2.csv'),'49c04922ee0cebb3fef8aad923e04bd11874587a263c9511358ddb833b860bc6');
const native=JSON.parse(fs.readFileSync(dir+'/native_review.json'));assert.equal(native.baseSha256,createHash('sha256').update(raw).digest('hex'));
for(const name of ['mci','day','bhm','phf']){
 const config=root+'/config/proposals/schedule_7_v1_3_1_evening_'+name+'.json';
 assert.equal(native.alternatives[name].overlaySha256,digest(config));assert.equal(native.alternatives[name].canonicalSha256,digest(dir+'/'+name+'_canonical.json'));
 const c=JSON.parse(fs.readFileSync(dir+'/'+name+'_canonical.json')),after=buildServiceAnalysis(c,demand,buildItineraries),app=compareServiceAnalyses(before,after),geo=compareServiceAnalyses(before,after,true),legs=c.legs.filter(l=>l.flight>=2199);
 const profile=[];
 for(const l of legs){const markets=new Map();
  for(const[k,p]of after.paths){if(!p.reasonable||p.stops>1||!k.split('-').includes(String(l.flight)))continue;
   const r=after.records.get(p.market),old=before.records.get(p.market);if(p.stops===1&&old.counts[0])continue;
   const comparable=[...after.paths].filter(([,s])=>s.market===p.market&&s.reasonable&&s.stops===p.stops),shares=comparable.filter(([s])=>s.split('-').includes(String(l.flight))).length/comparable.length;
   const oldBest=coverageView(old,true).fastest;const row={market:p.market,od:r.demand,minutes:p.minutes,newOneStop:coverageView(old,true).gap,beforeMinutes:oldBest?.totalMinutes??null,equalChoiceShare:shares};
   if(!markets.has(p.market)||markets.get(p.market).minutes>p.minutes)markets.set(p.market,row);
  }
  const values=[...markets.values()].sort((a,b)=>b.od-a.od),competitive=values.filter(m=>m.market===l.origin+'-'+l.destination||m.newOneStop||(m.beforeMinutes!==null&&m.minutes<=m.beforeMinutes+30));
  profile.push({flight:l.flight,origin:l.origin,destination:l.destination,totalUnderlyingMarketOd:values.reduce((s,m)=>s+m.od,0),equalChoiceIndex:values.reduce((s,m)=>s+m.od*m.equalChoiceShare,0),competitiveMarketOd:competitive.reduce((s,m)=>s+m.od,0),competitiveIndex:competitive.reduce((s,m)=>s+m.od*m.equalChoiceShare,0),markets:values,competitive});
 }
 const targets={};for(const key of ['RFD-ROA','ROA-RFD','RFD-ECP','RFD-TLH','RFD-MYR','MYR-RFD'])targets[key]={before:coverageView(before.records.get(key),true),after:coverageView(after.records.get(key),true),app:coverageView(after.records.get(key))};
 results[name]={app,geographic:geo,newChoices:after.paths.size-before.paths.size,flightDemand:profile,targets};
 if(name!=='phf'){assert.equal(app.lostPaths,0);assert.equal(app.lost.length,0);assert.equal(app.slower.length,0);assert.equal(geo.lostPaths,0);assert.equal(geo.lost.length,0);assert.equal(geo.slower.length,0);}
 console.log(name,JSON.stringify({newChoices:results[name].newChoices,newOneStops:app.gained.map(x=>x.market),lostPaths:app.lostPaths,lostCoverage:app.lost,slower:app.slower,faster:app.faster.length,geographicGains:geo.gained.map(x=>x.market),geoSlower:geo.slower,geoFaster:geo.faster.length,profile:profile.map(p=>({flight:p.flight,competitiveIndex:p.competitiveIndex}))}));
}
fs.writeFileSync(dir+'/network_review.json',JSON.stringify({status:'analysis only; accepted draft unchanged',baseSha256:createHash('sha256').update(raw).digest('hex'),alternatives:results,limitations:['O-D and equal-choice indices are opportunity indicators, not forecast passenger loads.','Connecting market demand excludes existing nonstop alternatives and applies a 2.25 distance screen.','Flight market totals overlap and must not be summed as unique passengers.']},null,2)+'\n');
if(!raw.equals(fs.readFileSync(root+'/data/schedules/schedule_7_v1_3_1_draft/canonical_schedule.json')))throw Error('Accepted draft changed');
