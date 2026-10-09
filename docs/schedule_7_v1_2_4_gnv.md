# Schedule 7 v1.2.4 — approved XNA/JAX/GNV overnight plan

**Implemented in the unpublished draft at the user's instruction.** Route 517 is the best current PHF terminator for the GNV overnight: it maintains ample MX coverage on line AG and returns in time for Route 518's unchanged 06:55 PHF–PIE flight. This resolves GNV overnight coverage and allows the 115/116/117 JAX/XNA plan to operate without a maintenance exception.

This document records approved round-three flying and its 1,164-flight comparison state. Subsequent approved 125/157 additions bring the current unpublished draft to **1,168 flights**, with Flight 1811 also retimed by nine minutes. See `docs/schedule_7_v1_2_4_extensions.md`; current cumulative replay is `config/optimizations/schedule_7_v1_2_4_accepted_rounds_1_4.json`. All flying described here is retained.

## Added flying and the one existing-flight change

| Flight | Route / line-day | Fleet | Added flying, local times | Modeled total opportunity |
|---|---|---|---|---:|
| 2161 | 115 / AD-5 | CRJ200 | GNV 20:42 → JAX 21:19 ET | 0.3 |
| 2162 | 116 / AD-6 | CRJ200 | JAX 04:30 → GNV 05:07 ET | 0.3 |
| 2163 | 116 / AD-6 | CRJ200 | MCI 21:25 → XNA 22:22 CT | 139.6 |
| 2164 | 117 / AD-7 | CRJ200 | XNA 05:30 → MCI 06:27 CT | 30.4 |
| 2165 | 517 / AG-7 | CRJ900 | PHF 21:45 → GNV 23:30 ET | 30.5 |
| 2166 | 518 / AG-8 | CRJ900 | GNV 04:30 → PHF 06:15 ET | 17.1 |

**Flight 1739 GNV–JAX moves from 05:10–05:47 to 05:47–06:24 ET**, allowing the 40-minute GNV turn after the new 04:30 JAX flight. Every other pre-existing departure/arrival clock remains unchanged. Route 117 still leaves MCI for OMA at **07:15 CT**; Route 518 still leaves PHF for PIE at **06:55 ET**. Existing flight IDs/numbers, fleet, route, line and day are preserved; sequence positions shift on the three routes with new originators.

The six new legs add **6h38 block** across the affected aircraft days. The earlier approved 350, 126 and 308 flying remains intact. The accepted draft now has **1164 flights, 181 routes and 20 lines**, twelve more flights than released v1.2.3. No fleet, airport inventory or bank changes are made.

## Why Route 517 is the preferred PHF aircraft

517 already reaches PHF at **20:59**, leaving a **46-minute turn** before the new 21:45 GNV departure. Its next aircraft day is 518, whose 06:55 first PHF departure is late enough to accommodate GNV 04:30 → PHF 06:15. That leaves **exactly the 40-minute minimum turn**. GNV aircraft RON is **5h00**. The connecting passenger window to the 06:55 wave is also 40 minutes.

Line AG retains MX-target overnights at **PIE on day 3, JAX on day 4, FLL on day 6 and SYR on day 8**. Its longest consecutive non-target RON run remains **three nights**, with no use of the standing grace. It retains hub/focus overnights at JAX and SYR. The removed PHF RON is therefore not load-bearing for maintenance cadence.

For line AD, shifting 115's overnight from GNV to JAX replaces the maintenance credit removed when 116 moves from MCI to XNA. Its longest non-target RON run remains **nine nights**, below the ten-night limit. The JAX RON is **7h11**; the XNA RON is **7h08**. The XNA return leaves **48 minutes** before MCI–OMA. GNV has a true overnight again, supplied by 517/518.

Other PHF terminators were inventoried with their cyclic next originators and maintenance coverage. **314/315** is a feasible alternative after delaying PHF–PVD three minutes to 06:58: PHF 22:12 → GNV 00:00, GNV 04:30 → PHF 06:18. It has weaker evening opportunity (27.5), a shorter **4h30 aircraft RON**, and extends line AH's longest non-MX stretch from six to **ten nights**. 517/518 offers more maintenance slack and preserves the existing originator clock. Most other PHF terminators either cannot accommodate an earliest-legal 04:30 GNV return before their next originator or require much larger clock changes. In particular, 347/348 would require at least a 50-minute originator delay.

The five-minute buffered 518 alternative, PHF–PIE at 07:00, was validated too. It leaves 45 minutes at PHF but slows four existing PIE-bound markets by five minutes. The selected schedule keeps 06:55, with the tight 40-minute turn explicitly recorded.

## Demand and connection tradeoffs

