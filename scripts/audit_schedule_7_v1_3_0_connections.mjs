import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {buildItineraries} from '../web/app.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const load=async p=>JSON.parse(await fs.readFile(path.join(root,p),'utf8'));
const base=await load('data/schedules/schedule_7_v1_3_0_draft/canonical_schedule.json');
const released=await load('data/schedules/schedule_7_v1_2_5/canonical_schedule.json');
const hubs=new Set([...base.operatingPolicy.hubs,...base.operatingPolicy.focusCities]);
const cities=Object.fromEntries(base.cities.map(c=>[c.code,c]));
const tz=Object.fromEntries(base.cities.map(c=>[c.code,c.timezone]));
const codes=base.cities.filter(c=>c.active).map(c=>c.code);
const rad=x=>x*Math.PI/180;
const distance=(a,b)=>{const c=cities[a],d=cities[b];const t=Math.sin(rad(d.latitude-c.latitude)/2)**2+Math.cos(rad(c.latitude))*Math.cos(rad(d.latitude))*Math.sin(rad(d.longitude-c.longitude)/2)**2;return 3440.065*2*Math.atan2(Math.sqrt(t),Math.sqrt(1-t));};
const csv=(await fs.readFile(path.join(root,'data/reference/airport_od_matrix_consolidated_v2.csv'),'utf8')).split(/\r?\n/);const hi=csv.findIndex(l=>l.startsWith('Origin \\ Dest,'));const cc=csv[hi].split(',').slice(1),od={};for(const l of csv.slice(hi+1).filter(Boolean)){const [a,...v]=l.split(',');od[a]=Object.fromEntries(cc.map((b,i)=>[b,Number(v[i]||0)]));}
function scan(c,geographic=false){const tt={minConnect:30,maxConnect:240,flights:c.legs.map(l=>({origin:l.origin,dest:l.destination,dep:l.departure,arr:l.arrival,flight:l.flight,fleet:l.fleet}))};const map=new Map(),best=new Map(),one=new Set();for(const a of codes)for(const p of buildItineraries(tt,a,hubs,tz)){if(geographic&&p.stops&&p.legs.reduce((s,l)=>s+distance(l.origin,l.dest),0)/distance(a,p.dest)>2.25+1e-10)continue;const key=a+'-'+p.dest;map.set(p.legs.map(l=>l.flight).join(','),{a,b:p.dest,minutes:p.totalMinutes,stops:p.stops});if(!best.has(key)||best.get(key)>p.totalMinutes)best.set(key,p.totalMinutes);if(p.stops<=1)one.add(key);}return{map,best,one};}
function compare(old,now){const lost=[...old.map].filter(([k])=>!now.map.has(k));return{lostChoices:lost.length,lostMarkets:[...old.best.keys()].filter(k=>!now.best.has(k)),lostOneStopMarkets:[...old.one].filter(k=>!now.one.has(k)),newOneStopMarkets:[...now.one].filter(k=>!old.one.has(k)),lostChoiceMarkets:[...new Set(lost.map(([,p])=>p.a+'-'+p.b))].map(k=>{const [a,b]=k.split('-');return{market:k,od:od[a][b]};}),slowerFastest:[...old.best].filter(([k,t])=>now.best.has(k)&&now.best.get(k)>t).map(([k,t])=>{const[a,b]=k.split('-');return{market:k,oldMinutes:t,newMinutes:now.best.get(k),od:od[a][b]};}),fasterFastest:[...old.best].filter(([k,t])=>now.best.has(k)&&now.best.get(k)<t).length};}
const accepted=compare(scan(released),scan(base));
await fs.writeFile(path.join(root,'data/schedules/schedule_7_v1_3_0_draft/connection_review.json'),JSON.stringify(accepted,null,2)+'\n');
const directory='outputs/schedule_7_v1_3_0_shared_hub_gaps';
const old=scan(base),oldGeo=scan(base,true);const results={};
for(const name of ['pgd_cak_2','blv_hou_6','oma_bna_11','bna_oma_both','rfd_myr_2_flights','myr_rfd_both_new_bank']){
 const c=await load(directory+'/'+name+'.json'),now=scan(c),nowGeo=scan(c,true);
 const all=compare(old,now),geo=compare(oldGeo,nowGeo);
 const targets={};for(const[a,b]of[['CAK','PGD'],['PGD','CAK'],['BLV','HOU'],['HOU','BLV'],['MYR','RFD'],['RFD','MYR'],['BNA','OMA'],['OMA','BNA']])targets[a+'-'+b]=[...nowGeo.map].filter(([k,p])=>p.a===a&&p.b===b&&p.stops<=1).map(([flights,p])=>({flights,...p}));
 results[name]={app:all,geographic:geo,targets};
 console.log(name,JSON.stringify({lostChoices:all.lostChoices,lostOneStopMarkets:all.lostOneStopMarkets,newOneStopMarkets:all.newOneStopMarkets,slowerCount:all.slowerFastest.length,slowerPositiveOd:all.slowerFastest.filter(p=>p.od>0).length,lostMarkets:all.lostMarkets,targets}));
 await fs.writeFile(path.join(root,directory+'/connection_review.json'),JSON.stringify(results,null,2)+'\n');
}
