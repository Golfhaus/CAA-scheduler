import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {buildItineraries} from '../web/app.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const read=async p=>JSON.parse(await fs.readFile(path.join(root,p),'utf8'));
const base=await read('data/schedules/schedule_7_v1_3_0_draft/canonical_schedule.json');
const screen=await read('outputs/schedule_7_v1_3_0_r307_day/screen.json');
if(createHash('sha256').update(await fs.readFile(path.join(root,'data/schedules/schedule_7_v1_3_0_draft/canonical_schedule.json'))).digest('hex')!==screen.baseSha256)throw Error('Stale DAY timing screen');
const hubs=new Set([...base.operatingPolicy.hubs,...base.operatingPolicy.focusCities]);
const cities=Object.fromEntries(base.cities.filter(c=>c.active).map(c=>[c.code,c]));
const tz=Object.fromEntries(Object.entries(cities).map(([k,c])=>[k,c.timezone]));
const rows=(await fs.readFile(path.join(root,'data/reference/airport_od_matrix_consolidated_v2.csv'),'utf8')).split(/\r?\n/).map(x=>x.split(','));
const header=rows.findIndex(r=>r[0]==='Origin \\ Dest'),codes=rows[header].slice(1),od={};
for(const r of rows.slice(header+1))if(cities[r[0]])od[r[0]]=Object.fromEntries(codes.map((b,i)=>[b,r[i+1]?.trim()?Number(r[i+1]):null]));
const rad=x=>x*Math.PI/180,distances=new Map();
const distance=(a,b)=>{const key=a+'-'+b;if(distances.has(key))return distances.get(key);const x=cities[a],y=cities[b];const h=Math.sin(rad(y.latitude-x.latitude)/2)**2+Math.cos(rad(x.latitude))*Math.cos(rad(y.latitude))*Math.sin(rad(y.longitude-x.longitude)/2)**2;const d=3440.065*2*Math.atan2(Math.sqrt(h),Math.sqrt(1-h));distances.set(key,d);return d;};
const clock=m=>`${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`;
const nextFlight=Math.max(...base.legs.map(l=>l.flight))+1;
const original=base.legs.map(l=>({origin:l.origin,dest:l.destination,dep:l.departure,arr:l.arrival,flight:l.flight,fleet:l.fleet}));
const newOut=t=>({origin:'PIT',dest:'DAY',dep:clock(t.departure),arr:clock(t.arrival),flight:nextFlight,fleet:'CRJ700'});
const newBack=t=>({origin:'DAY',dest:'PIT',dep:clock(t.back),arr:clock(t.returnArrival),flight:nextFlight+1,fleet:'CRJ700'});
function scan(extra=[],side='both',geographic=true){
 const tt={flights:[...original,...extra],minConnect:30,maxConnect:240},result=new Map();
 const origins=side==='out'?['PIT']:Object.keys(cities);
 for(const a of origins)for(const p of buildItineraries(tt,a,hubs,tz)){
  if(a!=='PIT'&&p.dest!=='PIT')continue;
  if(side==='in'&&p.dest!=='PIT')continue;
  const ratio=p.legs.reduce((s,l)=>s+distance(l.origin,l.dest),0)/distance(a,p.dest);
  if(geographic&&p.stops&&ratio>2.25+1e-10)continue;
  const market=a+'-'+p.dest;
  if(!result.has(market))result.set(market,[]);
  result.get(market).push({...p,origin:a,circuity:ratio});
 }
 return result;
}
const best=options=>options?.reduce((a,b)=>!a||b.totalMinutes<a.totalMinutes?b:a,null)||null;
const brief=p=>p?{flights:p.legs.map(l=>l.flight),airports:[p.origin,...p.legs.map(l=>l.dest)],departure:p.legs[0].dep,arrival:p.legs.at(-1).arr,minutes:p.totalMinutes,stops:p.stops,waits:p.waits,circuity:p.circuity}:null;
const baseline=scan(),outCache=new Map(),inCache=new Map();
function compare(now,oldBaseline=baseline){
 const changes=[];let score=0,gapDemand=0;
 for(const [market,options] of now){
  const old=oldBaseline.get(market),oldBest=best(old),newBest=best(options);
  const oldOne=best(old?.filter(p=>p.stops<=1)),newOne=best(options.filter(p=>p.stops<=1));
  const [a,b]=market.split('-'),demand=od[a][b];
  const gain=oldBest?oldBest.totalMinutes-newBest.totalMinutes:null;
  if(gain>0)score+=(demand??0)*gain;
  if(!oldOne&&newOne)gapDemand+=demand??0;
  if(gain>0||!oldOne&&newOne)changes.push({market,demand,newOneStopCoverage:!oldOne&&!!newOne,minutesSaved:gain,oldFastest:brief(oldBest),newFastest:brief(newBest),oldOneStop:brief(oldOne),newOneStop:brief(newOne)});
 }
 return {weightedMinutesSaved:score,newOneStopUnderlyingOd:gapDemand,changes:changes.sort((a,b)=>(b.demand??-1)-(a.demand??-1))};
}
const ranks=[];
for(const t of screen.candidates){
 if(!outCache.has(t.departure))outCache.set(t.departure,scan([newOut(t)],'out'));
 if(!inCache.has(t.back))inCache.set(t.back,scan([newBack(t)],'in'));
 const now=new Map([...outCache.get(t.departure),...inCache.get(t.back)]),m=compare(now);
 const bhm=best(now.get('PIT-BHM')?.filter(p=>p.stops<=1));
 if(!bhm)throw Error('Candidate does not enable PIT-BHM');
 ranks.push({...t,weightedMinutesSaved:m.weightedMinutesSaved,newOneStopUnderlyingOd:m.newOneStopUnderlyingOd,bhmMinutes:bhm.totalMinutes});
}
const byGain=[...ranks].sort((a,b)=>b.weightedMinutesSaved-a.weightedMinutesSaved||a.bhmMinutes-b.bhmMinutes);
const byBhm=[...ranks].sort((a,b)=>a.bhmMinutes-b.bhmMinutes||b.weightedMinutesSaved-a.weightedMinutesSaved);
const selected={best_time_gain:byGain[0],shortest_bhm:byBhm[0]};
const keyDeparture=Math.min(...base.legs.filter(l=>[1363,1538,1460].includes(l.flight)).map(l=>l.departureMinute));
selected.buffered=byGain.find(t=>t.groundMinutes.every(n=>n>=45)&&keyDeparture-t.arrival>=35);
if(!selected.buffered)throw Error('No buffered candidate');
const morningBhm=base.legs.find(l=>l.flight===2070);
selected.two_way_bhm=byGain.find(t=>t.back-morningBhm.arrivalMinute>=30&&t.back-morningBhm.arrivalMinute<=240);
if(!selected.two_way_bhm)throw Error('No two-way BHM candidate');
const comparisons={};
for(const [name,t] of Object.entries(selected)){
 const now=scan([newOut(t),newBack(t)]),m=compare(now);
 const appBefore=scan([], 'both',false),appAfter=scan([newOut(t),newBack(t)],'both',false);
 const pathSet=map=>new Set([...map.values()].flatMap(rows=>rows.map(p=>p.legs.map(l=>l.flight).join(','))));
 const beforePaths=pathSet(appBefore),afterPaths=pathSet(appAfter);
 const lostCoverage=[...appBefore].filter(([k,v])=>v.some(p=>p.stops<=1)&&!appAfter.get(k)?.some(p=>p.stops<=1)).map(([k])=>k);
 const slower=[...appBefore].filter(([k,v])=>appAfter.has(k)&&best(appAfter.get(k)).totalMinutes>best(v).totalMinutes).map(([k])=>k);
 const bhm=best(now.get('PIT-BHM')?.filter(p=>p.stops<=1));
 const reverse=best(now.get('BHM-PIT')?.filter(p=>p.stops<=1));
 const dayReverse=best(now.get('BHM-PIT')?.filter(p=>p.stops===1&&p.legs.some(l=>l.flight===nextFlight+1)));
 comparisons[name]={...m,appChanges:compare(appAfter,appBefore).changes,bhm:brief(bhm),reverseBhm:brief(reverse),reverseBhmViaDay:brief(dayReverse),lostDirectOneStopCoverage:lostCoverage,slowerFastestMarkets:slower,displacedAppChoices:[...beforePaths].filter(k=>!afterPaths.has(k)).length,newAppChoices:[...afterPaths].filter(k=>!beforePaths.has(k)).length,newOutFlight:nextFlight,newBackFlight:nextFlight+1};
 console.log(name,JSON.stringify({timing:t,bhm:brief(bhm),newAppChoices:comparisons[name].newAppChoices,displacedAppChoices:comparisons[name].displacedAppChoices,lostCoverage,slower,changes:m.changes.map(x=>({market:x.market,demand:x.demand,newOneStop:x.newOneStopCoverage,before:x.oldFastest?.minutes??null,after:x.newFastest?.minutes,saved:x.minutesSaved,stops:x.newFastest.stops}))}));
}
await fs.writeFile(path.join(root,'outputs/schedule_7_v1_3_0_r307_day/connection_review.json'),JSON.stringify({baseSha256:screen.baseSha256,status:'analysis only; not accepted',rankingMethod:'Exhaustive 210 bank/turn-feasible timings; rank by pinned O-D multiplied by fastest elapsed minutes saved, with a separate shortest-BHM option. This is a timing comparison, not forecast traffic allocation.',selected,comparisons,ranks:byGain},null,2)+'\n');
