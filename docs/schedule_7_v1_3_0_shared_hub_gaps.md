# Schedule 7 v1.3.0 — shared-hub bidirectional gap effort

Reviewed October 12, 2026 against the earlier two-flight round-one draft. The user subsequently accepted F2017's two-minute advance for PGD→CAK; it is now included alongside F1437/F1036 and jointly validated in the [current draft](schedule_7_v1_3_0_draft.md). All other scenarios below remain analysis only. Saved trial reports retain their original two-flight baseline; demand, inventories, roster and the 30–240-minute transfer window are unchanged.

## Timing lower bounds

These are the smallest combined clock changes to create a valid transfer using the existing flights. They are not aircraft-feasible construction plans or a proof that the tested portfolio is globally optimal. Clock changes may be divided between incoming and outgoing flights; exact routes, banks and gates can require more work.

| Market; shared hub | First direction | Reverse direction | Effort to resolve both |
|---|---|---|---|
| CAK–PGD; MCI | CAK→PGD: current 20:45 arrival to next-day 05:25 departure waits 8h40, 4h40 over the cap | PGD→CAK: 11:35 arrival to 15:37 departure waits 4h02, two minutes over | Large change or additional service for CAK→PGD; the reverse is an easy repair |
| BLV–HOU; MCI | BLV→HOU: 11:29 arrival to 15:35 departure waits 4h06 | HOU→BLV: 19:54 arrival misses the latest 15:25 departure; requires at least 4h59 to provide a 30-minute transfer | Large change or new evening/morning service for HOU→BLV; forward direction is an easy repair |
| MYR–RFD; PHF | MYR→RFD: 06:16 arrival to 11:35 departure waits 5h19 | RFD→MYR: 15:34 arrival to 20:55 departure waits 5h21 | At least 79/81 minutes respectively; representative repair needs three retimings and a proposed new bank, with material coverage losses |
| BNA–OMA; MCI | BNA→OMA: 09:49 arrival misses the 08:55 departure; at least 84 minutes to provide a 30-minute transfer | OMA→BNA: 10:44 arrival to 14:55 departure waits 4h11 | A tested two-flight repair uses −11 and −89 minutes plus one existing-bank reassignment; it sacrifices other one-stop markets |

## Three isolated small repairs

All times are local. Each individual proposal passes structural, operating, overnight and fixed gate/stand checks with zero effective operating errors and the same 166 advisories. Each loses zero existing direct/one/two-stop itinerary choices, loses no market coverage or one-stop market, and slows no fastest journey, both in the app audit and under the 2.25 circuity screen. They have not been jointly validated as an accepted new round.

| Proposal | Change | Aircraft turn and benefit |
|---|---|---|
| `pgd_cak_2` | Flight 2017 MCI–CAK 15:37 CT–18:42 ET to 15:35 CT–18:40 ET | 41-minute MCI turn. Creates PGD→CAK, DSM→CAK and FSD→CAK one-stop service. PGD→CAK takes 8h50, so the existing 5h45 two-stop trip remains faster. |
| `blv_hou_6` | Flight 1357 BLV–MCI 10:25–11:29 to 10:31–11:35 CT | 40-minute next MCI turn, unchanged subsequent departure. Creates BLV→HOU one-stop service and improves the fastest trip from 7h49 to 6h53. Advancing MCI–HOU by six minutes instead would leave an illegal 34-minute turn after CLT–MCI. |
| `oma_bna_11` | Flight 1077 MCI–BNA 14:55–16:24 to 14:44–16:13 CT | 86-minute MCI turn; departure exactly at MCI-B7's opening. Creates OMA→BNA one-stop service, improving the fastest trip from 10h31 to 6h18. |

## Tested larger options and tradeoffs

