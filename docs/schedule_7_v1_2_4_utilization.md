# Schedule 7 v1.2.4 — working draft

> Release update, October 10, 2026: accepted work below is published as v1.2.4. See [release notes](schedule_7_v1_2_4_release.md). Draft-stage status statements and source-route references below are historical. Start future work from the released v1.2.4 canonical.

**Unpublished.** Routes 350, 126 and 308 are implemented at the user's instruction. Subsequent approved work adds the 115/116/117 JAX/XNA overnight changes and 517/518 PHF–GNV overnight/originator service, described in `docs/schedule_7_v1_2_4_gnv.md`. Route 518's original four flights retain their clocks. The subsequently approved 125 SYR–ROC morning turn and 157 OMA–BHM evening turn are also implemented; see `docs/schedule_7_v1_2_4_extensions.md`. Route 304 is retained. The revised source-route 337/345 PHF–MCI exchange is now implemented with a 00:01 local arrival cutoff; see `docs/schedule_7_v1_2_4_midnight_swap.md`. Main and the live app remain on v1.2.3. Work is saved on `codex/v1.2.4-utilization`.

The base is the **released v1.2.3 canonical (1152 flights)**, not the older v1.2.3 draft. The accepted v1.2.4 canonical now has **1170 flights**. Existing flight IDs, numbers, fleets and city pairs are preserved. Round five rebuilds AH/AK/AL/AS into 9/9/12/11-day cycles and changes route/line/day assignments in that pool. Flight 1739 GNV–JAX moves 37 minutes later, and Flight 1811 SYR–PVD moves nine minutes later under earlier approvals. Round five advances flights 1404/1319/1320/1784/1589 by 12/16/16/3/1 minutes; other released clocks are preserved. Aircraft and gate inventories remain unchanged. Two MCI banks move one minute earlier and PHF gains a midnight arrival bank. Current replay input is `config/optimizations/schedule_7_v1_2_4_accepted_rounds_1_5.json`. The 1154/1158/1164/1168-flight round-one through round-four comparison snapshots are preserved in their named folders. Historical route references below use their original snapshot numbers.

## Implemented: Route 350

CRJ700, line AO / day 1. All times below are local; ELP is MT and MCI is CT.

| Flight | Flying | Departure | Arrival | Local allocation | Connecting opportunity | Total opportunity |
|---|---|---|---|---:|---:|---:|
| 2155 | ELP–MCI | 18:27 MT | 21:43 CT | 3.3 | 0.0 | 3.3 |
| 2156 | MCI–ELP | 22:33 CT | 23:49 MT | 3.2 | 148.0 | 151.1 |

This raises the market from three to four daily flights each way. The latest previous ELP departure was 12:10; the latest previous MCI return was 16:25. The new flights follow them by **6h17 and 6h08**, respectively. Turns are **46 minutes at ELP and 50 minutes at MCI**. The next ELP originator remains 04:55, leaving **5h06 aircraft RON**. Block utilization increases from **9h04 to 13h36** (an additional 4h32).

At 21:43, none of MCI's remaining onward departures forms a qualifying connection for ELP demand in the model. The ELP–MCI flight's low demand remains a real weakness; the return is supported by TEX, FLP, APP, GCP, OZK and other connecting flows. No currently connected market disappears or gets a slower fastest itinerary; six improve.

Replay input: `config/optimizations/schedule_7_v1_2_4_accepted_350.json`. Working canonical: `data/schedules/schedule_7_v1_2_4_draft/canonical_schedule.json`. Detailed validation and demand: `config/proposals/schedule_7_v1_2_4_accepted_350_review.json`.

## Accepted round two: Routes 126 and 308

The user subsequently approved these with "Add the proposals to the 1.2.4 draft as suggested." Both turns are now in the accepted canonical with flight numbers 2157–2160. Times and scores use the complete timetable including the approved Route 350 turn.

