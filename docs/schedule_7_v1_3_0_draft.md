# Schedule 7 v1.3.0 working draft

Unpublished. Based on released v1.2.5 at `c5c3550a24080a91d1e5d0fcee9a97673c3fe8e3`. The current destination roster, fleet inventory, demand-data v7, hubs/focus city, gates/stands and policies are retained.

## Scope

Continue aircraft utilization, improve connecting banks within hubs and BHM, and investigate markets lacking nonstop or one-connection service. Retain separate directional coverage and geographic-circuity audits. Pinned O-D measures market size, not forecast CAA loads.

## Accepted timing changes, October 12, 2026

| Flight | Route | Change, local times | Result |
|---|---|---|---|
| 1437 JAX–SFB | 351 | 16:15–17:00 to 16:13–16:58 ET (−2 min) | BLV/GPT→SFB within 240 minutes; 41-minute JAX turn. |
| 1036 MCI–SFB | 713 | 10:35 CT–14:08 ET to 10:34 CT–14:07 ET (−1 min) | MKE→SFB within 240 minutes; 89-minute MCI turn. |
| 2017 MCI–CAK | 170 | 15:37 CT–18:42 ET to 15:35 CT–18:40 ET (−2 min) | PGD/DSM/FSD→CAK within 240 minutes; 41-minute MCI turn. |
| 2019 MCI–PNS | 135 | 15:35–17:45 to 15:31–17:41 CT (−4 min) | DAL→PNS within 240 minutes. Requires the F1589 supporting adjustment below. |
| 1727 VPS–JAX | 115 | 05:50 CT–07:57 ET to 05:58 CT–08:05 ET (+8 min) | VPS→BWI within 240 minutes; 95 minutes before the next JAX departure. |
| 1723 MCI–SGF | 154 | 17:15–18:05 to 17:14–18:04 CT (−1 min) | RDU→SGF within 240 minutes. |
| 1589 MFE–MCI | 135 | 12:19–14:54 to 12:16–14:51 CT (−3 min, supporting adjustment) | Restores F2019's MCI turn from an illegal 37 minutes to 40; the preceding MFE turn remains 46 minutes. |

The first three advances are retained once, not applied again. Round two adds the three requested timing changes and the minimum F1589 adjustment required by the 40-minute turn rule. All other 1,183 flights retain their complete identities and clocks.

## Joint validation and connection tradeoff

The draft retains 1,190 flights, 181 routes and 19 lines. Structure, operating, overnight, planning and fixed physical gates/stands pass with zero effective operating errors, 166 existing advisories and 14 stand claims / 3,253 minutes. No new override or bank change is introduced.

Compared with v1.2.5, the app and 2.25× circuity audits lose no existing direct/one/two-stop itinerary choice, market coverage or one-stop market. There are 20 new app itinerary choices and nine new one-stop directional markets: BLV→SFB, GPT→SFB, MKE→SFB, PGD→CAK, DSM→CAK, FSD→CAK, DAL→PNS, VPS→BWI and RDU→SGF.

F1589's earlier departure creates a small travel-time tradeoff: 17 MFE-origin fastest app journeys become 1–3 minutes longer (nine under the circuity screen). All their itineraries remain available; the onward arrival time is fixed while the first departure is earlier. Fastest travel improves in 111 app markets (85 under the circuity screen). Full market details are in `connection_review.json`.

MKE→SFB's new one-stop option takes 7h57 versus the retained 5h10 two-stop option. PGD→CAK's new one-stop option takes 8h50 versus the retained 5h45 two-stop option. Fewer connections do not always mean a faster trip.

## R307 PIT hold review

PIT's current 11:24–16:46 ET hold is ten minutes too short for PIT–BHM–PIT. A [validated modification proposal](schedule_7_v1_3_0_r307_review.md) exists, but the extension is not accepted: delaying the subsequent PHF flying costs 19 itinerary choices and makes PIT→DAL's fastest journey 140 minutes slower. The accepted draft has no added R307 legs or R307 clock changes.

## Reproduction and pending work

`python scripts/build_schedule_7_v1_3_0_draft.py` replays the cumulative `config/optimizations/schedule_7_v1_3_0_round_2.json` from the SHA-pinned v1.2.5 canonical. Source identity, stale-input guards, seven exact changed flights, all unchanged flights, fleet, policies and banks are checked before full validation. Round one's overlay remains available as historical evidence.

`node scripts/audit_schedule_7_v1_3_0_connections.mjs --accepted-only` requires all six requested one-stop markets, no lost service and no slower journey outside the reviewed MFE-origin 1–3-minute tradeoff.

The earlier [shared-hub effort review](schedule_7_v1_3_0_shared_hub_gaps.md) covers CAK–PGD, BLV–HOU, MYR–RFD and BNA–OMA. Only its PGD→CAK repair is accepted. The other reports describe the older two-flight draft and remain historical analysis, not joint validation against the current draft.

Main and `web/schedules.json` remain on released v1.2.5. Publication of v1.3.0 requires a later explicit user instruction. Regression policy is latest-only; do not reconstruct superseded releases for regression.
