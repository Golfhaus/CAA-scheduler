import fs from 'node:fs';
import {buildItineraries} from '../web/app.mjs';
import {buildServiceAnalysis,parseAirportDemand,compareServiceAnalyses,coverageView} from '../web/opportunity-analysis.mjs';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const root='outputs/schedule_7_v1_3_3_pie_review';
const base=read('data/schedules/schedule_7_v1_3_2/canonical_schedule.json');
const od=parseAirportDemand(fs.readFileSync('data/reference/airport_od_matrix_consolidated_v2.csv','utf8'));
const old=buildServiceAnalysis(base,od,buildItineraries);
const native=read(root+'/r514_physical_screen.json');
const selected=['PIE-IND','PIE-AUS','PIE-BLV','PIE-GRR','GRR-PIE'];
const report={base:'released v1.3.2',publication:'not authorized',results:{}};
const groupKey=(a)=>a.map(x=>x.market);
for(const [scenario,check] of Object.entries(native)){
 if(!check.pass)continue;
 const current=read(root+'/'+scenario+'_canonical.json'),now=buildServiceAnalysis(current,od,buildItineraries);
 const geo=compareServiceAnalyses(old,now,true),raw=compareServiceAnalyses(old,now,false);
 const marketChanges={};
 for(const k of selected){
  const a=old.records.get(k),b=now.records.get(k);
  const x=coverageView(a,true),y=coverageView(b,true);
  marketChanges[k]={demand:b.demand,oldStops:x.stops,newStops:y.stops,oldFastest:x.fastest?.totalMinutes??null,newFastest:y.fastest?.totalMinutes??null,
   oldReasonableCounts:x.counts,newReasonableCounts:y.counts,
   bestRoute:y.best.filter(Boolean).sort((p,q)=>p.stops-q.stops||p.totalMinutes-q.totalMinutes).slice(0,3).map(q=>({flights:q.legs.map(l=>l.flight),route:q.legs.map(l=>l.origin).join('→')+'→'+q.dest,waits:q.waits,minutes:q.totalMinutes}))};
 }
 const lost=geo.lost.map(x=>({market:x.market,demand:x.demand,previous:x.beforeMinutes,after:x.afterMinutes}));
 const highLoss=geo.lost.filter(x=>x.demand>=5).map(x=>x.market);
 report.results[scenario]={markets:marketChanges,geo:{gains:geo.gained.length,losses:lost,faster:geo.faster.length,slower:geo.slower.length,lostPaths:geo.lostPaths,
 highDemandLost:highLoss,largestSlower:geo.slower.slice().sort((a,b)=>b.demand-a.demand).slice(0,15)},raw:{gains:raw.gained.length,losses:raw.lost.length},removed:[1230,1227],flights:current.legs.length};
 console.log(scenario,JSON.stringify({targets:Object.fromEntries(Object.entries(marketChanges).map(([k,v])=>[k,[v.oldStops,v.newStops,v.oldFastest,v.newFastest]])),gains:geo.gained.length,losses:lost,faster:geo.faster.length,slower:geo.slower.length,highLoss}));
}
fs.writeFileSync(root+'/r514_network_screen.json',JSON.stringify(report,null,2)+'\n');