| Route / line-day | Fleet | Proposed flight | Local departure → arrival | Current frequency → proposed | Local allocation | Connecting opportunity | Total opportunity |
|---|---|---|---|---|---:|---:|---:|
| 126 / AD-16 | CRJ200 | 2157 MLB–JAX | 20:00 → 20:52 ET | 2 → 3 | 0.1 | 11.8 | 11.9 |
| 126 / AD-16 | CRJ200 | 2158 JAX–MLB | 21:42 → 22:34 ET | 2 → 3 | 0.1 | 18.2 | 18.3 |
| 308 / AA-8 | CRJ700 | 2159 CLT–MCI | 20:30 ET → 21:43 CT | 3 → 4 | 14.5 | 20.6 | 35.1 |
| 308 / AA-8 | CRJ700 | 2160 MCI–CLT | 22:45 CT → 01:58 ET next day | 3 → 4 | 14.9 | 95.2 | 110.0 |

**126: the best short extension, with modest demand.** The MLB–JAX local market is only 0.2 daily passengers in each direction in the pinned demand snapshot; nearly all modeled opportunity is connecting. The arrival feeds CLT, MSY and SAV, dominated by CLT. The return draws CGI, APP, GLC, LEC and other groups into MLB. This adds **1h44 block**, taking the aircraft from **8h44 to 10h28**. Turns are **48 minutes at MLB and 50 minutes at JAX**. The next 04:55 MLB originator is unchanged, leaving **6h21 aircraft RON**. This is a discretionary service addition, not a high-demand case. BHM alternatives pass at sufficiently late times, but produce only about 3 outbound and 16–18 inbound opportunities for 3h20 extra block and a return after midnight. Direct PNS/VPS/ECP turns offer very little demand.

**308: the strongest extension in this review.** CLT–MCI has pinned directional local O-D of 62.3 / 62.7. Existing competing flights and connection choices reduce the added flights' local allocations to about 14.5 / 14.9. The new CLT arrival connects to MAF, SAT and the newly approved ELP return. The late MCI departure collects TEX, GLC, OZK and UMP flows, led by SAT, MKE, DAL and OMA. Route 350's ELP arrival also feeds this CLT departure. This adds **4h26 block**, taking the aircraft from **7h03 to 11h29**. Turns are **49 minutes at CLT and 62 minutes at MCI**. Route 309 still starts CLT at 07:30, leaving **5h32 aircraft RON**. The SAT arrival at 22:15 connects to the 22:45 departure at the **30-minute minimum**; the MAF connection from the new CLT arrival is **32 minutes**. Those are material delay-sensitive connections.

The combined 126/308 addition passes structural, operating, minimum-turn, overnight, planning and physical gate/stand checks with **zero effective operating errors and no hard-stop failures**. It preserves every existing clock, loses no connected market and slows no fastest itinerary; eleven markets improve relative to the round-one draft. Stand use is **16 claims / 3717 minutes**, versus 15 / 3771 in round one; no passenger handling occurs on stands. Existing 182 operating warnings remain. The combined accepted schedule has **1158 flights**.

Historical proposal replay input: `config/proposals/schedule_7_v1_2_4_proposed_126_308.json`, repinned to the unchanged round-one snapshot. Current accepted replay is the cumulative rounds-1–2 overlay above. No main or live-app publication has occurred.

## Route 518: retain the current schedule

CRJ900, line AG / day 8, terminates SYR at **19:19 ET**. It cannot turn before **19:59**, after SYR-B6 closes at 19:45. Waiting for SYR-B7 at 21:30 leaves no fully compliant round trip in the screened evening window. Short spoke returns run into the 21:00 spoke departure cutoff; hub alternatives fail the configured bank/turn combination.

Moving only the last PIE–SYR flight earlier into B6 collides with Flight 1231's 16:05 departure. An earlier PHF/PIE rebuild also conflicts with Route 519's 08:55 PIE–PHF flight. A larger, physically feasible reconstruction resolves those conflicts:

| Existing flight | Current local times | Rebuilt local times | Shift |
|---|---|---|---:|
| 1171 PHF–PIE | 06:55–08:54 | 05:25–07:24 | −90 min |
| 1179 PIE–PHF | 11:15–13:14 | 08:25–10:24 | −170 min |
| 1173 PHF–PIE | 13:55–15:54 | 11:30–13:29 | −145 min |
| 1232 PIE–SYR | 16:35–19:19 | 14:15–16:59 | −140 min |

All are ET. This permits these fully validated late SYR turns:

| Destination | Existing SYR flights each way | SYR departure → destination arrival | Return departure → SYR arrival | Outbound / return total opportunities |
|---|---:|---|---|---:|
| BDL | 2 | 18:45–19:40 | 20:45–21:40 | 132.1 / 18.0 |
| PIT | 3 | 18:45–19:50 | 20:30–21:35 | 114.5 / 11.4 |
| CAK | 3 | 18:45–19:54 | 20:34–21:43 | 136.1 / 2.2 |
| GRR | 0 | 18:45–20:13 | 20:53–22:21 | 143.0 / 2.6 |
| CMH | 0 | 18:45–20:06 | 20:46–22:07 | 140.1 / 4.1 |

BDL and PIT best match the existing-market frequency priority. Their new departures capture useful Florida and other inbound groups, but their returns are weak. More seriously, the rebuild erodes current service: Flight 1171's modeled opportunity falls **87.3 → 7.4**, Flight 1179 falls **277.3 → about 150**, and Flight 1173 falls **241.0 → 167.3**. The existing-flight audit identifies lost connecting choices as well as gains; these figures are not additive net passenger losses.

The BDL/PIT/CAK alternatives make the fastest itinerary slower in **14 markets**. Examples include PIE–IND (+71 minutes), PIE–MSN (+71), ILM–PIE (+140), and MYR–PIE (+140). No market loses every itinerary, but preserving reachability does not preserve service quality. GRR has 13 slower markets; CMH has 14. These costs and the weak return legs outweigh the utilization benefit. Store these as sensitivities for a future SYR-bank redesign, rather than implement this rebuild now.

## Method, scope and checks

The bounded screen compares unchanged clocks, modest retimings and a larger 518 rebuild. Wide timing windows use a 15-minute one-stop ranking grid; selected candidates receive full one/two-stop enumeration, competing-itinerary allocation, physical validation and before/after connection audits. Explicit buffered and late-slot alternatives supplement the grid. This is not an exhaustive optimization of all possible fleet or schedule exchanges.

Demand uses `bts-db1c-6mo-jul2025-apr2026-v7`, 30–240-minute connections and the existing circuity/relative-choice model. Reported opportunities are **seat-uncapped, full-capture scenario measures**, not forecasts, guaranteed loads, profit estimates or net incremental passengers. Scores on successive legs can count the same traveler. In particular, scores above aircraft seats are evidence of network opportunity, not a claim the aircraft can carry that many passengers.

Aircraft-day validation is separate from crew staffing. The 350 day spans 04:55–23:49 with 13h36 block; 308 would end after midnight. Both need a crew plan, and the quoted aircraft RONs do not establish legal crew rest. Marginal flight cost, realistic demand capture and connection reliability remain decision factors, especially for 126 and the weak 350 outbound.

Accepted 350/126/308 changes pass all full constraint checks. No gates, stands, bank boundaries, frequency limits, minimum turns or curfews are waived. Latest-release regression passed **49 checks (13 Python + 36 JavaScript)** against v1.2.3 only. The draft's replay verification independently confirms exactly six added flights and no changes to the 1152 released legs. Main/app publication remains reserved to the user.

Detailed screening, rejected constraints, geography, flight-level connecting choices, fastest-itinerary audits and retimed-flight impacts are in `config/proposals/schedule_7_v1_2_4_evening_screen.json`. Resume tools read a base SHA checkpoint and do not reapply older v1.2.3 work.

```bash
python scripts/analyze_schedule_7_v1_2_4.py --accept
python scripts/analyze_schedule_7_v1_2_4.py --screens
python scripts/analyze_schedule_7_v1_2_4.py --rebuild
python scripts/analyze_schedule_7_v1_2_4.py --trials
python scripts/analyze_schedule_7_v1_2_4.py --holistic
python scripts/analyze_schedule_7_v1_2_4.py --holistic2
python scripts/analyze_schedule_7_v1_2_4.py --audit
python scripts/analyze_schedule_7_v1_2_4.py --joint
python scripts/analyze_schedule_7_v1_2_4_xna.py --accept
python scripts/analyze_schedule_7_v1_2_4_xna.py --alternative
python scripts/analyze_schedule_7_v1_2_4_gnv.py
python scripts/analyze_schedule_7_v1_2_4_gnv.py --accept
```
