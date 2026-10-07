# Schedule 7 v1.2.3

Published October 7, 2026 at the user's instruction: "Publish the suggested changes as v1.2.3 in the main branch of the app."

This release adds **24 daily flights** on existing aircraft, including all previously approved v1.2.3 work and the recommended Route 114 PHF and Route 169 DAY extensions. The optional Route 350 MCI and Route 163 extensions remain proposals.

| Route / line-day | Fleet | Added flying, local times |
|---|---|---|
| 331 / AK-7 | CRJ700 | BWI 05:43 → DAY 07:05; DAY 07:53 → BWI 09:15; BWI 19:52 → DAY 21:14; DAY 21:54 → BWI 23:16 ET |
| 340 / AL-4 | CRJ700 | CLT 19:48 → DAY 21:05; DAY 21:55 → CLT 23:12 ET |
| 327 / AK-3 | CRJ700 | PGD 05:55 → JAX 06:57; JAX 08:00 → PGD 09:02; SDF 20:17 → DAY 21:05; DAY 21:55 → SDF 22:43 ET |
| 145 / AD-35 | CRJ200 | PWM 04:40 → PHF 06:24; PHF 07:04 → PWM 08:48; SYR 11:18 → BUF 12:04; BUF 12:44 → SYR 13:30 ET |
| 305 / AA-5 | CRJ700 | MCI 09:46 → TUL 10:44; TUL 11:25 → MCI 12:23 CT |
| 526 / AJ-7 | CRJ900 | DAL 04:58 → MCI 06:25; MCI 07:15 → DAL 08:42 CT |
| 509 / AB-9 | CRJ900 | SAT 05:00 → DAL 06:01; DAL 06:51 → SAT 07:52 CT |
| 114 / AD-4 | CRJ200 | ROA 19:30 → PHF 20:24; PHF 21:45 → ROA 22:39 ET |
| 169 / AF-5 | CRJ200 | FWA 20:25 → DAY 21:05; DAY 21:55 → FWA 22:35 ET |

New flight numbers are 2131–2154. Existing flights retain their identities, fleet, route, line and day. Three approved flights change time:

- **1853 SYR–HPN:** +5 minutes to 14:10–15:04 ET.
- **1448 HRL–MCI:** −191 minutes to 06:39–09:06 CT. The previously analyzed HRL coverage tradeoff was explicitly approved, including Route 305.
- **1206 DAL–PHF:** +12 minutes to 09:32 CT–13:25 ET.

**DAY-B9 is 21:05–22:05 ET.** BWI, CLT, SDF and FWA receive evening service into that bank. MCI-B3 shifts two minutes later to **08:07–09:07 CT**, retaining its previous assigned touches and accepting the retimed HRL flight. A ROA second-hub exception permits the useful PHF service alongside JAX under the user's standing authorization. No gate inventory, aircraft count, curfew, minimum turn or passenger-handling constraint is waived.

The release has **1152 flights, 181 routes, 20 lines and 560 directed markets**. Structure, operating rules, overnight turns, planning reconstruction and gate/stand allocation pass with **zero effective operating errors and no hard-stop failures**. The existing 182 warning findings remain. Stand use is **15 claims and 3771 minutes**, with no passenger handling on stands. All fleet inventories and line/day aircraft usage remain unchanged.

The DAY connection audit measures whole-timetable service between BWI/CLT/SDF/FWA and JAX/PHF/SYR/MCI: all eight cities have direct DAY round trips and 17 of 32 directional cross-group pairs meet the configured connection window. It is not a claim that all those connections occur in the late bank. The accompanying utilization reports assess late-bank demand using competing nonstop, one-stop and two-stop itineraries.

Route 114 retains its tight 41-minute ROA turn and 31-minute connection to PHF's 20:55 wave. The 169 DAY turn has 50 minutes. Demand opportunity scores are seat-uncapped relative-choice measures, not forecasts or profitability estimates; aircraft-day validation is separate from crew staffing. Detailed comparisons and approved tradeoffs remain in the v1.2.3 analysis reports.

The latest-release regression suite passed **49 checks (13 Python, 36 JavaScript)** against v1.2.3, including exact approved flying, preservation of every existing flight except the three authorized retimings, bank/policy changes, full release reproduction, physical gates, overnight turns, planning, connection accounting and the web console. Older releases were not regression tested. The static app build contains 13 selectable schedules and 135 data files, with v1.2.3 as the default.

The authoritative release input is `config/optimizations/schedule_7_v1_2_3.json`, applying the accepted rounds 1–3 overlay and the approved round-four overlay to the pinned v1.2.2 canonical. Final artifacts are in `data/schedules/schedule_7_v1_2_3/`. The earlier working draft and proposal reports are historical comparison inputs. **Future schedule work should start from the released v1.2.3 canonical**, not the earlier draft snapshot.

Rebuild and verify:

```bash
PYTHONPATH=src python -m caa_scheduler build-optimization-release config/optimizations/schedule_7_v1_2_3.json
bash scripts/run_latest_regression.sh
PYTHONPATH=src python -m caa_scheduler build-web --output dist
```
