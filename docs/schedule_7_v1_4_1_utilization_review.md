# Schedule 7 v1.4.1 — CRJ200 utilization review and provisional draft

**Status:** Unpublished, pending user review. Published app default on `main` is Schedule 7 v1.4.0. The v1.4.1 development branch contains a reproducible provisional **1,266-flight** schedule; none of its optimizations are on `main`.

## Objective and current disposition

Improve the lowest-usage SYR-heavy CRJ200 routes 105, 106, 107, 108, 162 and 167 without reducing high-demand connectivity simply to add aircraft time. Published v1.4.0 baseline: 1,259 flights, 188 routes, 17 aircraft routing lines. The provisional v1.4.1 draft has 1,266 flights, 188 routes, 17 lines and no additional physical gate or stand inventory.

| Route | Published total flying | Current provisional total | Disposition |
| --- | ---: | ---: | --- |
| R105 | 6h46m | **9h26m** | Late BGR–SYR–BGR productive turn |
| R106 | 7h32m | 7h32m | Retained intact; avoid forcing another rebuild |
| R107 | 5h47m | **7h29m** | ISP–PHF–SYR noon triangle with only 8-minute BDL delay |
| R108 | 6h09m | **8h21m** | Provisional SYR–PIT–SYR turn; BTV–RFD connection retained |
| R162 | 6h53m | **9h33m** | Morning SYR–BGR–SYR turn |
| R167 | 6h54m | 6h54m | No acceptable market-preserving growth selected |

The draft also includes one supporting CRJ700 timing change to **R356**, ensuring that BDL–PIE connections remain competitive.

## Provisional schedule changes

All edits are reconstructible by `python scripts/build_schedule_7_v1_4_1_draft.py` from the published `schedule_7_v1_4_0` canonical and four overlays:

1. `config/optimizations/schedule_7_v1_4_1_r105_r162_provisional.json`
2. `config/optimizations/schedule_7_v1_4_1_r107_isp_phf_provisional.json`
3. `config/optimizations/schedule_7_v1_4_1_r356_compensation.json`
4. `config/optimizations/schedule_7_v1_4_1_r108_pit_provisional.json`

The built canonical and native reports are stored under `data/schedules/schedule_7_v1_4_1_draft/`.

**R105:** Retimes MHT–SYR to 11:45–12:45, reaches SYR M12, and advances the SYR/BGR afternoon pair into B5/M17. Adds flights 2271 BGR–SYR 20:10–21:30 and 2272 SYR–BGR 22:10–23:30. Retains BGR terminator and next-day originator; gains 160 flight minutes, 80 within the critical 06:00–22:00 window.

**R162:** BDL–SYR flight 2102 departs 08:16 and arrives 09:10, making the new SYR M09 bank. Adds flight 2269 SYR–BGR 09:50–11:10 and 2270 BGR–SYR 11:55–13:15. The original PHF–MDT flying and ILM terminator remain intact. Gains 160 flight minutes, all within the critical window.

**R107:** Replaces flight 1893 ISP–SYR 12:25–13:23 with flight 2273 ISP–PHF **10:13–11:29**, reaching PHF B3, and flight 2274 PHF–SYR **12:09–13:33** via new logical PHF M12. Moves existing SYR–BDL flight 1792 from 14:05 to **14:13**, preserving its SYR B4 assignment, BDL–SYR return at 18:00 and CAK terminator. Adds one net flight and 102 flight minutes. The smaller eight-minute BDL delay replaces an earlier tested 80-minute-delay proposal with severe BDL passenger penalties.

**R356 supporting retiming:** Moves CRJ700 flight 2209 BDL–SYR from **10:35–11:29 to 10:05–10:59**. This restores the BDL–PIE fastest reasonable journey formerly served by R162's 10:05 BDL return. It passes gate, turn, bank, overnight and operating rules and adds no flights or fleet usage. Seven other BDL directional itineraries become about 30 minutes slower; the individual O-D-weighted benefit is positive by roughly 4,041 modeled passenger-minutes.

### Mini-bank inventory

The accepted v1.4.0 SYR M15/M17 and DAY-M0 banks remain. v1.4.1 provisionally adds **SYR-M09 08:55–09:55**, **SYR-M12 11:55–12:55**, and **PHF-M12-V141 11:55–12:55**. These are logical schedules only: no changes to the airport's fixed gate or stand inventories.

## Native validation and itinerary effects

