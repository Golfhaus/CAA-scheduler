import {readFileSync} from "node:fs";
import {buildItineraries} from "../web/app.mjs";
import {parseAirportDemand,buildServiceAnalysis,compareServiceAnalyses,coverageView} from "../web/opportunity-analysis.mjs";
const base=JSON.parse(readFileSync("data/schedules/schedule_7_v1_4_1/canonical_schedule.json"));
const demand=parseAirportDemand(readFileSync("data/reference/airport_od_matrix_consolidated_v2.csv","utf8"));
const candidate=structuredClone(base);
const leg=candidate.legs.find(l=>l.flight===1879);
leg.departureMinute-=50;leg.arrivalMinute-=50;leg.departure="08:55";leg.arrival="09:51";
let pair=Math.max(...candidate.legs.map(l=>l.pairing))+1;
for(const [i,o,d,dep,arr] of [[0,"SYR","RDU",650,740],[1,"RDU","SYR",795,885]]){
 candidate.legs.push({id:"V142-R178-"+i,route:178,line:"AC",day:9,fleet:"CRJ200",flight:2280+i,pairing:pair+i,sequenceWithinRoute:i+1,origin:o,destination:d,departureMinute:dep,arrivalMinute:arr,departure:String(Math.floor(dep/60)).padStart(2,"0")+":"+String(dep%60).padStart(2,"0"),arrival:String(Math.floor(arr/60)).padStart(2,"0")+":"+String(arr%60).padStart(2,"0")});
}
const a=buildServiceAnalysis(base,demand,buildItineraries),b=buildServiceAnalysis(candidate,demand,buildItineraries);
for(const geographic of [true,false]){
const delta=compareServiceAnalyses(a,b,geographic);
const rows=arr=>arr.map(x=>({market:x.market,demand:x.demand,before:x.beforeMinutes,after:x.afterMinutes,delta:x.beforeMinutes!=null&&x.afterMinutes!=null?x.beforeMinutes-x.afterMinutes:null}));
console.log(JSON.stringify({basis:geographic?"geographically reasonable":"all itineraries",counts:Object.fromEntries(["gained","lost","faster","slower"].map(x=>[x,delta[x].length])),gained:rows(delta.gained),lost:rows(delta.lost),faster:rows(delta.faster),slower:rows(delta.slower)},null,2));
}
