import {readFileSync} from "node:fs";
import {buildRoutingDetails} from "../web/routing-details.mjs";
const old=JSON.parse(readFileSync("data/schedules/schedule_7_v1_4_2/canonical_schedule.json"));
const newer=JSON.parse(readFileSync("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json"));
const g0=JSON.parse(readFileSync("data/schedules/schedule_7_v1_4_2/gates.json"));
const g1=JSON.parse(readFileSync("data/schedules/schedule_7_v1_4_3_draft/gates.json"));
for(let route of [177,178,359]){
 const a=buildRoutingDetails(old,g0,route),b=buildRoutingDetails(newer,g1,route);
 const compact=x=>({flights:x.flights.length,totalFlightMinutes:x.totalFlightMinutes,criticalFlightMinutes:x.criticalFlightMinutes,criticalUtilization:x.criticalUtilization});
 console.log(JSON.stringify({route,before:compact(a),after:compact(b),legs:newer.legs.filter(x=>x.route===route).sort((x,y)=>x.sequenceWithinRoute-y.sequenceWithinRoute).map(x=>({flight:x.flight,origin:x.origin,destination:x.destination,departure:x.departure,arrival:x.arrival}))},null,2));
}
