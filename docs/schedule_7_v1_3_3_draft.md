# Schedule 7 v1.3.3 working draft — PIE connecting-service initiative

**Unpublished, proposal under review.** Based on the published 1,229-flight Schedule 7 v1.3.2. No changes to `main`, released v1.3.2, or the web application's default.

## What the baseline audit actually found

The app's 30–240-minute connection enumeration and 2.25× geographic suitability check show:

| Market | PIE outbound | Reverse | O-D/day from PIE |
| --- | --- | --- | ---: |
| PIE–IND | two stops | one stop via MCI | 106.0 |
| PIE–AUS | two stops | one stop via MCI | 96.8 |
| PIE–BLV | no geographically reasonable option (raw two-stop options exist) | one stop via MCI | 77.8 |
| PIE–GRR | **already one stop via MCI** (1074→2181; 86-minute change) | **two stops** | 39.1 |

The GRR asymmetry is opposite the user’s initial description. GRR→PIE remains a separate opportunity, not solved by the first proposal. Existing afternoon PIE→JAX flight 1536 arrives 14:24 ET, after JAX's useful IND/AUS/BLV flights; evening PIE→MCI arrives after MCI's afternoon outbound connections.

## Preferred single-route alternative — R514

Replace the existing afternoon **PIE–SYR–PIE** pair (flights 1230 and 1227) on **CRJ900 route 514, line AG/day 4**, with a **PIE–MCI–PIE** round trip. Preserve the PIE→PHF→PIE morning pair and PIE→JAX terminator. Times are local:

| Sector | Departure | Arrival | Treatment |
| --- | --- | --- | --- |
| PIE–PHF | 06:35 ET | 08:34 ET | unchanged |
| PHF–PIE | 09:15 ET | 11:14 ET | unchanged |
| PIE–MCI | **12:10 ET** | **13:46 CT** | new, replaces PIE–SYR |
| MCI–PIE | **14:44 CT** | **18:20 ET** | new, replaces SYR–PIE |
| PIE–JAX | 20:14 ET | 21:08 ET | unchanged |

The MCI arrival fits B6 (13:05–14:05 CT) and the departure fits B7 (14:44–15:44 CT). PIE morning turn 56 minutes; MCI turn 58 minutes; PIE final turn 114 minutes. No added aircraft day or route; the candidate remains 1,229 flights / 184 routes / 17 lines.

All **nine** independent PIE departure × MCI return timing combinations screened passed the native structural, operating, maintenance/overnight, planning and physical gate checks. Preferred 12:10/14:44 option selected on the strength of a later but still bank-compliant PIE departure, three new geographically reasonable one-stop markets and competitive overall elapsed time.

## Network results for the preferred option (vs. released v1.3.2)

- **12 geographically reasonable directional direct/one-stop coverage gains; one loss**.
- **9 faster and 5 slower fastest reasonable journeys**.
- PIE→IND one-stop appears, total 6h45m; fastest overall remains 5h39m on its existing two-stop BHM/DAY itinerary. One fewer stop, not a faster arrival.
- PIE→AUS one-stop 6h17m, improving best feasible journey by 72 minutes.
- PIE→BLV gains a geographically reasonable one-stop in 5h20m where none existed.
- PIE→GRR retains existing reasonable MCI one-stop; GRR→PIE remains two stops.
- **Loss:** FWA→PIE loses its one-stop coverage (underlying O-D 11.4/day), though its fastest two-stop journey remains 5h14m.
- Other slower fastest journeys include PIE→HVN (261→376 minutes), PIE→ALB (244→249), ALB→PIE (249→258), HPN→PIE (259→268), HVN→PIE (259→268). These passenger-network costs require review; do not claim no adverse effect.
- All directional O-D values describe underlying demand, **not load forecasts**.

Evidence: `outputs/schedule_7_v1_3_3_pie_review/baseline.json`, `r514_physical_screen.json`, `r514_network_screen.json`. Preferred saved candidate at `r514_730_884_canonical.json`, reproducible from `config/proposals/schedule_7_v1_3_3_r514_pie_mci.json`. Draft build script: `scripts/build_schedule_7_v1_3_3_draft.py`.

## User decision and remaining v1.3.3 priorities

**R514 PIE–MCI–PIE is accepted for retention in the unpublished v1.3.3 working draft.** The user explicitly directed that this change remain in the draft despite the reviewed connectivity tradeoffs. Do not revert it when evaluating subsequent revisions.

**Future optimization priorities:** (1) improve **PIE→HVN**, whose directional O-D demand is 32.4/day and fastest journey deteriorates from 4h21m to 6h16m under R514; (2) add a geographically reasonable **GRR→PIE one-stop** journey, while retaining the existing PIE→GRR one-stop. These are future adjustments, *not* prerequisites for keeping R514 in the draft. FWA→PIE remains a documented loss of its only one-stop but retains the 5h14m fastest two-stop journey.

**Do not publish v1.3.3 to main until separately authorized.** Assess future alterations against the full current v1.3.3 working draft and released v1.3.2 baseline, enforcing unchanged gate, bank, maintenance, curfew, line and stand limits.
