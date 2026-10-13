# R724 evening extension review — v1.3.1

Reviewed October 13, 2026 in response to the question about extending the new MAX9 beyond its 17:26 RFD terminator. **Historical comparison. MCI was accepted into the draft October 13, 2026; BHM, DAY and PHF remain unaccepted alternatives.** The tables below compare each option with the original four-leg draft; the current six-leg draft is documented in `schedule_7_v1_3_1_draft.md`. Published v1.3.0 is unchanged. Source: draft commit `7824040d363817d9d681d19de98d59aeeb8a076a`; canonical SHA-256 `448a9d9b15b871751d19371fad893d9313bf803f801775979aaecac985bbd23e`.

## Straightforward options

All three below fit the existing MAX9 aircraft-day, preserve all current flight times and all six original priority pairs' connections, return to RFD for the unchanged 04:35 SFB departure on R708, and pass native operating, curfew, bank, physical gate/stand, overnight and planning checks. They require no added aircraft, inventory or bank window. Prospective flight numbers F2199/F2200 are shared across mutually exclusive alternatives; F2199/F2200 now identify the accepted MCI flights. The other alternatives remain mutually exclusive historical proposals.

| Via | RFD outbound, local | Return to RFD, local | Added block | Total R724 block |
|---|---|---|---|---|
| **MCI** | 19:26 CT → 20:40 CT | 21:20 CT → 22:34 CT | 2h28 | 11h32 |
| **BHM** | 18:06 CT → 19:49 CT | 20:49 CT → 22:32 CT | 3h26 | 12h30 |
| DAY | 18:57 CT → 21:05 ET | 21:50 ET → 21:58 CT | 2h16 | 11h20 |

MCI is a strong option for balanced demand on both added legs, while BHM is attractive if the emphasis remains southern coverage. DAY is operationally feasible and short but offers no newly covered one-stop market and has substantially smaller local demand.

| Measure versus current four-leg draft | MCI | BHM | DAY |
|---|---|---|---|
| Underlying local O-D, both directions/day | 400.0 | 120.9 | 48.6 |
| Existing local departures each direction | 3 | 0 | 3 |
| Added app itinerary choices | 74 | 42 | 70 |
| Newly covered directional one-stop markets | SGF→RFD, LBB→RFD | RFD→OKC, LBB→RFD | None |
| Faster fastest journeys, full app | 10 | 8 | 9 |
| Lost itineraries/one-stop coverage/slower fastest journeys | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| Geographic-screen faster journeys | 8 | 8 | 9 |
| Extra-leg competitive opportunity indices, outbound/return | 143 / 144 | 231 / 84 | 99 / 88 |
| System stand minutes after extension | 3,595 | 3,597 | 3,631 |
| Reduction from draft's 3,903 stand minutes | 308 (5h08) | 306 (5h06) | 272 (4h32) |

Every option keeps 16 stand middles, with the saving entirely at RFD. No passenger handling occurs on a stand. MCI's turns are 120 minutes at RFD and 40 at MCI, with 6h01 before R708. BHM's are 40 and 60, with 6h03 before R708. DAY's are 91 and 45, with 6h37 before R708.

The opportunity indices screen direct/one-stop markets, exclude connecting claims for markets already served nonstop, apply the 2.25× distance screen, and divide underlying demand across the available choices of the same stop count. The competitive subset retains new coverage/local markets and options no more than 30 minutes slower than the prior fastest trip. **These are comparison indices, not forecast loads or captured passengers.** Local demand is spread across existing and proposed frequency; 400/day is not an assumption that each MCI flight fills with local passengers. Some existing nonstop markets may still use an evening connecting choice, but their O-D is excluded from the connecting-demand totals to keep the comparison conservative.

## Connection value

MCI fits its existing B10 arrival and M11 departure. The later return creates SGF→RFD in 2h44 and LBB→RFD in 4h24. It also improves RFD→MAF from 7h08 to 4h47, JAN→RFD from 4h32 to 3h29 and RFD→SAT from 5h34 to 5h25. The higher local demand and similar indices in both directions make it the balanced choice.

