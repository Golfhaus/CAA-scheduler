# Schedule 7 v1.2.3: Routes 327, 305 and 145 utilization review

Status: proposed and unpublished. Main/app remain on released v1.2.2. This review preserves the original round-one proposal and treats its additions as unapproved options.

## Recommendation

- **327: add a buffered morning PGD–JAX round trip.** PGD 05:55 → JAX 06:57; JAX 08:00 → PGD 09:02. No existing clock changes. Keep the prior SDF–DAY evening proposal as an independent round-one option. The morning turn increases PGD–JAX from one to two flights each way. It leaves 63 minutes at JAX and 53 minutes before the original PGD 09:55 flight. Compared with the highest-scoring 04:40 start/08:10 return, this timing retains about 85% of the joint opportunity score, reduces the JAX hold from 148 to 63 minutes, and gives the aircraft a longer overnight in PGD.
- **145: add morning PWM–PHF and midday SYR–BUF.** PWM 04:40 → PHF 06:24; PHF 07:04 → PWM 08:48. SYR 11:18 → BUF 12:04; BUF 12:44 → SYR 13:30. Flight 1853, SYR–HPN, moves five minutes later, from 14:05–14:59 to **14:10–15:04**. HPN–SYR 18:00–18:54 and SYR–ORH 19:35–20:33 remain unchanged. PWM–PHF rises from one to two daily flights each way. SYR–BUF rises from four to five; despite its higher frequency, its original 08:40–16:55 departure gap makes the midday addition useful. The tiny local SYR–BUF market is supported by substantial connecting opportunity.
- **305: keep the existing route in the recommended package; retain MCI–TUL as a conditional rebuild.** The strong loop is MCI 09:46 → TUL 10:44; TUL 11:25 → MCI 12:23, increasing one daily flight each way to two. It requires Flight 1448 HRL–MCI to move from 09:50–12:17 to **06:39–09:06**, plus a two-minute shift of MCI-B3 from 08:05–09:05 to **08:07–09:07**, retaining the 60-minute width and all existing assigned touches. Flight 1439 MCI–SYR 13:05–16:42 and Flight 1308 SYR–CLT 19:35–21:22 stay intact. Demand supports the TUL loop, but the HRL coverage cost prevents an unconditional recommendation.

## Interaction with the prior v1.2.3 draft

The new PWM–PHF turn passes by itself against v1.2.2, but fails fixed physical inventory when combined with the prior proposed 331 BWI–PHF morning turn. The combined allocator requires a 17th passenger gate at PHF; that cannot be accepted.

The coherent combined proposal therefore uses the **previously screened DAY morning alternative on 331**: BWI 05:43 → DAY 07:05; DAY 07:53 → BWI 09:15, followed by the unchanged BWI 10:05 originator. The evening BWI–DAY turn, CLT and SDF feeders, and proposed DAY-B9 21:05–22:05 remain as screened in round one. This changes an unapproved alternative; it does not retime any released flight on 331 or 332. It puts the added PHF flying on the currently single-frequency PWM pairing and expands the currently unserved BWI–DAY pairing.

## Added flying and demand evidence

All times below are local (these added legs are Eastern). Flight numbers are provisional in the **combined** proposal; standalone round two numbers differ because round one adds eight flights first.

The local O-D is pinned directional daily demand. Allocated local and connection columns are **seat-uncapped, full-capture relative-choice opportunity scores**, not expected passenger loads or load factors. They account for competing nonstop/one-stop/two-stop itineraries and frequency. Scores over aircraft capacity demonstrate strong relative opportunity, not the number actually carried. Summing scores across legs double-counts passengers using multiple listed flights; it is not net incremental traffic.

| Flight | Route / line-day | Flying | Current daily direction frequency | Local O-D | Allocated local | Connecting opportunity | Total opportunity |
|---|---|---|---:|---:|---:|---:|---:|
| 2137 | 327 / AK-3 | SDF 20:17 → DAY 21:05 | 1 | 0.2 | 0.1 | 43.7 | 43.8 |
| 2138 | 327 / AK-3 | DAY 21:55 → SDF 22:43 | 1 | 0.1 | 0.1 | 218.3 | 218.4 |
| 2139 | 327 / AK-3 | PGD 05:55 → JAX 06:57 | 1 | 2.8 | 1.4 | 589.2 | 590.6 |
| 2140 | 327 / AK-3 | JAX 08:00 → PGD 09:02 | 1 | 3.1 | 1.6 | 266.4 | 268.0 |
| 2141 | 145 / AD-35 | PWM 04:40 → PHF 06:24 | 1 | 8.0 | 3.6 | 114.8 | 118.4 |
| 2142 | 145 / AD-35 | PHF 07:04 → PWM 08:48 | 1 | 8.4 | 3.9 | 37.2 | 41.1 |
| 2143 | 145 / AD-35 | SYR 11:18 → BUF 12:04 | 4 | 1.1 | 0.2 | 187.0 | 187.2 |
| 2144 | 145 / AD-35 | BUF 12:44 → SYR 13:30 | 4 | 1.4 | 0.3 | 211.0 | 211.3 |

The PGD morning inbound reaches JAX’s early connection waves; its return draws inbound feed at JAX. PWM reaches PHF’s morning departures, with a smaller but useful reverse opportunity. BUF receives a midday SYR departure between the old early and late groups, and its new inbound reaches the SYR early-afternoon departure wave. Geographic-group scores and actual connecting-flight lists are saved for every evaluated added leg in the screen JSON.

## Route 305 tradeoffs

