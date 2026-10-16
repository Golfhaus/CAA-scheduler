import fs from 'node:fs';import assert from 'node:assert/strict';import {createHash}from'node:crypto';import path from 'node:path';import {fileURLToPath}from'node:url';
import {buildItineraries}from'../web/app.mjs';import {buildServiceAnalysis,parseAirportDemand,compareServiceAnalyses,coverageView}from'../web/opportunity-analysis.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),out=root+'/outputs/schedule_7_v1_3_2_maintenance';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));const base=read(root+'/data/schedules/schedule_7_v1_3_1/canonical_schedule.json'),od=parseAirportDemand(fs.readFileSync(root+'/data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const accepted=process.argv.includes('--accepted');
const before=buildServiceAnalysis(base,od,buildItineraries),native=accepted?{accepted:{valid:true}}:read(out+'/native_review.json'),reports={};
for(const name of Object.keys(native)){
 if(!native[name].valid)continue;
 const c=read(accepted?root+'/data/schedules/schedule_7_v1_3_2_draft/canonical_schedule.json':out+'/'+name+'_canonical.json'),after=buildServiceAnalysis(c,od,buildItineraries),raw=compareServiceAnalyses(before,after),geo=compareServiceAnalyses(before,after,true);
 const targets=[];for(const ne of ['HPN','HVN','ISP','BTV','ORH'])for(const fl of ['PGD','DAB','FLL','PIE','SFB','SRQ'])for(const[a,b]of[[ne,fl],[fl,ne]]){const v=coverageView(after.records.get(a+'-'+b),true);if(v.stops==null||v.stops>1)targets.push(a+'-'+b);}
 reports[name]={raw,geo,priorityCoverageLosses:targets,newChoices:after.paths.size-before.paths.size};
 if(accepted){
  assert.equal(raw.lostPaths,23);assert.equal(geo.lostPaths,18);assert.deepEqual(raw.lost.map(x=>x.market),['OMA-PHF']);assert.deepEqual(geo.lost.map(x=>x.market),['OMA-PHF']);assert.deepEqual(targets,[]);
  for(const [key,p]of before.paths)if(!after.paths.has(key))assert.ok(['1257','1258','1360','1991-1521'].includes(key)||key==='1991-1928'||key.startsWith('1991-1928-'),key);
  const approvedChs={'CHS-SFB':170,'SFB-CHS':234};
  assert.ok(geo.slower.every(x=>approvedChs[x.market]===x.afterMinutes||[1,43].includes(x.afterMinutes-x.beforeMinutes)||x.origin==='ISP'&&x.afterMinutes-x.beforeMinutes===8||['RDU','MYR','ILM'].includes(x.origin)&&x.destination==='BWI'&&x.afterMinutes-x.beforeMinutes===2||x.origin==='OMA'&&x.afterMinutes-x.beforeMinutes===26||x.market==='DAB-BDL'&&x.afterMinutes-x.beforeMinutes===71));
  const prior=buildServiceAnalysis(read(root+'/outputs/schedule_7_v1_3_2_r175/base_round_2_canonical.json'),od,buildItineraries),round3=buildServiceAnalysis(read(root+'/outputs/schedule_7_v1_3_2_r125/base_round_3_canonical.json'),od,buildItineraries),r175Raw=compareServiceAnalyses(prior,round3),r175Geo=compareServiceAnalyses(prior,round3,true);
  assert.equal(r175Raw.lostPaths,0);assert.equal(r175Geo.lostPaths,0);assert.deepEqual(r175Geo.lost,[]);
  assert.equal(r175Geo.faster.length,15);assert.equal(r175Geo.slower.length,22);
  assert.ok(r175Geo.slower.every(x=>x.origin==='ISP'&&x.afterMinutes-x.beforeMinutes===8));
  for(const market of ['PWM-BWI','BWI-PWM'])assert.equal(coverageView(after.records.get(market),true).stops,0);
  reports[name].r175Impact={raw:r175Raw,geo:r175Geo};
  const round4=buildServiceAnalysis(read(root+'/outputs/schedule_7_v1_3_2_r111_r312/base_round_4_canonical.json'),od,buildItineraries);
  const r125Raw=compareServiceAnalyses(round3,round4),r125Geo=compareServiceAnalyses(round3,round4,true);
  assert.equal(r125Raw.lostPaths,0);assert.equal(r125Geo.lostPaths,0);assert.deepEqual(r125Geo.lost,[]);
  assert.equal(r125Geo.faster.length,2);assert.equal(r125Geo.slower.length,3);
  assert.ok(r125Geo.slower.every(x=>['RDU','MYR','ILM'].includes(x.origin)&&x.destination==='BWI'&&x.afterMinutes-x.beforeMinutes===2));
  for(const market of ['PVD-BWI','BWI-PVD'])assert.equal(coverageView(after.records.get(market),true).fastest.totalMinutes,73);
  reports[name].r125Impact={raw:r125Raw,geo:r125Geo};
  const addedRaw=compareServiceAnalyses(round4,after),addedGeo=compareServiceAnalyses(round4,after,true);
  assert.equal(addedRaw.lostPaths,21);assert.equal(addedGeo.lostPaths,16);
  assert.deepEqual(addedGeo.lost.map(x=>x.market),['OMA-PHF']);
  assert.equal(addedGeo.faster.length,26);assert.equal(addedGeo.slower.length,17);
  assert.ok(addedGeo.slower.every(x=>x.origin==='OMA'&&x.afterMinutes-x.beforeMinutes===26||x.market==='DAB-BDL'&&x.beforeMinutes===157&&x.afterMinutes===228));
  for(const market of ['PIE-OKC','PIE-TUL','DAB-BNA','DAB-ILM','DAB-ROA'])assert.equal(coverageView(after.records.get(market),true).stops,1);
  for(const [market,minutes]of [['DAB-PVD',266],['DAB-BWI',206],['DAB-BNA',285],['DAB-BDL',228]])assert.equal(coverageView(after.records.get(market),true).fastest.totalMinutes,minutes);
  const connecting=after.canonical.legs.find(l=>l.flight===2225);
  assert.equal(connecting.arrival,'19:40');
  for(const flight of [1284,1292,1929,2171,1203])assert.ok(after.paths.get('2225-'+flight)?.reasonable,'Missing approved bank connection '+flight);
  reports[name].r111R312Impact={raw:addedRaw,geo:addedGeo};
  const sha=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex');
  reports[name].provenance={baseSha256:sha(root+'/data/schedules/schedule_7_v1_3_1/canonical_schedule.json'),draftSha256:sha(root+'/data/schedules/schedule_7_v1_3_2_draft/canonical_schedule.json'),demandSha256:sha(root+'/data/reference/airport_od_matrix_consolidated_v2.csv')};
 }

 console.log(name,JSON.stringify({raw:{lostPaths:raw.lostPaths,gained:raw.gained.length,lost:raw.lost.length,faster:raw.faster.length,slower:raw.slower.length},geo:{lostPaths:geo.lostPaths,gained:geo.gained.length,lost:geo.lost.length,faster:geo.faster.length,slower:geo.slower.length},priorityLosses:targets}));
 console.log('LOSSES',JSON.stringify(geo.lost));console.log('SLOWER',JSON.stringify(geo.slower.slice(0,12)));
}
fs.writeFileSync(accepted?root+'/data/schedules/schedule_7_v1_3_2_draft/connection_review.json':out+'/network_review.json',JSON.stringify(reports,null,2)+'\n');
