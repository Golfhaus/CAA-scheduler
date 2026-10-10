# Schedule 7 CRJ200 line alignment draft

Prepared October 10, 2026 from **released v1.2.4** at commit `944ed86165ddfd55b517873392b3e94a8f78f02c`. This is an **unpublished working draft**. The app continues to use released v1.2.4; no next release number is assigned. Future DAY destination overnights are not yet implemented.

## Fleet verification and scope

All seven requested lines are exclusively **CRJ200**. None were discarded. Original lengths: AD 40, AE 14, AF 5, AI 2, AM 3, AN 1, AR 1, totaling **66 aircraft-days**. AC's ten-day CRJ200 line and every other fleet/line are outside this operation.

Merely regrouping complete days cannot absorb all the short loops: AF/AR, AM and AN have disconnected overnight endpoint components. The accepted draft instead exchanges existing flight suffixes at shared DAY, JAX, MCI and SYR stations. There are **24 changed daytime flight-to-flight handoffs and 80 legs assigned to a different source day**. Every passenger flight ID, flight number, fleet, city pair, local clock and bank assignment is preserved. Every original overnight flight-to-flight handoff is preserved, including both DAY pairs under review. Route IDs are then renumbered sequentially within each line.

The 66 route days become six closed lines. AR is retired as a line label; its flying is retained. Total schedule line count falls from 20 to 19, while all 181 route days, 1,170 flights, aircraft requirements, fleet inventory and spares remain unchanged. A shorter list of line labels does not free an aircraft.

## Result and independent maintenance coverage

The independent RON column excludes route 125's and route 136's DAY terminators. The rolling gap test also withholds maintenance credit from **both** of those overnights, treating any future destination as a non-MX city. All six lines meet the normal ten-day limit without using the standing one-day grace. Each has an actual hub/focus RON apart from the protected DAY overnights.

| New line | Route range | Days | Independent hub/focus RONs | Maximum consecutive non-MX RONs without 125/136 credit |
|---|---|---:|---|---:|
| AD | 111–121 | 11 | MCI (route 112, day 2), MCI (route 113, day 3) | 9 |
| AE | 122–132 | 11 | SYR (route 129, day 8) | 10 |
| AF | 133–143 | 11 | MCI (route 135, day 3), DAY (route 138, day 6) | 7 |
| AI | 144–155 | 12 | MCI (route 145, day 2), MCI (route 154, day 11) | 8 |
| AM | 156–167 | 12 | DAY (route 156, day 1), SYR (route 166, day 11) | 9 |
| AN | 168–176 | 9 | JAX (route 169, day 2) | 8 |

## Protected DAY pairs and the next extension study

The complete current days for routes **125 and 136** are preserved, including their numbers, their flight sequences and their DAY termination times. The next-day originators also retain route numbers **126 and 137** and their original first flights. Other routing numbers change; use the mapping below rather than earlier release notes when referring to draft routing IDs.

| Terminator | Draft line/day | DAY arrival | Next-day route | DAY departure | Latest return to preserve 40-minute turn |
|---|---|---|---|---|---|
| 125 (flight 1850) | AE / 4 | 19:43 ET | 126, AE / 5 (flight 1503) | 05:50 ET | 05:10 ET |
| 136 (flight 1572) | AF / 4 | 19:46 ET | 137, AF / 5 (flight 1873) | 05:50 ET | 05:10 ET |

AE's independent MX night is **SYR on route 129 / day 8**; AF has **MCI on route 135 / day 3** and **DAY on route 138 / day 6**. Thus the proposed future extensions do not need to retain either protected DAY overnight for line maintenance eligibility. Their destination, demand, curfews, gates, bank arrival time and operating feasibility still need to be screened when flying is proposed. The 05:10 return deadline preserves the existing 05:50 originator; feeding other DAY B1 flights must be evaluated against their individual departure times and the 30-minute passenger connection floor.

## Verification

The draft passes structural validation, geographic continuity and wraparound closure, sequential route/day numbering, minimum turns, overnight turns, operating hard stops, planning reconstruction, gates and stands, and independent maintenance cadence. There are **zero effective operating errors**, no new operating exceptions and **172 advisory findings**, down from 179 because seven affected line-length warnings are removed. Unrelated line-length advisories remain for MAX9 A (13), CRJ700 AO (1) and AQ (1); they were not brought into the CRJ200 pool. §2.6 A continues to pass; the 79 inherited §2.6 B departure-gap advisories are unchanged because passenger times are unchanged.

The fixed physical gate/stand inventory is preserved. Stand utilization remains **16 claims / 3,717 minutes**, with no passenger turn on a stand. The latest-release regression suite passes **52 checks** against released v1.2.4; no superseded releases were retested. The draft itself is independently replayed and checked by the review script.

## Replay and authoritative files

- Overlay: `config/optimizations/schedule_7_crj200_line_alignment.json`.
- Machine-readable review, full route mapping and changed handoffs: `config/proposals/schedule_7_crj200_line_alignment_review.json`.
- Replay/verification: `python scripts/review_crj200_line_alignment.py`.
- Reconstructed local artifacts: `builds/crj200-line-alignment/`; these are reproducible and not publication artifacts.

