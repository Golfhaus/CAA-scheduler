# Schedule 7 v1.4.2 — tactical candidate validation (October 20, 2026)

**Scope:** unpublished draft from released v1.4.1. No spare aircraft released. The builder `scripts/build_schedule_7_v1_4_2_draft.py` applies the reversible MCI overlay and emits a 1,266-flight draft and operating reports. The GitHub Actions native test completed successfully, including combined retimings.

- R304 flight **1357 BLV–MCI** shifts +6 minutes, 10:31–11:35. MCI–HOU #1099 departs 15:35, producing a 240-minute MCI connection.
- R705 flight **1077 MCI–BNA** shifts -11 minutes, 14:44–16:13. OMA–MCI #1639 arrives 10:44, producing a 240-minute MCI connection.
- Structural validation: **pass**; overnight: **pass**; planning: **pass**; gates: exported; operating: **zero effective errors**. Both individual screens and combined screen clean.

Independent passenger network comparison, geographically reasonable direct/one-stop coverage vs published v1.4.1:

| Measure | Result |
|---|---:|
| New directional reasonable markets | 3 |
| Lost directional reasonable markets | 0 |
| Faster fastest geographically reasonable journeys | 27 |
| Slower fastest geographically reasonable journeys | 0 |

New reasonable coverage: **BLV→HOU** (52 O-D/day; fastest 469→413 minutes), **OMA→BNA** (35.1/day; previously no reasonable routing; new 378 minutes) and **BLV→CAK** (26.6/day; fastest 660→429 minutes). Reverse directions **HOU→BLV and BNA→OMA** remain unsolved.

**Next construction tasks:** attempt productive BNA–BHM patterns that connect BNA↔OMA and BNA↔ECP, BHM–RDU return that joins HVN, and DAY–SRQ return that joins GRR. Limit any added aircraft to three; validate each route's whole cyclic line, passenger connection impact, gate/stand inventory and critical period utilization. Those proposals are *not yet part of this tactical draft*. Main still points at v1.4.1. 
