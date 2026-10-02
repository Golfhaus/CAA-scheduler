# Schedule 7 v1.2.1: unpublished ground-hold draft

The latest cumulative draft is now feasibility checkpoint 02; see `schedule_7_v1_2_1_remaining_holds.md`. This document records the first optimization round. Regression checks target the cumulative draft.

This first v1.2.1 round inserts eight daily legs into Routes 701, 123, 321 and 129 using their existing aircraft. Publication is reserved to the user. The app default, release manifest and regression workflow remain on released v1.2.0. No v1.1 schedules are reconstructed or tested for this work.

## Proposed flying

All clocks are local: E = Eastern, C = Central. A rotation day is an aircraft position in a daily repeating line, rather than a weekday restriction.

| Route / line-day | Fleet | Flight | From | Departure | To | Arrival | Block minutes |
|---|---|---:|---|---|---|---|---:|
| 701 / A1 | MAX9 | 2099 | PHF | 09:20 E | PGD | 11:21 E | 121 |
| 701 / A1 | MAX9 | 2100 | PGD | 12:40 E | PHF | 14:41 E | 121 |
| 123 / AD13 | CRJ200 | 2101 | SYR | 08:40 E | BDL | 09:34 E | 54 |
| 123 / AD13 | CRJ200 | 2102 | BDL | 10:30 E | SYR | 11:24 E | 54 |
| 321 / AH10 | CRJ700 | 2103 | SYR | 16:50 E | RFD | 17:44 C | 114 |
| 321 / AH10 | CRJ700 | 2104 | RFD | 18:44 C | SYR | 21:38 E | 114 |
| 129 / AD19 | CRJ200 | 2105 | MCI | 14:50 C | DAY | 17:35 E | 105 |
| 129 / AD19 | CRJ200 | 2106 | DAY | 18:15 E | MCI | 19:00 C | 105 |

The only existing-flight retiming is Flight 2041, SYR–PIT, on Route 321: departure 22:14 → 22:25 E and arrival 23:20 → 23:31 E. It remains in the same SYR bank and leaves a 47-minute turn after the RFD return. All other existing flight clocks, aircraft assignments, flight numbers, route membership and line-days are preserved. Routes finish at their original overnight airports.

## Frequency and ground-time results

| Route | New pairing | Daily departures each way, before → after | Original hub hold | Added block | Remaining ground segments |
|---|---|---|---:|---:|---|
| 701 | PHF–PGD | 1 → 2 | 409 min | 242 min | PHF 44 / PGD 79 / PHF 44 min |
| 123 | SYR–BDL | 1 → 2 | 376 min | 108 min | SYR 46 / BDL 56 / SYR 166 min |
| 321 | SYR–RFD | 2 → 3 | 368 min | 228 min | SYR 44 / RFD 60 / SYR 47 min |
| 129 | MCI–DAY | 1 → 2 | 356 min | 210 min | MCI 51 / DAY 40 / MCI 55 min |

Route 321's usable interval grows by 11 minutes with the retiming. Total added block is 788 minutes (13:08). Three daytime tow/stand stays are eliminated; system stand use falls from 20 claims / 5,552 minutes to 17 / 4,714. No new stand claim is introduced. Route 123 retains a 2:46 SYR hold at a gate; the next departure bank leaves insufficient time for another round trip before the original PHF departure.

The screened bank-compatible slots support one round trip per targeted hold. The screen uses five-minute grids plus exact feasible boundary times, considers markets with one or two baseline departures from the hub, and combines retained timings for two different markets. It is a practical candidate search, not proof of a global optimum over continuous clocks or all multi-market combinations. Banks, inventory, curfews, turns and spacing are then checked by the authoritative whole-schedule validators.

## Demand support and alternatives

These are **allocated segment opportunity units, not forecast passenger loads**. Values are evaluated jointly with all eight additions and the retimed existing flight.

