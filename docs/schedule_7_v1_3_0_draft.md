# Schedule 7 v1.3.0 working draft

Unpublished. Start from released v1.2.5 at `c5c3550a24080a91d1e5d0fcee9a97673c3fe8e3`. The current destination roster, fleet inventory, demand-data v7, hubs/focus city, gates/stands and policies are retained.

## Scope

Continue aircraft utilization, improve connecting banks within hubs and BHM, and investigate markets lacking nonstop or one-connection service. Retain separate directional coverage and geographic-circuity audits. Pinned O-D measures market size, not forecast CAA loads.

## Accepted round 1, October 12, 2026

The user approved F1437 −2 minutes, F1036 −1 minute and F2017 −2 minutes for the v1.3.0 draft. The first two advances were already present; the October 12 follow-up adds F2017 without applying either earlier change twice.

| Flight | Route | Change, local times | Result |
|---|---|---|---|
| 1437 JAX–SFB | 351 | 16:15–17:00 to 16:13–16:58 ET | BLV and GPT arrivals at 12:13 now connect within 240 minutes. JAX turn is 41 minutes; the later SFB return is unchanged. |
| 1036 MCI–SFB | 713 | 10:35 CT–14:08 ET to 10:34 CT–14:07 ET | MKE arrival at 06:34 CT now connects within 240 minutes. MCI turn is 89 minutes. |
| 2017 MCI–CAK | 170 | 15:37 CT–18:42 ET to 15:35 CT–18:40 ET | PGD arrival at 11:35 CT now connects within 240 minutes. Also creates DSM→CAK and FSD→CAK one-stop service. MCI turn is 41 minutes; subsequent flying is unchanged. |

All other 1,187 flights keep their full identities and clocks. The draft retains 1,190 flights, 181 routes and 19 lines. Structure, operating, overnight, planning and fixed physical gates/stands pass with zero effective operating errors, 166 existing advisories and 14 stand claims / 3,253 minutes. No new override or bank change is introduced.

The joint whole-timetable comparison loses no existing direct/one/two-stop itinerary, loses no market coverage, and slows no fastest journey, both in the app and under the 2.25× circuity screen. It adds 16 itinerary choices and six one-stop directional markets: BLV→SFB, GPT→SFB, MKE→SFB, PGD→CAK, DSM→CAK and FSD→CAK. BLV's fastest journey improves from 7h31 to 6h43. The new MKE one-stop journey takes 7h57; its existing 5h10 two-stop journey remains faster. The new PGD→CAK one-stop journey takes 8h50; its existing 5h45 two-stop journey remains faster. Fastest travel improves in 34 app markets (31 under the circuity screen).

## Reproduction and next work

`python scripts/build_schedule_7_v1_3_0_draft.py` replays `config/optimizations/schedule_7_v1_3_0_round_1.json` from the SHA-pinned v1.2.5 canonical and regenerates the isolated draft package. Source identity, stale-input guards, the three exact changed flights, all unchanged flights, fleet, policies and banks are checked before full validation. `node scripts/audit_schedule_7_v1_3_0_connections.mjs --accepted-only` regenerates the accepted draft's connection review and requires all three target markets plus no lost service or slower fastest journeys.

The completed [shared-hub effort review](schedule_7_v1_3_0_shared_hub_gaps.md) covers CAK–PGD, BLV–HOU, MYR–RFD and BNA–OMA. Its PGD→CAK repair is now accepted and jointly validated with the two Sanford advances. BLV→HOU, OMA→BNA and the larger scenarios remain proposals. Their saved reports describe the earlier two-flight draft and are retained as historical evidence; use the accepted-only audit above for the current draft.

Main and `web/schedules.json` remain on released v1.2.5. Publication of v1.3.0 requires a later explicit user instruction. Current regression policy is latest-only; do not reconstruct superseded releases for regression.
