import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis,parseAirportDemand,coverageView,compareServiceAnalyses} from '../web/opportunity-analysis.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const read=p=>JSON.parse(fs.readFileSync(root+'/'+p,'utf8'));
const sha=p=>createHash('sha256').update(fs.readFileSync(root+'/'+p)).digest('hex');
const source='data/schedules/schedule_7_v1_3_1_draft/canonical_schedule.json',baseline='outputs/schedule_7_v1_3_1_ne_service/base_round_2_canonical.json';
const config=read('config/optimizations/schedule_7_v1_3_1_round_3.json'),decision=config.acceptedNortheastService;
assert.equal(sha(baseline),decision.sourceDraftSha256);
assert.equal(sha('data/reference/airport_od_matrix_consolidated_v2.csv'),'49c04922ee0cebb3fef8aad923e04bd11874587a263c9511358ddb833b860bc6');
const old=read(baseline),now=read(source),od=parseAirportDemand(fs.readFileSync(root+'/data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const before=buildServiceAnalysis(old,od,buildItineraries),after=buildServiceAnalysis(now,od,buildItineraries);
const raw=compareServiceAnalyses(before,after),geo=compareServiceAnalyses(before,after,true);
assert.deepEqual(raw.lost.map(x=>x.market).sort(),decision.reviewedRawCoverageLosses.slice().sort());
assert.deepEqual(geo.lost.map(x=>x.market).sort(),decision.reviewedGeographicCoverageLosses.slice().sort());
const flp=now.cities.filter(c=>c.active&&c.group==='FLP').map(c=>c.code),rows=[];
for(const ne of decision.northeast)for(const fl of flp)for(const [a,b]of[[ne,fl],[fl,ne]]){
 const key=a+'-'+b,prior=before.records.get(key),r=after.records.get(key),rawView=coverageView(r),geoView=coverageView(r,true);
 const row={market:key,origin:a,destination:b,demand:r.demand,beforeMinimumConnections:coverageView(prior).stops,minimumConnections:rawView.stops,geographicMinimumConnections:geoView.stops,bestOneStop:rawView.best[1]??null,beforeFastestMinutes:coverageView(prior,true).fastest?.totalMinutes??null,afterFastestMinutes:geoView.fastest?.totalMinutes??null};
 if(['PGD','DAB'].includes(fl)){assert.equal(row.minimumConnections,1,key);assert.equal(row.geographicMinimumConnections,1,key);assert.ok(row.bestOneStop);}
 if(['FLL','PIE','SFB','SRQ'].includes(fl)){assert.ok(rawView.stops!=null&&rawView.stops<=1,key);assert.ok(geoView.stops!=null&&geoView.stops<=1,key);}
 if(['EYW','GNV','MLB'].includes(fl))assert.ok(row.minimumConnections==null||row.minimumConnections>=2,key);
 rows.push(row);
}
const priority=rows.filter(r=>['PGD','DAB'].includes(r.origin)||['PGD','DAB'].includes(r.destination));assert.equal(priority.length,20);
const changed=[];for(const l of now.legs){const previous=old.legs.find(p=>p.id===l.id);if(previous&&(previous.departureMinute!==l.departureMinute||previous.arrivalMinute!==l.arrivalMinute))changed.push({flight:l.flight,market:l.origin+'-'+l.destination,beforeDeparture:previous.departure,beforeArrival:previous.arrival,departure:l.departure,arrival:l.arrival,beforeRoute:previous.route,route:l.route});}
assert.equal(changed.length,13);
const added=now.legs.filter(l=>!old.legs.some(p=>p.id===l.id));assert.equal(added.length,14);
const report={status:'Accepted into unpublished v1.3.1 draft',date:'2026-10-13',sourceCanonical:source,sourceSha256:sha(source),beforeCanonical:baseline,beforeSha256:sha(baseline),sourceDraftCommit:decision.sourceDraftCommit,demandSha256:sha('data/reference/airport_od_matrix_consolidated_v2.csv'),priorityDemand:priority.reduce((n,r)=>n+r.demand,0),priorityDirectionsCovered:20,retainedExistingNortheastFloridaDirections:40,remainingOtherFlpGapDirections:rows.filter(r=>['EYW','GNV','MLB'].some(c=>r.origin===c||r.destination===c)&&(r.minimumConnections==null||r.minimumConnections>=2)).length,priorityConnections:priority,rows,addedFlights:added,changedOriginalClocks:changed.sort((a,b)=>a.flight-b.flight),comparison:{app:raw,geographic:geo},coverageLossUnderlyingOd:{app:raw.lost.reduce((n,r)=>n+r.demand,0),geographic:geo.lost.reduce((n,r)=>n+r.demand,0)},demandProfiles:read('data/schedules/schedule_7_v1_3_1_draft/connection_review.json').flightDemandProfiles.filter(p=>p.flight>=2201),decisions:decision,limitations:['O-D values and opportunity indices measure eligible markets, not bookings, aircraft loads or proven profitability.','Every flight uses the pinned CRJ700 block-time model; no new bank, connection-window, curfew, fleet or physical-inventory waiver is introduced. Existing approved useful-hub exceptions remain in force for PGD and DAB.','This is a deliberate coverage tradeoff: all original flight IDs and fleets remain, but 13 clocks and named same-fleet round-trip assignments change. Slower fastest journeys and lost options are reported without claiming a regression-free network.','Some new one-stop itineraries are slower than retained two-stop choices. Both are available.','EYW, GNV and MLB need new service rather than trivial adjustments; that expansion is not included.']};
const out=root+'/outputs/schedule_7_v1_3_1_ne_service';fs.mkdirSync(out,{recursive:true});fs.writeFileSync(out+'/service_review.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({priorityDemand:report.priorityDemand,priorityDirectionsCovered:20,remainingOtherFlpGapDirections:report.remainingOtherFlpGapDirections,addedFlights:14,changedOriginalClocks:13,raw:{gained:raw.gained.length,lost:raw.lost.length,faster:raw.faster.length,slower:raw.slower.length,lostPaths:raw.lostPaths},geographic:{gained:geo.gained.length,lost:geo.lost.length,faster:geo.faster.length,slower:geo.slower.length,lostPaths:geo.lostPaths},lostCoverageOd:report.coverageLossUnderlyingOd}));
for(const r of priority)console.log(r.market,r.demand,r.bestOneStop.totalMinutes,r.bestOneStop.legs.map(l=>l.flight));
