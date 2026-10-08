# Schedule 7 v1.2.4 — 116/117 XNA overnight review

> Follow-up: the user authorized replacing GNV's lost overnight with PHF service. The fully validated combined plan is now implemented in the unpublished draft. Route 517 terminates in GNV, Route 518 originates GNV–PHF, and 115/116/117 adopt the JAX/XNA plan. See `docs/schedule_7_v1_2_4_gnv.md`. The analysis below records the earlier round-two finding and uses its preserved 1158-flight snapshot.

**Timing and demand support the idea, but Route 116's MCI overnight is currently required for line AD's maintenance cadence.** The XNA scenario remains analysis only. The approved 126 MLB–JAX and 308 CLT–MCI additions are now implemented alongside 350 in the unpublished 1158-flight draft; 518 is retained.

## XNA timing

Routes 116 and 117 are CRJ200 line AD, days 6 and 7. Existing Route 116 ends CAK–MCI at **20:45 CT**, including the previously approved CAK service. Route 117's first flight is **1634 MCI–OMA, 07:15–08:04 CT**. Neither would need to move.

One physically feasible two-day extension is:

| Route | Proposed flight | Local times, all CT | Aircraft ground time |
|---|---|---|---|
| 116 | MCI–XNA | 21:25–22:22 | 40-minute turn after CAK arrival |
| 117 | XNA–MCI | 05:30–06:27 | 7h08 XNA RON; 48 minutes before the existing 07:15 OMA departure |

Each leg is **57 minutes**, adding 1h54 block across the two aircraft days. The evening departure fits MCI-M11 and the morning arrival fits MCI-B2. The latest possible XNA departure without moving OMA is **05:38**, arriving MCI 06:35 and leaving the 40-minute minimum. The selected 05:30 departure provides an eight-minute aircraft-turn buffer above minimum. Planned morning bank alignment permits departures from XNA **05:28–05:38** for this bank; an earlier B1 return is also possible.

The full scenario passes structure, continuity, cyclic overnight turns, planning reconstruction, curfews, spacing, bank alignment and fixed gates/stands. Its **only unresolved operating finding is maintenance-base RON cadence**. It adds no inventory or physical exception.

## Demand and coverage

XNA currently has **two MCI flights each way**, both XNA departures in the afternoon (14:00 and 15:38). BHM departures are 04:30 and 21:00. This would add a third MCI flight each way and XNA's first MCI originator.

| Added leg | Pinned local O-D per day | Added local allocation | Connecting opportunity | Total opportunity |
|---|---:|---:|---:|---:|
| MCI–XNA evening | 0.6 | 0.2 | 139.4 | 139.6 |
| XNA–MCI morning | 0.6 | 0.2 | 30.2 | 30.4 |

These are seat-uncapped, full-capture relative-choice opportunities, not forecasts. The 139.6 evening figure exceeds CRJ200 capacity and must not be interpreted as carried passengers. Existing competing flights and itineraries are included.

The evening flight collects TEX, FLP, GLC, APP and other flows, led by HOU, BNA, SFB, AUS and PIE. The morning return opens MCI's 07:15 wave, including the same aircraft's OMA flight, plus FLL, IND, MKE and other onward service. It also reaches later MCI departures inside the 30–240-minute connection window. Morning modeled opportunity is concentrated in FLP, GLC and UMP, which provides useful coverage beyond the BHM originator. The additive timetable audit loses no connected market or fastest-itinerary quality; **21 markets gain a faster best itinerary**.

## Why the MCI RON matters

XNA is **not an MX base** in the active city metadata. Active maintenance/RON target stations are the five hubs, BHM, SFB, RFD, FLL, DAL, PIE and BNA. The embedded operating policy permits at most 10 consecutive non-target RONs, with one standing grace day. It credits **overnights**, so Route 117's morning MCI visit does not replace maintenance RON credit.

The relevant line AD sequence is:

| Aircraft day | Route | Current target RON |
|---:|---:|---|
| 38 | 148 | DAY |
| 6, after cycle wrap | 116 | MCI |
| 15 | 125 | DAY |

Removing day 6's MCI overnight creates **16 consecutive non-target RONs**: days 39–40 and 1–14. That exceeds even the 11-day grace ceiling. Line AD's longest non-target run is currently **9**, with no grace needed. Other target RONs remain at days 23, 25, 26 and 28, so the issue is the specific day-38-to-day-15 portion of the cycle, not a lack of maintenance bases anywhere on the line.

The standing instructions also require at least one hub/focus-base RON in each line. That broad requirement remains met, but the tighter rolling cadence fails. This finding is a scheduler policy constraint, not an aircraft-specific maintenance work-order assessment; actual task durations and crew plans are outside the timetable model.

## Replacement-RON sensitivity

A replacement JAX overnight one day earlier was checked: extend 115 GNV 20:42 → JAX 21:19, begin 116 JAX 04:30 → GNV 05:07, and move its existing GNV–JAX flight from 05:10–05:47 to **05:47–06:24**. The later JAX–DAB departure stays at 07:30. Combined with XNA, this restores line AD's longest non-target run to 9 and passes physical timing and gate checks.

However, it removes **GNV's only terminating route**, failing destination RON coverage. It therefore is **not a compliant replacement** by itself. No policy exception or partial implementation was made. A compliant XNA addition needs a broader line/RON reassignment that replaces the lost maintenance night while retaining destination overnight coverage.

Recommendation: **keep 116's MCI terminator for now**. Preserve XNA as a worthwhile conditional option for a future RON/line reconstruction, rather than waive the maintenance rule. The two requested approved extensions are implemented; 116/117 and 115 remain unchanged.

Inputs and reproducibility: `config/optimizations/schedule_7_v1_2_4_accepted_rounds_1_2.json` rebuilds the accepted draft from released v1.2.3. `config/proposals/schedule_7_v1_2_4_xna_conditional.json` contains the blocked XNA-only overlay. `config/proposals/schedule_7_v1_2_4_xna_review.json` contains full candidate validation, maintenance-day evidence and flight-level demand. Rule sources: embedded `operatingPolicy.rollingRonWindowDays`, `rollingRonGraceDays` and `ronTargetCities`; standing instructions §2.1 / Lesson 31 and §2.8. No XNA change is approved or published.
