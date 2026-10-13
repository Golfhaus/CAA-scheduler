import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis,parseAirportDemand,coverageView,compareServiceAnalyses} from '../web/opportunity-analysis.mjs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const digest=p=>createHash('sha256').update(fs.readFileSync(root+'/'+p)).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(root+'/'+p,'utf8'));
const base=read('data/schedules/schedule_7_v1_3_0/canonical_schedule.json'),now=read('data/schedules/schedule_7_v1_3_1_draft/canonical_schedule.json');
const od=parseAirportDemand(fs.readFileSync(root+'/data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const config=read('config/optimizations/schedule_7_v1_3_1_round_3.json');
assert.equal(digest(config.baseSchedule.canonical),config.baseSchedule.sha256);
assert.equal(digest('data/reference/airport_od_matrix_consolidated_v2.csv'),'49c04922ee0cebb3fef8aad923e04bd11874587a263c9511358ddb833b860bc6');
assert.equal(read('web/schedules.json').defaultScheduleId,'schedule_7_v1_3_0');
const before=buildServiceAnalysis(base,od,buildItineraries),after=buildServiceAnalysis(now,od,buildItineraries);
const raw=compareServiceAnalyses(before,after),geo=compareServiceAnalyses(before,after,true);
const targets={};for(const code of ['MYR','EYW','ECP','ILM','ROA','TLH'])for(const [a,b]of[[code,'RFD'],['RFD',code]]){const r=after.records.get(a+'-'+b);targets[r.key]={demand:r.demand,before:coverageView(before.records.get(r.key),true),after:coverageView(r,true)};}
const added=now.legs.filter(l=>!base.legs.some(b=>b.id===l.id)),profile=[];
assert.equal(added.length,20);assert.deepEqual(added.map(l=>l.flight),Array.from({length:20},(_,i)=>2195+i));
for(const l of added){
 const markets=new Map();
 for(const [key,p]of after.paths){if(!p.reasonable||p.stops>1||!key.split('-').includes(String(l.flight)))continue;
 const r=after.records.get(p.market),old=before.records.get(p.market);
 if(p.stops===1&&old.counts[0])continue; // protect already served nonstop traffic from a connection claim
 const bestOld=coverageView(old,true).fastest;
 const marginal=coverageView(old,true).gap;
 const newBest=coverageView(r,true).fastest;
 const entries=[...after.paths].filter(([,s])=>s.market===p.market&&s.reasonable&&s.stops===p.stops);
 const flightEntries=entries.filter(([k])=>k.split('-').includes(String(l.flight)));
 if(markets.has(p.market)&&markets.get(p.market).minutes<=p.minutes)continue;
 markets.set(p.market,{market:p.market,demand:r.demand,stops:p.stops,minutes:p.minutes,existingOneStop:!marginal,oldFastestMinutes:bestOld?.totalMinutes??null,newFastestMinutes:newBest?.totalMinutes??null,equalChoiceShare:flightEntries.length/entries.length,newOneStop:marginal,group:after.cities.get(l.origin==='RFD'?r.destination:r.origin).group});
 }
 const mm=[...markets.values()].sort((a,b)=>b.demand-a.demand);
 const competitive=mm.filter(m=>m.stops===0||m.newOneStop||(m.oldFastestMinutes!=null&&m.minutes<=m.oldFastestMinutes+30));
 profile.push({competitiveMarketOd:competitive.reduce((s,m)=>s+m.demand,0),competitiveEqualChoiceIndex:competitive.reduce((s,m)=>s+m.demand*m.equalChoiceShare,0),flight:l.flight,origin:l.origin,destination:l.destination,departure:l.departure,arrival:l.arrival,uniqueMarkets:mm.length,underlyingMarketOd:mm.reduce((s,m)=>s+m.demand,0),newOneStopOd:mm.filter(m=>m.newOneStop).reduce((s,m)=>s+m.demand,0),equalChoiceOpportunityIndex:mm.reduce((s,m)=>s+m.demand*m.equalChoiceShare,0),markets:mm});
}
assert.deepEqual(raw.lost.map(x=>x.market).sort(),config.acceptedNortheastService.reviewedRawCoverageLosses.slice().sort());
assert.deepEqual(geo.lost.map(x=>x.market).sort(),config.acceptedNortheastService.reviewedGeographicCoverageLosses.slice().sort());
for(const ne of config.acceptedNortheastService.northeast)for(const fl of ['PGD','DAB','FLL','PIE','SFB','SRQ'])for(const [a,b]of[[ne,fl],[fl,ne]]){
 const r=after.records.get(a+'-'+b);assert.ok(coverageView(r).stops<=1&&coverageView(r).stops!=null,a+'-'+b);
 assert.ok(coverageView(r,true).stops<=1&&coverageView(r,true).stops!=null,'Geographic '+a+'-'+b);
}

for(const [k,t]of Object.entries(targets)) {assert.equal(t.after.counts[1]>0,!k.includes('ROA'));assert.ok(after.records.get(k).counts[1]>0);}
const newOpportunityMarkets=new Map(profile.flatMap(p=>p.markets.filter(m=>m.stops===0||m.newOneStop).map(m=>[m.market,m.demand])));
const out={baseCanonicalSha256:digest(config.baseSchedule.canonical),draftCanonicalSha256:digest('data/schedules/schedule_7_v1_3_1_draft/canonical_schedule.json'),demandSha256:digest('data/reference/airport_od_matrix_consolidated_v2.csv'),newChoices:after.paths.size-before.paths.size,uniqueLocalAndNewOneStopMarketOd:[...newOpportunityMarkets.values()].reduce((a,b)=>a+b,0),baseScheduleId:base.schedule.id,draftScheduleId:now.schedule.id,app:raw,geographic:geo,targets,flightDemandProfiles:profile,limitations:['Pinned directional O-D is already dampened for secondary airports. It is market size, not booked passengers or a load forecast.','Connection opportunity excludes markets already served nonstop, screens circuity at 2.25, and deduplicates each market within a flight.','This round has reviewed coverage and elapsed-time tradeoffs; it does not claim zero network regressions.','Underlying market totals across flights overlap; do not sum them as unique passengers. The competitive subset retains nonstop/new one-stop markets and options no more than 30 minutes slower than the prior fastest trip. This is a screening heuristic. The equal-choice index divides market demand across available options of the same stop count, without modeling booking preference or competitor capture.']};
fs.writeFileSync(root+'/data/schedules/schedule_7_v1_3_1_draft/connection_review.json',JSON.stringify(out,null,2)+'\n');
console.log('APP',JSON.stringify({lostPaths:raw.lostPaths,gained:raw.gained.length,lost:raw.lost.length,faster:raw.faster.length,slower:raw.slower.length,newChoices:after.paths.size-before.paths.size}));
console.log('GEO',JSON.stringify({lostPaths:geo.lostPaths,gained:geo.gained.length,lost:geo.lost.length,faster:geo.faster.length,slower:geo.slower.length}));
for(const [k,t]of Object.entries(targets)){const best=t.after.best[1];console.log(k,t.demand,after.records.get(k).best[1]?.totalMinutes,after.records.get(k).best[1]?.legs.map(x=>x.flight),'geographic',!!best)}
for(const p of profile)console.log('DEMAND',p.flight,p.uniqueMarkets,p.underlyingMarketOd,p.newOneStopOd,p.equalChoiceOpportunityIndex,'competitiveIndex',p.competitiveEqualChoiceIndex);

