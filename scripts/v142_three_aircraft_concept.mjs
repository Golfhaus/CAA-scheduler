import {readFileSync,writeFileSync,mkdirSync} from "node:fs";
import {buildItineraries} from "../web/app.mjs";
import {parseAirportDemand,buildServiceAnalysis,compareServiceAnalyses,coverageView} from "../web/opportunity-analysis.mjs";
const base=JSON.parse(readFileSync("data/schedules/schedule_7_v1_4_1/canonical_schedule.json"));
const od=parseAirportDemand(readFileSync("data/reference/airport_od_matrix_consolidated_v2.csv","utf8"));
const clock=n=>String(Math.floor(n/60)%24).padStart(2,"0")+":"+String(n%60).padStart(2,"0");
const plans=[
 {name:"BNA-BHM-two-market",fleet:"CRJ700",legs:[
 ["BHM","BNA",815,890],["BNA","BHM",930,1005],
 ["BHM","BNA",1045,1120],["BNA","BHM",1160,1235],
 ["BHM","BNA",1315,1390]]},
 {name:"SYR-RDU-HVN",fleet:"CRJ700",legs:[["SYR","RDU",680,770],["RDU","SYR",810,900]]},
 {name:"DAY-SRQ-GRR",fleet:"CRJ700",legs:[["DAY","SRQ",600,745],["SRQ","DAY",790,935]]}
];
const before=buildServiceAnalysis(base,od,buildItineraries);
const targets=["BNA-ECP","ECP-BNA","BNA-OMA","OMA-BNA","HVN-RDU","RDU-HVN","GRR-SRQ","SRQ-GRR"];
const norm=r=>{const v=coverageView(r,true);return {stops:v.stops,minutes:v.fastest?.totalMinutes??null}};
let cumulative=structuredClone(base);
for(const [i,plan] of plans.entries()){
 const rows=plan.legs.map(([origin,destination,departureMinute,arrivalMinute],k)=>({
  id:"V142-SCREEN-"+i+"-"+k,flight:3000+i*10+k,origin,destination,departureMinute,arrivalMinute,
  departure:clock(departureMinute),arrival:clock(arrivalMinute),fleet:plan.fleet,
  route:800+i,line:"V142-SCREEN-"+i,day:1,sequenceWithinRoute:k+1,pairing:900+i*10+k
 }));
 // Do not claim native feasibility here; this is a read-only passenger-network topology screen.
 cumulative.legs.push(...rows);
 const after=buildServiceAnalysis(cumulative,od,buildItineraries);
 const delta=compareServiceAnalyses(before,after,true);
 console.log(JSON.stringify({scenario:plan.name,hypotheticalLegs:rows.map(l=>({from:l.origin,to:l.destination,dep:l.departure,arr:l.arrival})),coverage:Object.fromEntries(targets.map(k=>[k,{before:norm(before.records.get(k)),after:norm(after.records.get(k))}])),gains:delta.gained.length,losses:delta.lost.length,lostMarkets:delta.lost.slice(0,12),faster:delta.faster.length,slower:delta.slower.length},null,2));
}