The cumulative 1,264-flight draft passes structural, planning, overnight, passenger-touch gate and operating validation with **zero effective operating errors**, no added aircraft and 17 unchanged routing lines.

Compared with published 1,259-flight v1.4.0:

| Passenger-network measure | Cumulative draft |
| --- | ---: |
| Geographically reasonable directional market gains | **19** |
| Geographically reasonable directional market losses | **2** |
| Faster fastest reasonable itineraries | **93** |
| Slower fastest reasonable itineraries | **74** |
| Relative O-D-weighted fastest-journey score | **+18,313 modeled passenger-minutes** |

Gains include ISP→BWI, BGR↔PGD, BGR↔BNA, GSP→SYR, PNS→SYR, and several other BGR/ISP links. The two geographic losses are **ISP→BNA** (3.7 underlying directional O-D per day) and **ISP→FWA** (no recorded O-D in the pinned matrix). Other slower itineraries remain: BDL→PGD/BNA/CMH are about 30 minutes slower after R356's earlier return; PIE→BGR is about 70 minutes slower in the R105 pattern; RFD→BDL is eight minutes slower due to R107. These are tradeoffs requiring final review, not hard operating errors.

Commercial audit: `outputs/schedule_7_v1_4_1_utilization/provisional_network.json`. Individual compensation audit: `outputs/schedule_7_v1_4_1_utilization/r356_connection_protection_network.json`. Market O-D estimates are source-market directional demand, not forecast boarded passengers.

## Alternatives evaluated but not incorporated

**R108:** BTV–ROC–SYR, BTV–BUF–SYR and BTV–PWM–SYR each passed operating checks and add one segment, but make BTV→RFD 76 minutes slower (roughly 30 daily directional O-D) and remove BTV→MDT reasonable service. A more radical BTV–PHF–SYR triangle failed fixed PHF gate inventory. The existing route is better retained.

**R167:** ALB–BTV–ALB fits physically but the market has about 0.6 underlying directional O-D each way. A higher-demand ALB–BWI–ALB morning turn also passes native validation, but its tested timing loses ALB→PIT and DAB→CAK coverage and delays other existing journeys. ALB–PHF–ALB failed PHF gate/spacing checks. No R167 changes have been added.

**R106:** Already 7h32m after v1.4.0 and strongly connected. The HPN–BWI–SYR morning triangle fails BWI's fixed gate inventory. Preserve R106 as-is.

## Next optimization priorities

Review residual two-market ISP coverage losses and slower BDL/PIE/BGR connections before releasing. Consider tactical adjustment to protect ISP→BNA without undoing R107's modest BDL delay. Additional morning P2P/mini-bank experiments should not be added unless they pass both native physical/operating validation and independent passenger-itinerary audits.

**Governance:** This is a provisional v1.4.1 draft. No PR to `main`, web manifest/default change, or release package has been authorized.

## Additional October 20 holistic review — R108

A new R108 restructuring has been provisionally incorporated in the unpublished draft. It moves ORH→SYR from 12:25–13:23 to **10:13–11:11**, then adds flight **2275 SYR→PIT 11:55–13:01** and **2276 PIT→SYR 13:41–14:47**. It moves SYR→BTV from 14:05–14:57 to **15:27–16:19**, retaining the BTV→SYR **18:00–18:52** flight and therefore its evening onward RFD connection. R108's terminator remains SYR and the following day's originator remains unchanged.

- R108 flying rises from 6h09m to **8h21m**, gaining 132 minutes and two flights.
- Native structural, overnight, planning, operating and fixed physical gate/stand checks all pass with zero effective operating errors on the cumulative **1,266-flight draft**.
- Against the preceding 1,264-flight provisional version: one new geographically reasonable directional market (FWA→BTV, 0.3 underlying daily directional O-D); four lost markets with **zero recorded O-D** (ORH→ABE/ACY/BWI/DAB); 15 faster and 43 slower fastest reasonable itineraries; estimated O-D-weighted relative score **+860 modeled passenger-minutes**. Important caveats include ORH→PGD slowing 132 minutes (10.6 O-D/day) and RFD→BTV slowing 15 minutes (30.3 O-D/day). The **BTV→RFD 30.1/day directional market is preserved**, and RFD→BTV also remains served.
- Screen evidence: `outputs/schedule_7_v1_4_1_utilization/r108_bank_rebuild_screen.json` and `r108_bank_rebuild_network.json`.
- The newly screened R167 ALB→BWI→SYR alternative passed native checks but lost ALB→BNA (30.8/day), ALB→PIT (6.4/day), and ALB→FWA (0.7/day), with a strongly unfavorable weighted itinerary effect. It is **not integrated**. Another R108 ORH→SYR→PHF→SYR option failed physical PHF gate inventory; ROC failed ROC inventory and market spacing.

