# Schedule 7 v1.2.1: remaining five-hour daytime holds

This second unpublished round builds on the first v1.2.1 ground-hold draft. It adds eight daily legs using four existing aircraft positions and preserves all first-round flying. Publication remains reserved to the user; the app default and release manifest are still v1.2.0.

## Complete hold inventory

The scan includes consecutive flights within every route at airports whose role is `hub` or `focus_city`: BHM, DAY, JAX, MCI, PHF and SYR. It includes every daytime gap of at least 300 minutes, regardless of whether the aircraft is assigned a gate or stand. Overnight stays between route-days remain outside this daytime-fill exercise.

| Route | Line/day | Fleet | Hub | Local hold | Duration | Action |
|---:|---|---|---|---|---|---|
| 322 | AH11 | CRJ700 | SYR | 05:36–11:20 E | 5:44 | Defer: weak ABE option; stronger BWI option fails gates |
| 118 | AD8 | CRJ200 | MCI | 13:17–18:55 C | 5:38 | Add BLV round trip |
| 122 | AD12 | CRJ200 | SYR | 05:38–11:08 E | 5:30 | Defer: no usable round trip within fixed banks and onward turns |
| 323 | AH12 | CRJ700 | SYR | 16:50–22:18 E | 5:28 | Add BWI round trip; following flight +7 minutes |
| 147 | AD37 | CRJ200 | SYR | 10:41–16:00 E | 5:19 | Add PIT round trip; incoming flight −3 minutes |
| 151 | AE1 | CRJ200 | MCI | 12:07–17:15 C | 5:08 | Add XNA round trip |

No other hub or focus-city daytime hold meets the threshold after round one. After round two, only Routes 322 and 122 remain above five hours.

## New flying

E = Eastern; C = Central. Line/day identifies a position in a daily repeating rotation, not a weekday restriction. Demand values below are **uncapped allocated opportunity units, not forecast passengers**. Every value is recomputed jointly using all original flights, all sixteen v1.2.1 additions and all three retimings.

| Route | Flight | From | Local departure | To | Local arrival | Block min | Opportunity | Daily pair frequency each way |
|---:|---:|---|---|---|---|---:|---:|---|
| 118 | 2107 | MCI | 15:25 C | BLV | 16:30 C | 65 | 299.7 | 2 → 3 |
| 118 | 2108 | BLV | 17:10 C | MCI | 18:15 C | 65 | 278.6 | 2 → 3 |
| 151 | 2109 | MCI | 13:45 C | XNA | 14:42 C | 57 | 152.5 | 1 → 2 |
| 151 | 2110 | XNA | 15:38 C | MCI | 16:35 C | 57 | 116.5 | 1 → 2 |
| 147 | 2111 | SYR | 11:18 E | PIT | 12:24 E | 66 | 158.8 | 2 → 3 |
| 147 | 2112 | PIT | 13:04 E | SYR | 14:10 E | 66 | 86.1 | 2 → 3 |
| 323 | 2113 | SYR | 18:55 E | BWI | 20:00 E | 65 | 125.6 | 1 → 2 |
| 323 | 2114 | BWI | 20:40 E | SYR | 21:45 E | 65 | 28.2 | 1 → 2 |

The second round adds 506 minutes (8:26) of daily block. Combined with round one's 788 minutes, v1.2.1 adds 1,294 minutes (21:34), sixteen legs and eight round trips. Active aircraft positions, routes, lines, fleet inventories and route-ending airports are unchanged.

New ground segments, hub / destination / hub, are:

- Route 118: 128 / 40 / 40 minutes.
- Route 151: 98 / 56 / 40 minutes.
- Route 147: 40 / 40 / 110 minutes; the incoming flight arrives three minutes earlier.
- Route 323: 125 / 40 / 40 minutes; the following flight leaves seven minutes later.

## Minor timing changes

Flight 1607 PIT–SYR changes from 09:35–10:41 to 09:32–10:38 E (−3 minutes). Its prior PIT turn is exactly 40 minutes. This lets the new PIT return reach SYR at 14:10, five minutes before Bank 4 closes. Flight 2043 SYR–ABE changes from 22:18–23:10 to 22:25–23:17 E (+7 minutes), allowing a 40-minute turn after the new BWI return. Both changes retain the existing bank assignments. The first-round eleven-minute retiming of Flight 2041 SYR–PIT remains.