| Tested approach | Assessment |
|---|---|
| Add a turn before the unchanged HRL 09:50 originator | HRL–DAL 04:30–05:59 / 06:39–08:08 fits, but only 21.6/22.4 directional local opportunity and no modeled connections. HOU gives about 21 each way; AUS adds only about 12 each way after existing frequency competes. These are weaker uses of a CRJ700 than the hub turns. New-route demand/operating economics would need to justify them. |
| Fill the unchanged SYR 16:42–19:35 hold | No compliant loop fits with banks, 40-minute turns and pairing spacing. An earlier MCI–SYR/HRL–MCI cascade permits a ROC loop geometrically but fails SYR gate inventory. |
| HRL 04:30 start followed by an MCI–RFD turn | Strong added-flight opportunity (about 186 outbound / 450 inbound), but 18 modeled markets lose all valid itineraries and 11 have slower best journeys. Not selected. |
| Shift HRL to 06:39 and add MCI–TUL | About 80 outbound / 185 inbound opportunity, mostly connections; local TUL–MCI O-D only 1.6 each way. Physical/operating checks pass. Eight HRL-origin markets lose modeled availability, totaling **1.2 daily underlying O-D**, and 17 best journeys become slower. HRL–SYR/NEC remains available but its best journey is 191 minutes longer. HRL–RFD is 71 minutes longer. HRL’s longest daytime departure gap increases from **282 to 473 minutes**, with the remaining MCI departures at 05:50, 06:39 and 14:32. This is a real coverage compromise even though the warning count stays unchanged. |
| Add early HRL–MCI–HRL and rebuild the two following legs | Several clock variants pass physically, but pushing the sole MCI–SYR service to 18:45–19:05 removes **71 modeled markets, 110.5 daily underlying O-D**, largely midday NEC/GLC feed. Not selected. |

The eight lost markets in the conditional TUL option are HRL→HSV, AVL, CHA, TRI, CRW, ERI, TOL and FWA. Zero-demand rows are included in the availability count; the 1.2 figure sums the pinned O-D values, not passengers forecast to be lost. The corresponding MCI–OMA alternative serves a pairing already at four daily flights and has almost identical HRL damage, so TUL is preferable if the tradeoff is accepted.

## Utilization and verification

| Route | Released v1.2.2 | Combined recommended proposal |
|---|---|---|
| 327 | 5 legs; 5:59 block; PGD 09:55 → SDF 18:59 | 9 legs; 9:39 block; PGD 05:55 → SDF 22:43 |
| 305 | 3 legs; 6:51 block; HRL 09:50 → CLT 21:22 | 3 legs; 6:51 block; HRL 09:50 → CLT 21:22 |
| 145 | 4 legs; 3:54 block; PWM 09:30 → ORH 20:33 | 8 legs; 8:54 block; PWM 04:40 → ORH 20:33 |

Standalone round two adds six flights. The combined proposal adds 14 over the release, reaching **1142 flights**, with the same 181 routes, 20 lines and fleet counts. It passes structural, planning, bank/curfew/turn/spacing, cyclic overnight and gate/stand validation: **0 effective errors, 0 hard-stop failures, 182 warnings** (release: 183). Stand claims stay at 15; stand minutes fall from 4277 to **3771** through the prior DAY/BWI work. No operating overrides were introduced.

Against released v1.2.2, the combined model has **109 faster best itineraries**, and **zero markets losing all modeled availability**. Three best journeys become five minutes slower: RFD→HPN (204→209 minutes), CLT→HPN (199→204), ROC→HPN (134→139). These are the transparent cost of the five-minute Flight 1853 delay. The model finds newly available markets with 597.0 summed underlying directional O-D; this is a coverage statistic, not expected incremental bookings.

Route 145’s new PHF turn has 40 minutes at PHF, 42 before the original PWM originator, and two exact 40-minute turns around BUF. These comply but leave limited recovery margin. The nine-minute HPN-delay sensitivity gives four additional minutes after BUF at the cost of four more minutes on those three HPN journeys. It is saved as an alternative rather than silently replacing the five-minute choice.

Aircraft utilization does not prove crew-duty feasibility. The combined 327 aircraft day runs 05:55–22:43 and 145 runs 04:40–20:33; crew coverage and maintenance staffing must be planned separately. All aircraft continuity, destination overnight coverage and existing maintenance-cadence checks pass. A capacity-constrained assignment/revenue-cost model remains necessary to forecast loads and economics.

## Saved inputs and reproduction

- Released base: `data/schedules/schedule_7_v1_2_2/canonical_schedule.json`; SHA256 `750a112257e3829f9f831a258257cc753aed35e4e9e4ef0e8791143739524499`.
- Recommended standalone overlay: `config/proposals/schedule_7_v1_2_3_round_2.json`.
- Coherent combined overlay against v1.2.2: `config/proposals/schedule_7_v1_2_3_rounds_1_and_2_day_morning.json`.
- Conditional Route 305 overlay: `config/proposals/schedule_7_v1_2_3_route_305_tul_conditional.json`.
- All shortlisted timings, failed gates, demand allocations and itinerary audits: `config/proposals/schedule_7_v1_2_3_utilization_screen.json`.
- Reproduction: `python scripts/analyze_schedule_7_v1_2_3_utilization.py`; use `--fresh` to rescreen rather than resume the pinned checkpoint. The generated combined canonical is written to ignored build output. Neither the default manifest nor main/app release files are changed.

> Update, October 7, 2026: The user approved the combined recommendation, including Route 305. Implementation is captured in `config/optimizations/schedule_7_v1_2_3_accepted_rounds_1_2.json` and the current v1.2.3 draft canonical. This report retains the pre-approval analysis; see `docs/schedule_7_v1_2_3_round_3_plan.md` for current state. Publication remains reserved to the user.
