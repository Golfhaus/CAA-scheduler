# Schedule 7 v1.2.4 — accepted midnight PHF/MCI exchange

Approved for the unpublished draft by “Add the current recommendations to the draft.” This accepts the repaired CRJ700 source-route 337/345 exchange from the 00:01 review. SYR and the weak MAX9/CRJ200 alternatives remain deferred. Main and the live app remain v1.2.3.

The draft has **1,170 flights**, including **18 additions** since released v1.2.3. Incremental replay is `config/optimizations/schedule_7_v1_2_4_accepted_round_5.json`; exact cumulative replay from v1.2.3 is `config/optimizations/schedule_7_v1_2_4_accepted_rounds_1_5.json`. The previous 1,168-flight canonical and report remain immutable in `data/schedules/schedule_7_v1_2_4_round_4/`.

| Flight | Current route / line / day | Source route | Direction | Departure local | Arrival local | Local opportunity | Connecting opportunity | Total opportunity |
|---|---|---|---|---|---|---:|---:|---:|
| 2171 | 323 / AK / 3 | 337 | PHF–MCI | 20:45 ET | 22:22 CT | 5.7 | 84.4 | 90.1 |
| 2172 | 337 / AL / 8 | 345 | MCI–PHF | 20:24 CT | 00:01 ET next day | 5.6 | 23.3 | 28.9 |

Each direction increases from one to two daily flights. Opportunity figures are pinned O-D, seat-uncapped full-capture relative-choice model outputs, not forecasts, incremental passengers or profit. The eastbound case remains substantially weaker. PHF–MCI connects to the existing 22:55 MCI–SAT departure with 33 minutes. MCI–PHF does not connect to PHF's first 04:30 departures: the 269-minute wait exceeds the 240-minute model limit.

## Accepted clock and bank changes

| Existing flight | Direction | New local times | Advance |
|---|---|---|---:|
| 1404 | ELP–MCI | 11:28 MT–14:44 CT | 12 minutes |
| 1319 | MCI–CMH | 15:24 CT–18:14 ET | 16 minutes |
| 1320 | CMH–MCI | 18:54 ET–19:44 CT | 16 minutes |
| 1784 | XNA–MCI | 13:57–14:54 CT | 3 minutes |
| 1589 | MFE–MCI | 12:19–14:54 CT | 1 minute |

XNA and MFE arrive 30 minutes before revised flight 1319, preserving their CMH connection. Existing approved changes to flights 1739 and 1811 also remain in the draft. All other existing flight clocks are preserved.

MCI-B7 moves from 14:45–15:45 to 14:44–15:44 CT; MCI-B10 moves from 19:45–20:45 to 19:44–20:44 CT. PHF gains the 00:00–01:00 ET arrival bank. Bank assignments and the authorized PHF bank count are recorded in the overlay.

## Line reconstruction and verification

AH / AK / AL / AS retain their 41 aircraft-days and fleet count, reclosed into **9 / 9 / 12 / 11-day** cycles. Current route numbers change for this pool; the incremental overlay records every source-to-target mapping. In particular source 337 is now **323 / AK-3**, and source 345 is now **337 / AL-8**. Earlier analysis route references must be interpreted using their pinned snapshot. The PHF overnight before current route 338 is **4h29**; the MCI overnight before current route 324 is **8h53**.

Structural, operating hard stops, planning, overnight continuity, maintenance cadence and physical gates/stands pass with **zero effective operating errors**. §2.6 Check A passes, and Check B has no new findings or worsened gaps compared with round four. Advisory operating findings remain. Exact cumulative replay matches the sequentially accepted draft. Every prior flight ID, number, fleet and city pair is retained; only the explicit route/line/day reconstruction and approved clock changes occur.

The independently reproduced round-five connection audit improves the fastest itinerary for **25 directional markets** and slows **31 by 1–16 minutes**. No previously connected market loses all valid connections. Newly connected markets have 24.8 daily underlying O-D, distinct from the flight-level allocations. The short SAT connection and an arrival exactly on the 00:01 cutoff have little delay margin. Aircraft feasibility does not establish crew duty/rest legality or a detailed overnight maintenance-task plan.

Reproduce acceptance with `python scripts/accept_schedule_7_v1_2_4_midnight_swap.py`. It checks the pinned input, reviewed allocation/audit, route identities, fleet counts, arrival cutoff, replay and complete draft validation before writing. Latest regression remains limited to the latest released schedule; no historical v1.1 checks are required.

Publication remains reserved to the user's decision.