Every other existing flight number, ID, fleet, route membership, line/day and clock is preserved. The selected changes do not modify bank windows, physical gate/stand inventory, operating policies or curfews.

## Selection and deferred cases

MCI–BLV and MCI–XNA are the leading demand candidates for their respective usable slots. BLV now receives the third service deferred in favor of MCI–DAY during round one. At MCI, moving the new flights five minutes earlier forfeited substantial connection allocation: BLV's outbound fell from about 300 to 219 units; XNA's return fell from about 116 to 81. The selected bank-aligned times preserve that feed, with 40-minute final turns.

For the midday SYR hold, BWI and PIT have similar isolated scores. PIT is chosen so the late route can give the one-flight BWI market its second service. This spreads the additions rather than adding two BWI round trips. BWI has stronger late-slot feed than BDL, PIT or PVD. Its return is still relatively weak at 28.2 units versus 125.6 outbound; the commercial case needs review of both directions. BWI arrival cannot be moved five minutes earlier to 19:55 without stranding existing passenger gate touches. The selected 20:00 arrival passes the full allocator.

Route 322 has one gate-screened ABE round trip with only 0.7 outbound and 31.4 return opportunity in the isolated screen. The stronger SYR–BWI morning option (about 65.5 / 203.8 before other additions) was also evaluated with the authoritative whole-schedule rules. Both unchanged and nine-minute-delayed following-flight cases fail BWI fixed-gate and passenger-touch checks. A later ABE option with better outbound feed fails SYR gates. The draft therefore keeps Route 322's hold rather than add an almost empty outbound leg or relax physical rules.

Route 122 has no round trip with unchanged clocks. The earliest feasible post-arrival departure misses the first SYR bank, while the next return bank begins at 10:30, after the 10:28 latest return needed for its original 11:08 departure. Delaying SYR–SWF then consumes its original 40-minute SWF turn. Delaying the following SWF–DAY flight misses DAY's arrival bank: its original 14:19 arrival is already one minute before the 14:20 close. A useful modification requires changes beyond minor alignment of this route, so the hold remains.

The screen considers one or two baseline departures from the relevant hub, timing grids plus exact boundaries, minimum turns, bank windows, spacing and gates. It also searches retained combinations of two different round trips. No two-round-trip plan was found for these slots. This is a practical search, not a global optimum proof. Gate-screen rejections on the early SYR cases were challenged with the full allocator before deferral.

## Validation, demand limitations and reproduction

The cumulative draft has 1,112 legs, 181 routes and 20 lines. Structural, planning and overnight checks pass. There are zero effective operating errors and zero hard-stop failures. There are 183 effective operating warning findings and the existing unavailable airport-performance check. Several new turns are exactly 40 minutes; crew relief, recovery from delays, runway/payload and gate geometry require separate assessment.

Stand use falls from 17 claims / 4,714 minutes after round one to 15 / 4,277. Versus released v1.2.0, that is five fewer claims and 1,275 fewer stand minutes. No new stand claim is introduced.

The pinned BTS DB1C Jul 2025–Apr 2026 v7 model allocates each directional O-D pool across all eligible nonstop, one-stop and two-stop choices through all six hubs/focus cities. Transfers are 30–240 minutes, circuity ≤2.25 and visited airports distinct. Connecting weights are 0.35^stops / elapsed² / circuity²; nonstop weights are 1/block². Middle segments receive through allocation once. The workbook supplies contribution rows for all sixteen additions and formula-linked local/inbound/outbound/through totals.

The model assumes full CAA capture, does not cap feeder or trunk seats, and omits fares, yield, cost, competitor share, seasonality and surface travel. Extra frequency reallocates existing O-D demand; it does not create new travelers. Scores above seat counts indicate opportunities for further investigation, not feasible loads.

```bash
python scripts/analyze_schedule_7_v1_2_1_remaining_holds.py
python scripts/build_schedule_7_v1_2_1_remaining_holds.py
python -m unittest discover -s tests -p test_v121_ground_holds.py -v
```

The builder reconstructs round one from the current released canonical before applying `config/optimizations/schedule_7_v1_2_1_round_2.json`. It does not require the ignored search output. Generated files are under `builds/schedule_7_v1_2_1_feasibility_02/`. Draft regression tests now target the latest cumulative checkpoint only; older v1.1 schedules remain excluded. Publishing still requires the user's decision.