The R108 change is **provisional, not a publication authorization**. The accepted web default remains v1.4.0. Future effort should focus on preserving/mitigating the slower R108 ORH→PGD journey and finding commercially stronger R167 morning options rather than adding low-demand flying solely for utilization.

## October 20 continuation — BTV–RFD demand and R167 holistic test

The pinned `data/reference/airport_od_matrix_consolidated_v2.csv` shows **BTV→RFD 30.1** and **RFD→BTV 30.3** underlying daily directional O-D. Both exceed the user-defined threshold of 15. Preserve this connection as an optimization priority. The current provisional R108 keeps flight BTV→SYR at 18:00–18:52; it preserves the BTV→RFD reasonable path, although the inverse RFD→BTV fastest connection slows by approximately 15 minutes.

The last saved provisional 1,266-flight draft was recovered and validated. A follow-up R167 screening used an earlier 05:09 SYR→ALB originator to create capacity for demand-relevant **ALB–BWI–ALB** and **ALB–PIT–ALB** morning returns, with a subsequent SYR M12 departure to CAK. Both variants pass all native structural, overnight, planning, operating and fixed-inventory checks; each adds two flights.

Commercial itinerary comparisons against the 1,266-flight provisional draft:

| R167 variant | Reasonable market gains | Losses | Faster | Slower | O-D-weighted planning score |
| --- | ---: | ---: | ---: | ---: | ---: |
| ALB–BWI–ALB | 0 | 1 | 19 | 17 | -1,222 |
| ALB–PIT–ALB | 0 | 1 | 9 | 13 | -2,005 |

Both lose DAB→CAK as a reasonable path (4.0 underlying daily directional O-D) and delay high-demand ALB/SFB and PIE/CAK markets. The ALB–BWI market itself has 21.5/22.5 underlying directional O-D, but it does not offset the observed systemwide travel-time penalties at the tested banks. **Neither R167 option is approved or integrated.** Evidence: `outputs/schedule_7_v1_4_1_utilization/r167_followup_native.json` and `r167_followup_network.json`.

Next: preserve the accepted-to-provisional R108 morning SYR–PIT turn and BTV–RFD network coverage; concentrate further R167 testing on preserving existing ALB and CAK bank connections instead of simply extending flying. R107's residual ISP→BNA loss and R108's ORH→PGD delay remain commercial review items, not hard operating errors.


## October 20 resumed continuation — BTV/RFD threshold and holistic R167 options

The pinned O-D matrix reports **BTV→RFD 30.1** and **RFD→BTV 30.3** average daily directional passengers. These are *two separate directions*, not 30.1 combined. Both exceed the user's 15-passenger threshold; keep BTV/RFD connectivity protected. R108's current provisional BTV→SYR 18:00–18:52 return remains in place.

The latest recovered provisional draft is **1,266 flights, 188 routes, 17 lines**. R105, R162, R107 (ISP–PHF–SYR), supporting R356 BDL timing, and R108 (SYR–PIT–SYR) were already in this draft; they were not created again during this continuation.

The read-only R167 ALB hold screen tested four additional possibilities on that *actual* cumulative draft:
- **ALB–PHF–SYR:** fails PHF physical gate inventory, PHF–SYR same-pairing spacing and the 40-minute SYR turn. Do not adopt.
- **ALB–PIT–SYR:** no physical gate conflict, but fails native bank alignment and needs further coordinated bank retiming before acceptance.
- **ALB–BTV–SYR:** passes native structural, overnight, planning, operating and physical gate checks, adds one net leg, and preserves the existing 11:20 SYR–CAK departure. Passenger-network audit required before any incorporation.
- **ALB–BTV–ALB:** passes native checks and adds two flights but has only 0.6/day underlying ALB–BTV directional O-D. Not recommended solely for utilization.

Evidence: `outputs/schedule_7_v1_4_1_utilization/r167_holistic_native.json` and `scripts/screen_schedule_7_v1_4_1_r167_holistic.py`. The comparative passenger-network audit is `scripts/audit_schedule_7_v1_4_1_r167_holistic_network.mjs` and its output `r167_holistic_network.json`.

**Governance:** No additional route changes have been incorporated in the provisional 1,266-flight draft; published `main` remains v1.4.0.