The XNA flights remain the largest demand benefit, adding a third MCI flight each way and the first XNA–MCI originator. The PHF–GNV pair adds modest useful coverage: late arrivals into PHF feed GNV, while the 06:15 return reaches PHF's morning wave. Evening PHF–GNV opportunity is mainly TEX, LEC, NEC, GLC and OZK; morning GNV–PHF is mainly TEX, NEC, LEC and MAC. The PHF–GNV local allocation is about **1.4 each way**; most demand opportunity is connecting. This is modest demand for a CRJ900, and the schedule uses it as part of the requested overnight/maintenance restructuring.

The two new GNV–JAX/JAX–GNV flights are chiefly **positioning flights**, with about 0.3 local opportunity and no qualifying connecting demand each in this timing model. They retain GNV's existing evening JAX service while placing the CRJ200 at JAX for its maintenance RON and back at GNV for its existing flying. These legs need to be assessed as a cost of enabling the full plan, not as independently strong passenger services.

Moving Flight 1739 by 37 minutes misses some early JAX connection choices. Its modeled opportunity falls **59.0 → 38.6**, with 19 connecting choices lost. In the complete model:

- **Four markets lose all qualifying nonstop/one-stop/two-stop options:** GNV–RDU (4.3 daily pinned O-D), GNV–LEX (2.7), GNV–AVP (0.3), and GNV–TTN (0.0), totaling **7.3**. This is a connectivity loss in the model, not a forecast of seven displaced passengers.
- Four other GNV-origin markets get slower fastest itineraries: PIT (+93 minutes), ALB (+124), ABE (+40) and PIE (+135).
- **74 markets get a faster best itinerary**, and newly connected markets have 54.7 daily underlying O-D. These improvements are not a net carried-passenger forecast and do not eliminate the losses above.

The alternative 314/315 aircraft produces the same GNV connection losses and adds four small PVD-bound timing deteriorations. The five-minute buffered 518 departure adds four PIE-bound timing deteriorations. The selected 517/518 plan has the least existing-flight timing impact of the validated choices.

All opportunity figures use the pinned O-D snapshot `bts-db1c-6mo-jul2025-apr2026-v7`, competing itineraries, 30–240-minute connections and the existing one/two-stop circuity/choice model. They are **seat-uncapped, full-capture scenario measures**, not forecast loads or profit estimates. Multiple added legs can count the same traveler. The 139.6 XNA evening score exceeds CRJ200 capacity.

## Validation and limits

The complete batch passes structure, operating rules, bank alignment, pair spacing, cyclic continuity/overnight turns, maintenance RON cadence, destination RON coverage, planning reconstruction and physical gate/stand allocation with **zero effective operating errors and no hard-stop failures**. No passenger handling is assigned to stands. Stand use remains **16 claims / 3717 minutes**.

A GNV second-hub exception is recorded under the user's explicit PHF-service instruction and standing additional-hub authorization. It changes the city-tier hub-count finding only; no MX, RON, curfew, bank, turn, gate or aircraft constraint is waived.

Warnings become **183**, up from 182. The new finding is GNV's **08:25–20:42 departure gap (12h17)**. At four daily departures it enters the §2.6 city-gap check; that daytime coverage remains a future opportunity. This is not a new hard failure.

Aircraft timing does not certify a crew plan. The 517 aircraft day now runs **05:00 FLL → 23:30 GNV**, with **13h20 block**; 518 starts GNV at 04:30. A crew change/rest arrangement is required to operate the planned aircraft utilization. The 40-minute PHF turn and the repositioning costs are material operational limitations.

Exact replay confirms all 1152 released flight identities remain; only Flight 1739's clock changes. New flight numbers are 2155–2166 including earlier approved rounds. Latest-release regression passes **49 checks (13 Python, 36 JavaScript)** against v1.2.3. The new draft receives separate full constraint and replay checks. The live app and main remain v1.2.3 pending publication approval.

Current replay input: `config/optimizations/schedule_7_v1_2_4_accepted_rounds_1_3.json`, applying all approved v1.2.4 flying to the pinned released v1.2.3 canonical. The incremental accepted overlay is `config/optimizations/schedule_7_v1_2_4_accepted_round_3.json`. Current canonical and summary are in `data/schedules/schedule_7_v1_2_4_draft/`. The unchanged 1158-flight comparison input is preserved in `data/schedules/schedule_7_v1_2_4_round_2/`.

`config/proposals/schedule_7_v1_2_4_gnv_review.json` records the full PHF terminator inventory, candidate maintenance evidence, flight-level demand, lost/added connections and rejected/alternative timing costs. Earlier XNA-only findings are preserved as history, now resolved by this combined plan.

```bash
python scripts/analyze_schedule_7_v1_2_4_gnv.py
python scripts/analyze_schedule_7_v1_2_4_gnv.py --accept
bash scripts/run_latest_regression.sh
```
