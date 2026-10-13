# Schedule 7 v1.3.1 draft — RFD connections over JAX

Started October 12, 2026 from main commit `80185b5dd8464899a6f09cb8249e54e264185aa4`, the published v1.3.0 canonical. This is an **unpublished draft**, not a release. The app default and public manifest remain v1.3.0. The user authorized use of spare fleet where system demand supports it.

Updated October 13, 2026: the reviewed MCI turn is accepted into R724. Northeast/FLP work is at the hypothesis-validation stage only.

## Selected flying

Add one MAX9 aircraft-day, R724 on Line A, Day 6, with two daily RFD–JAX round trips and the accepted evening RFD–MCI round trip:

| Flight | Departure, local | Arrival, local | Block |
|---|---|---|---|
| F2195 | RFD 05:40 CT | JAX 08:56 ET | 2h16 |
| F2196 | JAX 09:40 ET | RFD 10:56 CT | 2h16 |
| F2197 | RFD 12:14 CT | JAX 15:30 ET | 2h16 |
| F2198 | JAX 16:10 ET | RFD 17:26 CT | 2h16 |
| F2199 | RFD 19:26 CT | MCI 20:40 CT | 1h14 |
| F2200 | MCI 21:20 CT | RFD 22:34 CT | 1h14 |

The new day adds **11h32 of block flying**: 9h04 for JAX plus 2h28 for MCI. Same-day turns are 44 minutes at JAX, 78 at RFD, 40 at JAX, 120 at RFD and 40 at MCI. The 22:34 RFD return preserves 6h01 before R708's unchanged 04:35 SFB departure. JAX assignments use existing B5/B5/B11/B11; MCI uses B10 for arrival and M11 for departure; no bank window or passenger connection limit changes. TLH's morning inbound and ECP/TLH's evening outbound connections have 235-minute waits, five minutes inside the 240-minute maximum.

All **1,192 existing flights retain their clocks, flight and route IDs, fleet and within-route sequence**. This includes load-bearing prior fixes on R703/R704 and the newly released R307 extension. Move the existing closed SFB–DAY–SFB two-day segment, R703/R704, from Line A into Line B after R721. Insert R724 between R707 and R708; reindex MAX9 line days. Both A and B then contain 12 routes, close correctly, and retain legal maintenance RONs. The change to R703/R704 is an administrative rotation move with no flight retiming.

The result is **1,198 flights, 182 routes and 19 lines**. MAX9 use rises from 23/35 to **24/35**, leaving 11 spare aircraft. Other fleet usage remains CRJ900 28/45, CRJ700 54/65, CRJ200 76/80. Fleet inventory does not increase.

## Why JAX and why two round trips

JAX already has service in both directions to all six priority cities. BHM has EYW and ECP feeders, but would need new service in both directions to MYR, ILM, ROA and TLH. RFD–BHM would be shorter (103 versus 136 block minutes), but building those feeders would make it a much larger project.

Every existing MAX9 hold at JAX/BHM/RFD was screened. The longest relevant same-day hold is RFD's 162 minutes; JAX tops out at 78 and BHM at 150. Inserting a round trip while keeping 40-minute turns before, at the spoke and after requires 392 minutes from JAX or 326 from BHM. No relevant MAX9 originator or terminator has enough usable extension time either. The existing MAX9 service is too tightly routed for a simple insertion.

One JAX→RFD departure cannot accommodate all six unchanged feeders. EYW's morning arrival permits departure at 07:19–10:49, before MYR's first legal window at 14:55–18:25. Their late arrivals can connect together after 19:15, but TLH's latest feed window ends at 14:05 and ECP's at 15:11. Two outbound waves are therefore needed. The four-leg RFD day accommodates both waves with only one spare aircraft, avoiding a second new aircraft-day or disruptive feeder rebuild.

## Priority connections

Every row below gains a timetable-valid one-stop itinerary in **both directions**, over JAX. Durations are the fastest new one-stop journey, not necessarily the fastest journey of any stop count.

| City | O-D/day city→RFD / RFD→city | City→RFD | RFD→city | Geography screen |
|---|---|---|---|---|
| MYR | 42.0 / 41.5 | 5h06; F1628 + F2198 | 5h10; F2195 + F1626 | Pass |
| EYW | 40.5 / 39.6 | 6h31; F1555 + F2196 | 6h34; F2195 + F1557 | Pass |
| ECP | 32.8 / 32.0 | 6h06; F1743 + F2196 | 7h12; F2197 + F1742 | Pass |
| ILM | 24.5 / 24.1 | 5h16; F1601 + F2198 | 5h20; F2195 + F1599 | Pass |
| ROA | 19.2 / 19.6 | 6h41; F1561 + F2196 | 5h35; F2197 + F1560 | Outside 2.25× screen |
| TLH | 9.6 / 9.2 | 7h01; F1759 + F2196 | 7h01; F2197 + F1758 | Pass |

**ROA remains a quality opportunity.** JAX produces a 2.35649× distance ratio, so the app's geographic opportunity filter still flags this pair. No policy exception was made to the screen. PHF is geographically better, but its nearest current repairs are 139 minutes for ROA→RFD and 59 minutes for RFD→ROA; neither can be applied alone inside the assigned banks and aircraft turns. A coordinated PHF solution should be reviewed separately, rather than undoing prior work just to force this draft's smallest-but-one priority market into a better path.