The replay verifies the pinned base SHA256, rejects any non-CRJ200 selected line, validates all 1,170 flight identities and clocks, protects the two complete DAY terminator days, checks every original overnight flight handoff, and recomputes operating, overnight, planning, physical gates and maintenance results. The released schedule and app manifest are not modified.

## Source route order by new line

Numbers in this table refer to the **v1.2.4 source day whose first flight starts each new route**. Several source days exchange flight suffixes; this is not a claim that every old day is intact.

| New line | Source originator-route order |
|---|---|
| AD | 164, 151, 152, 153, 154, 155, 156, 157, 158, 172, 171 |
| AE | 167, 168, 147, 125, 126, 127, 143, 144, 176, 145, 146 |
| AF | 129, 130, 131, 136, 137, 138, 139, 140, 141, 142, 128 |
| AI | 132, 133, 134, 135, 161, 162, 163, 170, 173, 174, 159, 160 |
| AM | 175, 149, 150, 111, 112, 122, 123, 124, 148, 169, 165, 166 |
| AN | 114, 115, 116, 117, 118, 119, 120, 121, 113 |

## Full route mapping

| Source route | Original line/day | Draft route | Draft line/day |
|---:|---|---:|---|
| 111 | AD / 1 | 159 | AM / 4 |
| 112 | AD / 2 | 160 | AM / 5 |
| 113 | AD / 3 | 176 | AN / 9 |
| 114 | AD / 4 | 168 | AN / 1 |
| 115 | AD / 5 | 169 | AN / 2 |
| 116 | AD / 6 | 170 | AN / 3 |
| 117 | AD / 7 | 171 | AN / 4 |
| 118 | AD / 8 | 172 | AN / 5 |
| 119 | AD / 9 | 173 | AN / 6 |
| 120 | AD / 10 | 174 | AN / 7 |
| 121 | AD / 11 | 175 | AN / 8 |
| 122 | AD / 12 | 161 | AM / 6 |
| 123 | AD / 13 | 162 | AM / 7 |
| 124 | AD / 14 | 163 | AM / 8 |
| 125 | AD / 15 | 125 | AE / 4 |
| 126 | AD / 16 | 126 | AE / 5 |
| 127 | AD / 17 | 127 | AE / 6 |
| 128 | AD / 18 | 143 | AF / 11 |
| 129 | AD / 19 | 133 | AF / 1 |
| 130 | AD / 20 | 134 | AF / 2 |
| 131 | AD / 21 | 135 | AF / 3 |
| 132 | AD / 22 | 144 | AI / 1 |
| 133 | AD / 23 | 145 | AI / 2 |
| 134 | AD / 24 | 146 | AI / 3 |
| 135 | AD / 25 | 147 | AI / 4 |
| 136 | AD / 26 | 136 | AF / 4 |
| 137 | AD / 27 | 137 | AF / 5 |
| 138 | AD / 28 | 138 | AF / 6 |
| 139 | AD / 29 | 139 | AF / 7 |
| 140 | AD / 30 | 140 | AF / 8 |
| 141 | AD / 31 | 141 | AF / 9 |
| 142 | AD / 32 | 142 | AF / 10 |
| 143 | AD / 33 | 128 | AE / 7 |
| 144 | AD / 34 | 129 | AE / 8 |
| 145 | AD / 35 | 131 | AE / 10 |
| 146 | AD / 36 | 132 | AE / 11 |
| 147 | AD / 37 | 124 | AE / 3 |
| 148 | AD / 38 | 164 | AM / 9 |
| 149 | AD / 39 | 157 | AM / 2 |
| 150 | AD / 40 | 158 | AM / 3 |
| 151 | AE / 1 | 112 | AD / 2 |
| 152 | AE / 2 | 113 | AD / 3 |
| 153 | AE / 3 | 114 | AD / 4 |
| 154 | AE / 4 | 115 | AD / 5 |
| 155 | AE / 5 | 116 | AD / 6 |
| 156 | AE / 6 | 117 | AD / 7 |
| 157 | AE / 7 | 118 | AD / 8 |
| 158 | AE / 8 | 119 | AD / 9 |
| 159 | AE / 9 | 154 | AI / 11 |
| 160 | AE / 10 | 155 | AI / 12 |
| 161 | AE / 11 | 148 | AI / 5 |
| 162 | AE / 12 | 149 | AI / 6 |
| 163 | AE / 13 | 150 | AI / 7 |
| 164 | AE / 14 | 111 | AD / 1 |
| 165 | AF / 1 | 166 | AM / 11 |
| 166 | AF / 2 | 167 | AM / 12 |
| 167 | AF / 3 | 122 | AE / 1 |
| 168 | AF / 4 | 123 | AE / 2 |
| 169 | AF / 5 | 165 | AM / 10 |
| 170 | AI / 1 | 151 | AI / 8 |
| 171 | AI / 2 | 121 | AD / 11 |
| 172 | AM / 1 | 120 | AD / 10 |
| 173 | AM / 2 | 152 | AI / 9 |
| 174 | AM / 3 | 153 | AI / 10 |
| 175 | AN / 1 | 156 | AM / 1 |
| 176 | AR / 1 | 130 | AE / 9 |