BHM creates nonstop service in both directions and adds an evening connection wave for southern traffic. It improves **RFD→ECP from a fastest 5h50 to 4h49**; the existing JAX one-stop option is 7h12. It improves SRQ→RFD from 5h25 to 4h32, creates RFD→OKC in 4h59, and improves RFD→TUL from 4h46 to 4h12. Its strongest gap gain, RFD→OKC, has underlying directional demand of 57.2/day, compared with MCI's SGF→RFD 26.2 and LBB→RFD 7.9. The return leg's more modest conservative demand index is the principal tradeoff. Selecting BHM would also add another useful hub/focus touch at RFD; the existing standing RFD hub-count exception's rationale should explicitly reflect that additional BHM service when the accepted overlay is built.

DAY improves RFD→CAK from 3h06 to 2h28, RFD→IND from 2h59 to 2h21, FWA→RFD from 4h43 to 2h33 and BWI→RFD from 3h29 to 3h06. Its new outbound must be separated from the existing 18:19 RFD→DAY departure. The selected 18:57 departure clears the spacing floor and reaches B9 at 21:05; the initial 18:20 trial failed spacing.

## Why the PHF trial is not recommended

An initial PHF round trip, RFD 18:05 → PHF 21:04 ET and PHF 21:45 → RFD 22:44 CT, needed just one-minute advances to F2197/F2198 and would connect ROA both ways. **It fails fixed gate assignment at RFD:** its late arrival overlaps the concentrated existing overnight arrivals and leaves two passenger touches off-gate. This is a hard stop, not a permissible stand hold.

A coordinated variant does pass native checks:

- F2197/F2198 advance 10 minutes, putting the afternoon JAX arrival at 15:20 and RFD return at 17:16.
- F1556 EYW→JAX advances 4 minutes; F1742 JAX→ECP and F1758 JAX→TLH advance 5 minutes each, preserving the ECP/TLH transfers at the 240-minute maximum.
- Add RFD 17:56 CT → PHF 20:55 ET, returning PHF 21:35 ET → RFD 22:34 CT.

It improves geographically suitable ROA service to RFD→ROA 3h44 and ROA→RFD 4h04. However, the global app audit loses **43 itinerary choices and one-stop coverage in six markets**: RFD→TYS, AGS, BTR, MOB, GPT and MCN. It slows 25 fastest journeys. Its added-leg conservative indices are only 37 and 54. Native legality alone does not make this a good network extension, so it remains an unaccepted alternative. A separate ROA repair can still be investigated without compromising the useful JAX feeder wave.

The first MCI trial arrived 19:44 and held to 21:20; it caused an MCI gate conflict. Moving the new arrival to 20:40 clears that conflict without altering existing flights. This is why the selected clock is later than the first physically possible arrival.

## Other high-demand cities

BWI and RDU have substantial RFD O-D but cannot support a simple same-evening out-and-back from the unchanged 17:26 terminator. At the earliest legal 18:06 RFD departure, the minimum-turn return would leave BWI at 21:37 ET or RDU at 21:39 ET, after the 21:00 destination departure limit. SFB/FLL/SRQ are also too long for the destination-curfew-bound return. DAL could fit aircraft time, but its earliest return conflicts with the existing 21:00 DAL→RFD flight's 30-minute spacing floor. BNA's return is likewise too close to its existing 20:45 departure under the non-hub pairing spacing target. They require more than a simple extension.

## Reproduction

```bash
python scripts/review_schedule_7_v1_3_1_evening.py
node scripts/audit_schedule_7_v1_3_1_evening.mjs
```

The Python script first reproduces the SHA-pinned historical four-leg input from round 1 without changing the current accepted draft, then enforces that historical fingerprint, validates four proposal overlays and original-flight preservation, and writes native evidence plus temporary candidate canonicals. The JavaScript script applies the app's full itinerary enumeration and geographic screen and asserts zero losses/slowdowns for the MCI, BHM and DAY options. PHF's losses are deliberately reported rather than treated as acceptable. The accepted draft is checked unchanged after both runs. Reports: `outputs/schedule_7_v1_3_1_evening/native_review.json` and `network_review.json`. Proposals: `config/proposals/schedule_7_v1_3_1_evening_{mci,bhm,day,phf}.json`.
