import {readFileSync} from "node:fs";
import {buildItineraries} from "../web/app.mjs";
import {parseAirportDemand,buildServiceAnalysis,compareServiceAnalyses,coverageView} from "../web/opportunity-analysis.mjs";
const base=JSON.parse(readFileSync("data/schedules/schedule_7_v1_4_2/canonical_schedule.json"));
const draft=JSON.parse(readFileSync("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json"));
const od=parseAirportDemand(readFileSync("data/reference/airport_od_matrix_consolidated_v2.csv","utf8"));
const prior=buildServiceAnalysis(base,od,buildItineraries),next=buildServiceAnalysis(draft,od,buildItineraries);
for(const reasonable of [true,false]){
 const x=compareServiceAnalyses(prior,next,reasonable);
 const top=(rows,n)=>rows.filter(r=>(r.demand||0)>=10).sort((a,b)=>(b.demand||0)-(a.demand||0)).slice(0,n).map(r=>({market:r.market,demand:r.demand,before:r.beforeMinutes,after:r.afterMinutes,saved:r.beforeMinutes!=null&&r.afterMinutes!=null?r.beforeMinutes-r.afterMinutes:null}));
 console.log(JSON.stringify({reasonable,counts:Object.fromEntries(["gained","lost","faster","slower"].map(k=>[k,x[k].length])),highestDemandNew:top(x.gained,22),highestDemandFaster:top(x.faster,22),highestDemandSlower:top(x.slower,20),anyLoss:x.lost.slice(0,15),selected:["TYS-SFB","CRW-SFB","GRR-PIE","CMH-SRQ","RDU-BDL","BNA-FLL","FLL-BNA","BNA-DAL","DAL-BNA","SRQ-GRR","GRR-SRQ","HVN-RDU"].map(k=>({market:k,demand:prior.records.get(k)?.demand,before:coverageView(prior.records.get(k),reasonable),after:coverageView(next.records.get(k),reasonable)})).map(x=>({...x,before:{stops:x.before.stops,minutes:x.before.fastest?.totalMinutes??null},after:{stops:x.after.stops,minutes:x.after.fastest?.totalMinutes??null}}))},null,2));
}
