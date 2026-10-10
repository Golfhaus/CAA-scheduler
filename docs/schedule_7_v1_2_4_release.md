# Schedule 7 v1.2.4

Published October 10, 2026 at the user's instruction: “Push the existing recommendations as v1.2.4 to the main branch of the app.” The accepted five-round draft is released in full, including the revised PHF/MCI exchange. Deferred SYR and other hub-swap alternatives are excluded.

The release adds **18 flights on existing aircraft**, bringing Schedule 7 to **1,170 flights, 181 routes, 20 lines and 562 directed markets**. Fleet counts, aircraft-days and gate/stand inventory remain unchanged. Current route numbers below include the approved CRJ700 line reconstruction.

| Flight numbers | Current routes | Added flying, local times |
|---|---|---|
| 2155–2156 | 350 | ELP 18:27 MT → MCI 21:43 CT; MCI 22:33 CT → ELP 23:49 MT |
| 2157–2158 | 126 | MLB 20:00 → JAX 20:52; JAX 21:42 → MLB 22:34 ET |
| 2159–2160 | 308 | CLT 20:30 ET → MCI 21:43 CT; MCI 22:45 CT → CLT 01:58 ET next day |
| 2161–2164 | 115 / 116 / 117 | GNV 20:42 → JAX 21:19 ET; JAX 04:30 → GNV 05:07 ET; MCI 21:25 → XNA 22:22 CT; XNA 05:30 → MCI 06:27 CT |
| 2165–2166 | 517 / 518 | PHF 21:45 → GNV 23:30; GNV 04:30 → PHF 06:15 ET |
| 2167–2168 | 125 | SYR 06:06 → ROC 06:45; ROC 07:25 → SYR 08:04 ET |
| 2169–2170 | 157 | OMA 20:30 → BHM 22:38; BHM 23:23 → OMA 01:31 CT next day |
| 2171–2172 | 323 / 337 | PHF 20:45 ET → MCI 22:22 CT; MCI 20:24 CT → PHF 00:01 ET next day |

## PHF exchange, timing and line changes

The last two flights double PHF–MCI from one to two flights each way. The source routes were **337 and 345** in the round-four input; after reconstruction they are **323 / AK-3 and 337 / AL-8**. Source-to-target mappings are explicit in the accepted round-five overlay. AH / AK / AL / AS retain 41 aircraft-days and reclose into **9 / 9 / 12 / 11-day cycles**. PHF has 4h29 overnight before route 338; MCI has 8h53 before route 324.

Seven existing flights change clock relative to released v1.2.3:

| Flight | Direction | Released v1.2.4 times, local | Shift |
|---|---|---|---:|
| 1739 | GNV–JAX | 05:47–06:24 ET | +37 min |
| 1811 | SYR–PVD | 08:44–09:47 ET | +9 min |
| 1404 | ELP–MCI | 11:28 MT–14:44 CT | −12 min |
| 1319 | MCI–CMH | 15:24 CT–18:14 ET | −16 min |
| 1320 | CMH–MCI | 18:54 ET–19:44 CT | −16 min |
| 1784 | XNA–MCI | 13:57–14:54 CT | −3 min |
| 1589 | MFE–MCI | 12:19–14:54 CT | −1 min |

Every existing flight ID, number, fleet and city pair is preserved. All other existing clocks are preserved. XNA and MFE retain 30-minute connections to the retimed CMH departure. PHF–MCI retains a 33-minute connection to the 22:55 MCI–SAT flight. MCI-B7 shifts to **14:44–15:44 CT** and MCI-B10 to **19:44–20:44 CT**; PHF gains the **00:00–01:00 ET** arrival bank. The authorized GNV additional-hub exception from earlier draft approval remains; no physical gate, turn, curfew or maintenance requirement is waived.

## Validation and service tradeoffs

Structure, operating hard stops, planning, overnight turns and physical gates/stands pass, with **zero effective operating errors** and **179 advisory findings**. Stand use is **16 claims / 3,717 minutes**, including PHF's 2 / 142; no passenger handling occurs on stands. §2.6 Check A passes; the repaired exchange adds no Check B finding and worsens no departure gap compared with its round-four input. Full line maintenance cadence passes.

The repaired PHF exchange improves 25 fastest directional itineraries and slows 31 by 1–16 minutes, without removing all valid connections from any previously connected market. PHF–MCI / MCI–PHF modeled opportunity is 90.1 / 28.9. These are seat-uncapped relative-choice comparisons, not forecast passenger loads, incremental demand or profit. The eastbound flight cannot feed the first 04:30 PHF departures because a 269-minute wait exceeds the 240-minute connection ceiling. Arrival exactly at the 00:01 cutoff and the 33-minute SAT connection offer little delay margin. Aircraft feasibility is separate from detailed crew duty/rest and maintenance-task planning. Earlier approved CLT and OMA turns retain their after-midnight arrivals; the new 00:01 cutoff applies to the revised hub exchange.

The release's PHF connection report measures whole-timetable one-stop coverage between MDT/PIT/CHS/PVD and MCI: **5/5 cities have direct PHF round trips; 4/8 directional cross-group pairs connect**, all in the eastern-feeder-to-MCI direction. It is not a claim that midnight PHF arrivals feed an onward wave. Full one/two-stop demand and cumulative connection tradeoffs remain in the accepted draft report and per-round analyses.

The latest-only regression suite passes **49 checks (13 Python, 36 JavaScript)** against v1.2.4. It verifies exact approved additions and retimings, route reconstruction, bank/policy changes, every artifact's release reproduction, gates, overnight continuity, planning, two-stop demand accounting and the web UI helpers. Older released schedules are not regression tested. The static app build contains **14 selectable schedules and 145 data files**, with v1.2.4 as the default.

Authoritative configuration: `config/optimizations/schedule_7_v1_2_4.json`. Replay: `config/optimizations/schedule_7_v1_2_4_accepted_rounds_1_5.json` applied to pinned released v1.2.3. Final package: `data/schedules/schedule_7_v1_2_4/`. The package's flying exactly matches the accepted 1,170-flight draft; release metadata and provenance are regenerated. Future work must start from this **released v1.2.4 canonical**, not an earlier draft or analysis snapshot.

```bash
PYTHONPATH=src python -m caa_scheduler build-optimization-release config/optimizations/schedule_7_v1_2_4.json
bash scripts/run_latest_regression.sh
PYTHONPATH=src python -m caa_scheduler build-web --output dist
```
