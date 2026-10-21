import {readFileSync} from "node:fs";
import {buildItineraries} from "../web/app.mjs";
import {parseAirportDemand,buildServiceAnalysis,coverageView} from "../web/opportunity-analysis.mjs";
const canonical=JSON.parse(readFileSync("data/schedules/schedule_7_v1_4_1/canonical_schedule.json"));
const od=parseAirportDemand(readFileSync("data/reference/airport_od_matrix_consolidated_v2.csv","utf8"));
const audit=buildServiceAnalysis(canonical,od,buildItineraries);
const pairs=[["BLV","HOU"],["HVN","RDU"],["BNA","ECP"],["GRR","SRQ"],["BNA","OMA"]];
const hubs=[...canonical.operatingPolicy.hubs,...canonical.operatingPolicy.focusCities];
const flight=(l)=>({flight:l.flight,route:l.route,fleet:l.fleet,origin:l.origin,dest:l.destination,dep:l.departure,arr:l.arrival,bank:l.bankId});
const wrap=(a,b)=>(b-a+1440)%1440;
for(const [a,b] of pairs){
 console.log("\n### "+a+"-"+b);
 for(const [from,to] of [[a,b],[b,a]]){
  const r=audit.records.get(from+"-"+to);
  console.log(JSON.stringify({direction:from+"-"+to,demand:r.demand,rawCounts:r.counts,reasonableCounts:r.reasonableCounts,reasonableBest:r.reasonableBest.map(x=>x&&{minutes:x.totalMinutes,legs:x.legs.map(l=>l.flight)}),sharedHubs:r.sharedHubs}));
  const options=[];
  for(const hub of hubs){
   const first=canonical.legs.filter(x=>x.origin===from&&x.destination===hub);
   const second=canonical.legs.filter(x=>x.origin===hub&&x.destination===to);
   for(const f of first) for(const s of second){
    const gap=wrap(f.arrivalMinute,s.departureMinute);
    const distanceToWindow=gap<30?30-gap:gap>240?Math.min(gap-240,1470-gap):0;
    options.push({hub,first:flight(f),second:flight(s),gap,change:distanceToWindow});
   }
  }
  options.sort((x,y)=>x.change-y.change||x.gap-y.gap);
  console.log("BEST SAME-HUB TIMES "+JSON.stringify(options.slice(0,12)));
  const near=audit.nearMisses.find(x=>x.market===from+"-"+to);
  if(near)console.log("NEAR MISS "+JSON.stringify({hub:near.hub,adjustment:near.adjustment,first:flight(near.first),second:flight(near.second),transfer:near.transfer}));
 }
}