| Pairing | New outbound opportunity | New return opportunity | Local O-D pool, both directions |
|---|---:|---:|---:|
| PHF–PGD | 418.0 | 557.5 | 24.5 |
| SYR–BDL | 155.4 | 253.4 | 1.2 |
| SYR–RFD | 172.5 | 77.6 | 93.3 |
| MCI–DAY | 257.2 | 237.9 | 9.4 |

Connecting demand drives the PHF, BDL and inter-hub cases. The new MCI–DAY legs include 207.6 and 153.8 units on the middle segment of two-stop journeys, respectively. That middle segment is counted once as through opportunity, rather than both inbound and outbound.

One-at-a-time substitutions retain the other three selected round trips and use the full allocation model:

| Route | Alternative | Outbound / return opportunity | Decision |
|---|---|---|---|
| 701 | PHF–RDU | 444.0 / 498.5 | Strong alternative. PGD has slightly higher own-pair opportunity and adds 242 rather than 102 block minutes. RDU can improve allocation on other new flights, so PGD is a utilization and market choice rather than a network-score maximum. |
| 123 | SYR–BWI | 80.2 / 258.1 | BDL has stronger two-direction demand support. |
| 321 | SYR–BDL | 209.1 / 17.7 | RFD has a much stronger return and avoids a third BDL frequency alongside the morning addition. |
| 129 | MCI–BLV | 305.7 / 287.6 | Commercially stronger: 593.3 combined versus DAY's 495.0. DAY is retained to give a one-flight inter-hub pairing second service and add 210 rather than 130 block minutes. Choose BLV instead if commercial score takes priority over inter-hub availability. |

These four substitutions also have zero effective operating errors and hard-stop failures. Comparisons are schedule snapshots, not editable forecasts or independently optimized alternate networks.

Late SYR–DAY flying is blocked by DAY's full gate occupancy during 19:47–20:00 E within the required turn. SYR–MCI and SYR–JAX round trips require more time than the available interval once three minimum turns are included. Those options need broader changes beyond this minor-retiming scope.

## Model and limits

The demand source is pinned BTS DB1C Jul 2025–Apr 2026 v7. Each directional O-D pool is allocated across all eligible nonstop, one-stop and two-stop itineraries through BHM, DAY, JAX, MCI, PHF and SYR. Each transfer must be 30–240 minutes; total circuity must not exceed 2.25; visited airports must be distinct. Nonstop weight is 1/block²; connecting weight is 0.35^stops / elapsed² / circuity². Existing and added flights compete in the same allocation. The Excel connection rows expose each contribution to the eight new flights.

The model assumes full CAA capture and does not cap feeder or trunk seats. A score greater than seats therefore indicates opportunity to investigate, not an attainable load. Extra frequency reallocates demand from existing flights and cannot be treated as newly created travelers. Yield, operating costs, feeder capacity, overlapping airport catchments, surface travel and seasonal demand still need commercial assessment. Short regional sectors merit particular MAX9 cost review even when connection scores are high.

Crew duty/relief, recovery from delays and airport performance require separate assessment. All four new pairings use fleet types already present at their airports in the released schedule; this does not replace a runway/payload/gate-geometry check. DAY's new 40-minute turn has no extra recovery allowance. Bank-edge margins remain finite.

## Validation and reproduction

The draft has 1,104 legs, 181 routes and 20 lines; active aircraft positions and fleet inventory are unchanged. Structural, planning and overnight checks pass; there are zero effective operating errors and zero hard-stop failures. The report retains 187 operating warning findings and an unavailable airport-performance check, including the existing Line A 13-day exception.

```bash
python scripts/analyze_schedule_7_v1_2_1_holds.py
python scripts/build_schedule_7_v1_2_1_ground_holds.py
python -m unittest discover -s tests -p test_v121_ground_holds.py -v
```

The builder needs only the current released canonical and pinned repository inputs; the first command regenerates the optional broader candidate screen. The selected overlay is `config/optimizations/schedule_7_v1_2_1_round_1.json`. Generated feasibility exports live under ignored `builds/schedule_7_v1_2_1_feasibility_01/`. No draft appears in the app manifest until publication is authorized.