Some new one-stop choices are slower than retained two-stop options. For example EYW→RFD's prior fastest trip is 5h43 and ECP→RFD's is 5h18. Those alternatives remain available. This draft addresses the requested maximum-one-connection gaps without assuming that fewer stops always mean a faster trip.

## Demand and additional value

The pinned directional matrix uses an already-dampened own/primary blend for secondary airports. No Chicago metro total was added again and no second deflation was applied.

RFD–JAX itself has **269.0 daily directional O-D passengers combined** (135.6 toward RFD, 133.4 toward JAX). The six priority pairs add 334.6 in underlying bidirectional demand. Excluding ROA for the distance screen, the local market plus the five geographically suitable priority pairs total **564.8/day**.

The initial four-leg JAX case has a unique local/new geographically suitable one-stop market O-D pool of **698.7/day**. With MCI, the six-leg route's corresponding pool is **1,132.8/day**, including the already-served 400/day RFD–MCI local market and newly covered SGF→RFD/LBB→RFD markets. Existing MCI demand is shared across four daily frequencies, not claimed as a new passenger pool. Each directional market is counted once in that total. The benefit includes new one-stop coverage for GNV, AGS, BTR, MOB and GPT in both directions, plus VPS→RFD, RFD→AVL and MLB→RFD. RFD→SRQ also improves from 5h26 to 4h59 and RFD→SAT from 5h43 to 5h34.

The per-flight demand review excludes connecting markets already served nonstop, deduplicates each market and applies the 2.25× distance screen. It also reports a conservative comparison subset: new one-stop/local markets plus connecting choices no more than 30 minutes slower than the prior fastest trip. Its equal-choice opportunity indices are roughly 211, 194, 268 and 155 for F2195–F2198 before any booking preference or capture adjustment. These indices divide each market across its available choices of the same stop count. **Neither those indices nor the 698.7 pool are forecast loads**; secondary-airport uncertainty and existing alternatives remain material. The JAX case supports one spare MAX9. The accepted MCI turn uses that same aircraft-day, with comparable conservative opportunity indices of 143 outbound and 144 returning. It adds 74 app choices, improves 10 fastest journeys versus the four-leg draft and introduces no losses.

The full app comparison adds **358 itinerary choices and 33 one-stop directional markets**, improves the fastest journey in 35 markets, and loses no itineraries, coverage or fastest-trip time. Under the unchanged 2.25× screen, 27 directional markets gain one-stop coverage and 28 fastest journeys improve. The full evidence is in `data/schedules/schedule_7_v1_3_1_draft/connection_review.json`.

## Gate and operating tradeoffs

Native structure, operating, curfew, minimum turns, overnight continuity, maintenance RON, planning reconstruction and fixed gate/stand assignment pass with **zero effective errors and zero hard-stop failures**. Effective advisories decline from 165 to 164 because Line A's former 13-day rotation becomes 12 days. The pre-existing unavailable runway-data check remains unavailable.

RFD retains its four gates and two stands. The extra overnight aircraft creates **two additional deliberate stand middles totaling 342 minutes**: 256 minutes for R724→R708's overnight hold and 86 minutes in R329's existing long day hold. All deplaning and boarding remain at gates; no passenger turn is performed on a stand. System stand use increases from 14 claims / 3,253 minutes to **16 claims / 3,595 minutes**. The MCI turn saves 308 stand minutes compared with the four-leg draft. Neither JAX nor MCI adds stand use. This is a real cost of the proposed extra service, not an inventory increase.

A narrowly scoped RFD hub-count override records the user-requested fifth useful hub touch and standing hub-count exception authorization. City roster, demand pin, bank count/windows, physical inventory, curfews, other policies and all prior overrides remain unchanged.

## Reproduction and review

```bash
python scripts/build_schedule_7_v1_3_1_draft.py
node scripts/audit_schedule_7_v1_3_1_connections.mjs
python scripts/review_schedule_7_v1_3_1_rfd.py
```

The builder enforces the pinned v1.3.0 SHA and verifies original-flight preservation, the exact six new flights, legal 12-day lines, fleet use, fixed gates/stands and native hard stops. The network audit enforces all 12 requested timetable connections, the 10 geographically suitable priority connections, zero itinerary/coverage losses and zero slower fastest journeys. No superseded release package is reconstructed. Published v1.3.0 remains the latest-only regression target until release authorization.

Configuration: `config/optimizations/schedule_7_v1_3_1_round_2.json` (cumulative accepted flying). Round 1 is the historical four-leg checkpoint. Draft package: `data/schedules/schedule_7_v1_3_1_draft/`. Corridor/idle screen: `outputs/schedule_7_v1_3_1/corridor_screen.json`.

## Subsequent evening-utilization review

The [October 13 R724 evening review](schedule_7_v1_3_1_evening_review.md) identifies feasible MCI, BHM and DAY extensions using the same aircraft-day, plus an unaccepted coordinated PHF option. The user selected MCI on October 13; it is now included in the six-leg draft above. BHM, DAY and PHF remain historical proposals. The published app default is unchanged.

## Northeast/FLP hypothesis validation

The [current coverage audit](schedule_7_v1_3_1_ne_flp_coverage.md) confirms 25 of 45 northeast/FLP city pairs lack direct or one-stop service in both directions. PGD accounts for 77% of the recorded demand in those gaps. This is validation only: no northeast/Florida feeder or bank changes are accepted yet.
