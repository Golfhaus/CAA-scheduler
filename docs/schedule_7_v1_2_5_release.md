# Schedule 7 v1.2.5

Published October 11, 2026, following the user's authorization to add the four ROD extensions and publish the complete draft to the app's main branch. The app defaults to **v1.2.5: 1,190 flights, 181 routes and 19 lines**. Compared with v1.2.4, this includes 20 additional flights and 16 retimed original flights. Fleet inventory, aircraft-days and physical gates/stands are unchanged.

## Added flying

Every time is local. DAY, IND, CAK, SDF, SBN, GRR, ALB, PHF, SWF, SYR, BTV and HPN are Eastern; MCI and SGF are Central. SGF's 00:00 arrival is the next calendar day.

| Flights | Current routes; line/day | Added flying |
|---|---|---|
| 2173 / 2174 | 125 / 126; AE/4–5 | DAY 21:35 → IND 22:18; IND 04:30 → DAY 05:13 |
| 2175 / 2176 | 136 / 137; AF/4–5 | DAY 21:35 → CAK 22:25; CAK 04:30 → DAY 05:20 |
| 2177 / 2178 | 112 / 113; AD/2–3 | MCI 21:10 → SDF 23:45; SDF 04:30 → MCI 05:05 |
| 2179 / 2180 | 135 / 136; AF/3–4 | MCI 21:25 → SBN 23:58; SBN 04:30 → MCI 05:03 |
| 2181 / 2182 | 715 / 716; B/2–3 | MCI 21:23 → GRR 23:58; GRR 04:30 → MCI 05:05 |
| 2183 / 2184 | 323 / 324; AK/3–4 | MCI 23:10 → SGF 00:00; SGF 04:30 → MCI 05:20 |
| 2185 / 2186 | 159; AM/4 | ALB 10:15 → PHF 11:40; PHF 13:20 → ALB 14:45 |
| 2187 / 2188 | 130; AE/9 | SWF 08:00 → PHF 09:13; PHF 10:05 → SWF 11:18 |
| 2189 / 2190 | 318; AH/7 | SYR 07:45 → BTV 08:37; BTV 09:48 → SYR 10:40 |
| 2191 / 2192 | 161; AM/6 | SYR 07:45 → HPN 08:39; HPN 09:36 → SYR 10:30 |

The new PHF turns serve the holds identified under old route numbers **111 → 159** and **176 → 130**. The second SYR hold, formerly **122**, is now **161**. Route 318 keeps its number. Their maximum remaining ground intervals, including the new destination, are respectively **1h40, 1h21, 2h07 and 2h09**, replacing holds of 5h30–6h06. HPN gains its first morning departure to SYR; ALB–PHF gains its second daily flight each way, and SWF–PHF is a new pairing.

## Approved timing changes

DAY B1 shifts one minute later to **05:01–06:01**. DAY–HOU flight 1503 departs 05:53, three minutes later; DAY–FWA flight 1873 departs 06:00, ten minutes later. Their returns and later flying keep their clocks.

MCI B1 shifts six minutes later to **04:51–05:51**. Flights 1035/1139/1405/1595/1633/1647/1675/1715 to SFB/RDU/ELP/SHV/OMA/ICT/FSD/CID move 05:35→**05:50**. MCI–AUS 2002 moves 04:45→04:51, and AUS–MCI 1083 moves 07:15→07:18. PGD 05:25 and JAX 05:35 remain unchanged. The four new returns feed the later wave, with geographically valid SGF feed also reaching RDU.

For the HPN feeder, SYR–SWF 1886 moves 11:08→**11:10**, and SWF–DAY 2011 moves 12:37→**12:39**. DAY B5 shifts two minutes later to **13:22–14:22**. DAY–IND 2095 moves 13:20→13:22 and IND–DAY 2096 moves 14:47→14:49. The next DAY–JAX flight stays 16:16, exactly 40 minutes after the revised DAY arrival. All other 1,154 original flight clocks are preserved.

The broader Florida-originator advances and later BTV-turn alternatives were reviewed and excluded from this release. The saved [hold review](schedule_7_v1_2_5_long_holds_review.md) explains the alternatives and the directional demand limitation.

## CRJ200 lines and maintenance

The former AD/AE/AF/AI/AM/AN/AR flying is recalibrated into six closed CRJ200 lines, retaining all 66 selected aircraft-days: **AD 11, AE 11, AF 11, AI 12, AM 12, AN 9**. AR's flying remains under the other labels. Original flights, markets, fleets and clocks are preserved except for the explicitly approved retimings above. The [alignment review](schedule_7_crj200_line_alignment.md) and cumulative overlay record every original-to-current route and leg reassignment.

Routes 125 and 136 RON at IND and CAK without being needed for the independent maintenance proof. AE retains SYR on 129; AF retains DAY on 138. AD retains MCI on 113. AD, AE and AF peak at ten consecutive non-MX nights and require no new grace. AI's MCI nights on 145/154 remain protected. All four ROD extensions retain their prior overnight endpoints.

## Validation and demand limits

The **52 latest-version regression checks pass**, including an exact release rebuild and the Routing Details / Hub Bank Breakdown data behavior. Structural, operating, overnight, planning, §2.6, maintenance and fixed gate/stand checks pass with **zero effective operating errors and zero hard-stop failures**. There are 166 advisories. Stand use falls from 16 claims / 3,717 minutes to **14 / 3,253**, with zero stand claims at SYR and no passenger handling on stands. No new operating override is introduced; the existing SWF tier override is retained for the user-approved additional PHF coverage.

Relative to released v1.2.4, the full one/two-stop network comparison finds **222 directional markets with faster best itineraries** and no market losing all valid connections. Fifteen markets with positive pinned O-D have slower fastest itineraries by 2–15 minutes; fourteen additional slower markets have zero pinned O-D. IND–SFB is eight minutes slower; IND–OMA/ELP/ICT/FSD/SHV/CID are fifteen minutes slower. The full audit is pinned in `connectionScopeDecision.networkItineraryAudit` in the release configuration/report. The separate whole-timetable SYR one-stop audit covers all **16/16** directional BTV/HPN-to-Florida combinations; it is not a forecast of demand specifically in B3.

Opportunity figures in the [MCI review](schedule_7_v1_2_5_mci_b1_review.md) and [hold review](schedule_7_v1_2_5_long_holds_review.md) are seat-uncapped relative-choice allocations, not passenger forecasts, load factors or profitability. The SYR outbound positioning flights attract little modeled demand; most benefit sits on their B3 feeder returns. Several aircraft turns are exactly 40 minutes, and SGF's connection into the 05:50 MCI wave is exactly 30 minutes. Crew assignment and economic capture remain outside this aircraft-feasibility validation.

## Reproduction

```bash
PYTHONPATH=src python -m caa_scheduler build-optimization-release config/optimizations/schedule_7_v1_2_5_release.json
bash scripts/run_latest_regression.sh
PYTHONPATH=src python -m caa_scheduler build-web --output dist
```

The release configuration applies the accepted cumulative rounds 1–3 overlay directly to pinned v1.2.4. The accepted draft's source hashes, exact cumulative/sequential replay, joint demand and connection tradeoffs are verified by `python scripts/build_schedule_7_v1_2_5_draft.py`. Immutable round-one and round-two checkpoints keep the historical proposal comparisons reproducible. Routine regression targets the app's latest default, v1.2.5; earlier released versions are historical references.
