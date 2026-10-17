# Schedule 7 v1.3.2 — low-utilization CRJ200 group review

Updated October 16, 2026. **Working draft only. Do not publish.**

## Scope and objective

User clarification: improve productive flying on **R160, R176, R146, R158 and R107**; retain the already-improved R125 unless there is an independently useful change. Aircraft reduction is a welcome possible side effect, **not a priority or condition**. All six routes are CRJ200; avoid adding low-demand late flying solely to raise block hours.

## Validated selected change: R146

Adopt the evening FSD–MCI–FSD round trip on line AI/day 3. Retain all original sectors, advance original MCI–FSD by 30 minutes, and use the 20:45–21:45 MCI M11 arrival bank and 22:15–23:15 M12 departure bank.

| Flight | Sector | Local departure | Local arrival | Change |
| --- | --- | --- | --- | --- |
| 1677 | MCI–FSD | 18:25 CT | 19:36 CT | 30 min earlier |
| 2231 | FSD–MCI | 20:16 CT | 21:27 CT | new |
| 2232 | MCI–FSD | 22:15 CT | 23:26 CT | new |

R146 increases from five to seven flights and **5h27 to 7h49 total block** (+2h22). The new FSD–MCI leg adds 44 minutes inside 06:00–22:00; the return after 22:00 is outside that critical window. R146 remains in FSD overnight for the following route-day. No extra aircraft or stand claims.

App-equivalent network audit versus the validated R144-stage baseline: **10 geographically reasonable direct/one-stop coverage gains, one loss, 22 fastest journeys improved and eight slower**. Gains include BNA–FSD (O-D 19.2/day, fastest improves from 9h12 to 3h55), SFB–FSD (17.4/day, 8h17 to 5h21), AUS–FSD (6.7/day, 10h16 to 5h16), and HOU–FSD (6.1/day, 10h16 to 5h21). Loss: ATW–FSD one-stop market (0.7/day). RFD–FSD fastest grows 35 minutes (O-D 26.4/day), PIE–FSD 90 minutes (10.8/day); remaining slower markets are preserved in the network audit. O-D values are **market demand, not a flight-load forecast**.

The accepted working schedule is reproducible through `scripts/stage_schedule_7_v1_3_2_selected.py`, using `config/optimizations/schedule_7_v1_3_2_r146_selected.json` atop the separately validated R144 proposal. GitHub Actions run [38937682003](https://github.com/Golfhaus/CAA-scheduler/actions/runs/38937682003) passed all staging, network-audit, regression and artifact-push steps. Validated selected canonical: `outputs/schedule_7_v1_3_2_selected/canonical_schedule.json` (**1,227 flights**); the released app and standard five-round cumulative canonical remain unchanged.

## Alternatives rejected or deferred

- **R107**: CAK–SYR–CAK late turn passes native validation, but local O-D is only ~1.3/1.4 passengers/day, provides zero reasonable geographic coverage gains and worsens BDL–CAK's fastest itinerary from 2h46 to 5h38 for a market at 9.6/day. Do **not** select merely to increase block hours.
- **R160**: late PWM–SYR–PWM would compete almost exactly with existing SYR–PWM flight 2052 at 22:20. Pairing-spacing validation fails. Review more substantial bank or line changes before attempting.
- **R158**: extra ALB–SYR–ALB mid-hold pair conflicts with existing ALB–SYR around 18:10, triggers spacing errors and produces three off-gate passenger touches at SYR. Do **not** waive gate constraints.
- **R176**: 179-minute PHF hold and existing GSO/CAE/JAX pattern lack an independently validated commercially useful round-trip addition. Rebuild or swap existing flying rather than force a very-short-haul filler sector.
- **R125**: the earlier PVD–BWI–PVD addition is retained; nine flights and 9h20 block.

## Further exploration

For R160, R158, R176 and R107, examine daytime retimings or exchange of entire bank-to-bank segments with neighboring CRJ200 lines, **including adjacent routes** where necessary. Candidate selection should rank reasonable market reach, fastest journey improvements, daytime (06:00–22:00) block, and avoidance of poor frequency duplication above absolute block hours. Compare every proposal with the entire 1,227-flight selected baseline using the established app itinerary enumerator, not just local O-D or flight-count totals.

**Governance:** No authorization to release v1.3.2. `main` and application default remain v1.3.1.
