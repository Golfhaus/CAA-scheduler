# Schedule 7 v1.3.0 accepted draft and promotion record

Promoted to released v1.3.0 on October 12, 2026 after the user approved the buffered PIT–DAY–PIT round trip and publication. Based on v1.2.5 at `c5c3550a24080a91d1e5d0fcee9a97673c3fe8e3`. The destination roster, fleet inventory, demand-data v7, hubs/focus city, gates/stands and policies are retained. The [release notes](schedule_7_v1_3_0_release.md) and released canonical are authoritative; this draft package remains a reproduction checkpoint.

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

The accepted draft has 1,192 flights, 181 routes and 19 lines. Structure, operating, overnight, planning and fixed physical gates/stands pass with zero effective operating errors, 165 advisories and 14 stand claims / 3,253 minutes. No new override or bank-window change is introduced. New flights 2193/2194 on R307 use existing DAY-B5.

Compared with v1.2.5, the app and 2.25× circuity audits lose no existing direct/one/two-stop itinerary choice, market coverage or one-stop market. There are 190 new app itinerary choices and twelve new one-stop directional markets: BLV→SFB, GPT→SFB, MKE→SFB, PGD→CAK, DSM→CAK, FSD→CAK, DAL→PNS, VPS→BWI, RDU→SGF, PIT→BHM, MCI→PIT and PIT→GRR.

F1589's earlier departure creates a small travel-time tradeoff: 17 MFE-origin fastest app journeys become 1–3 minutes longer (nine under the circuity screen). All their itineraries remain available; the onward arrival time is fixed while the first departure is earlier. Fastest travel improves in 134 app markets (102 under the circuity screen). Full market details are in `connection_review.json`.

MKE→SFB's new one-stop option takes 7h57 versus the retained 5h10 two-stop option. PGD→CAK's new one-stop option takes 8h50 versus the retained 5h45 two-stop option. Fewer connections do not always mean a faster trip.

## R307 PIT hold review

R307's former 11:24–16:46 ET PIT hold was ten minutes too short for the direct BHM round trip. That [proposal](schedule_7_v1_3_0_r307_review.md) remains rejected/pending because it disrupts PHF connections. The user instead accepted the [buffered DAY alternative](schedule_7_v1_3_0_r307_day_review.md): F2193 PIT–DAY 12:38–13:35 ET and F2194 DAY–PIT 14:20–15:17 ET, with 74/45/89-minute turns. Existing R307 clocks are unchanged. PIT→BHM connects via DAY at 16:13 ET and reaches BHM at 16:44 CT, a 5h06 journey.

## Reproduction and pending work

`python scripts/build_schedule_7_v1_3_0_draft.py` replays cumulative `config/optimizations/schedule_7_v1_3_0_round_3.json` from SHA-pinned v1.2.5. It verifies the seven retimings, exactly two insertions, existing clocks and identities, permitted R307 sequence renumbering, fleet, policies, bank windows and assignments. Earlier overlays remain historical evidence.

`node scripts/audit_schedule_7_v1_3_0_connections.mjs --accepted-only` requires all nine primary target markets, no lost service and no slower journey outside the reviewed MFE-origin 1–3-minute tradeoff.

The earlier [shared-hub effort review](schedule_7_v1_3_0_shared_hub_gaps.md) covers CAK–PGD, BLV–HOU, MYR–RFD and BNA–OMA. Only its PGD→CAK repair is accepted. The other reports describe the older two-flight draft and remain historical analysis, not joint validation against the current draft.

Publication was explicitly authorized October 12, 2026. Main and `web/schedules.json` select released v1.3.0. The public package is reproduced by `python -m caa_scheduler build-optimization-release config/optimizations/schedule_7_v1_3_0_release.json`. Regression policy remains latest-only.