**BNA–OMA, existing aircraft:** Advance 1077 by eleven minutes as above, and 1080 BNA–MCI from 18:25–19:54 to **16:56–18:25 CT**, eighty-nine minutes earlier. Move 1080's MCI arrival assignment from B10 to existing B9. BNA's aircraft turn becomes 43 minutes; the later MCI–FLL flight keeps its clock. This provides BNA→OMA on 1080/1636 with a 30-minute MCI transfer and OMA→BNA on 1639/1077 with a 240-minute transfer. Full physical and operating validation passes, and stand use remains 14/3,253. However, four app itinerary choices disappear, BNA→SAT/ELP/SGF lose one-stop service, and twelve positive-O-D markets have slower fastest journeys by 5–302 minutes. No market loses all app paths of up to two connections, but BNA→SGF loses all such paths under the geographic screen. Do not adopt without replacement service or a deliberate network tradeoff.

**RFD→MYR alone:** Advancing PHF–MYR 1714 by 81 minutes on its own is impossible: its aircraft arrives from RDU at 20:14, while the desired departure is 19:34. One physically valid route-128 rebuild advances RDU–PHF 1660 **19:25–20:14 to 17:44–18:33 ET** (−101 minutes), followed by PHF–MYR **20:55–22:01 to 19:34–20:40 ET** (−81). Reassign the two PHF touches to existing B6/M6. It passes validation but loses 23 app itinerary choices and three markets' entire app paths of up to two connections; seven existing one-stop directional markets disappear and 26 positive-O-D fastest journeys slow. It is not a clean optimization.

**MYR–RFD both directions:** Add a 79-minute delay to MYR–PHF 1713, **05:10–06:16 to 06:29–07:35 ET**, to the route-128 rebuild above. The unchanged next PHF–SYR departure retains 100 minutes of aircraft ground time. The 07:35 arrival fits no current PHF bank, so the trial proposes a new **07:15–08:15 arrival bank**, increasing the configured PHF count by one. Both desired transfers then have 240-minute waits and seven-hour-five-minute journeys. Aircraft, gates, curfews, overnight and operating rules pass, but 56 app itinerary choices disappear, five markets lose all app paths of up to two connections and 39 positive-O-D fastest journeys slow. Under the geographic screen, seven markets lose all one/two-stop paths. Preserve the current feeders and investigate additional service or a broader coordinated bank portfolio instead.

**CAK→PGD and HOU→BLV:** The timing bounds are hours rather than minutes. CAK's existing evening MCI arrival cannot feed the morning PGD flight within four hours; simply delaying the CAK departure by 4h40 would exceed the destination's 21:00 cutoff. HOU reaches MCI after the last BLV departure; delaying that BLV round trip to catch HOU pushes its same-day BLV return beyond the 21:00 cutoff. These call for additional hub/spoke flying, an overnight pattern, or a broader rotation reconstruction. No larger trial for these directions is proposed as a validated solution here.

## Reproduction and saved evidence

- `python scripts/build_schedule_7_v1_3_0_draft.py`
- `python scripts/review_schedule_7_v1_3_0_shared_hub_gaps.py`
- `node scripts/audit_schedule_7_v1_3_0_connections.mjs`

The review writes isolated trial inputs; it checks that the accepted canonical's hash is unchanged. Native proposal overlays under `config/proposals/schedule_7_v1_3_0_*.json` exactly reproduce the reviewed flying, banks and policy; they are distinct from the accepted optimization overlay. `outputs/schedule_7_v1_3_0_shared_hub_gaps/review.json` records the screen and validation. `connection_review.json` records the full market losses, slower journeys and app/geographic comparisons. The accepted draft's own connection audit is `data/schedules/schedule_7_v1_3_0_draft/connection_review.json`.

Recommended next review: the remaining BLV→HOU and OMA→BNA small repairs, followed by demand-led additions for the harder directions. Only `pgd_cak_2` is accepted from these six scenarios. Run `node scripts/audit_schedule_7_v1_3_0_connections.mjs --accepted-only` for the current accepted draft. The proposal overlays and saved trial reports are historical evidence pinned to the earlier two-flight draft (SHA256 `b87c9c4aa438538a217e38fabf955b257c322a2205795f0e69665862f4178104`); their results should not be treated as joint validation against the current three-flight draft.
