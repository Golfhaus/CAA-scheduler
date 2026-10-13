# R307 PIT–DAY–PIT alternative

Originally reviewed October 12, 2026 against the seven-retiming v1.3.0 draft. The user subsequently accepted the buffered option and authorized v1.3.0 publication. Flights 2193/2194 below are included in the release; the three alternatives remain historical proposals. See the [release notes](schedule_7_v1_3_0_release.md).

## Recommended buffered timing

| New CRJ700 flight | Local times, all ET |
|---|---|
| PIT–DAY, provisional F2193 | 12:38–13:35 |
| DAY–PIT, provisional F2194 | 14:20–15:17 |

Both sectors use the repository's 57-minute CRJ700 block model. R307's existing PIT arrival remains 11:24, its PIT–PHF departure remains 16:46, and its PHF–CHS flight retains its clock. The resulting turns are 74 minutes in PIT, 45 in DAY and 89 back in PIT. DAY's arrival and departure both fit existing B5. This adds 114 block minutes using the existing aircraft-day, with no bank, fleet, policy or override change.

Full structure, operating, overnight, planning and fixed gate/stand validation passes: zero effective operating errors, 165 advisories (one fewer long hold), and unchanged 14 stand claims / 3,253 minutes. All existing flight clocks and identities are preserved; route sequence numbers alone accommodate the inserted legs.

## BHM connection

The new outbound arrives DAY at 13:35 ET. Existing F1981 leaves DAY at 16:13 ET and arrives BHM at 16:44 CT. The transfer is 158 minutes (2h38), safely inside 30–240, and total travel is 5h06. Circuity is 1.127×. PIT→BHM currently requires two connections: the fastest app option is 7h30, or 8h12 under the 2.25× screen. This adds one-stop coverage and improves elapsed time by 2h24 against the app.

The recommended 14:20 DAY–PIT return cannot receive BHM's morning F2070, which reaches DAY at 10:03: the 257-minute wait exceeds the cap. Existing BHM→PIT one-stop service via JAX remains available.

## Other improvements

Fastest times below compare the accepted draft's current app to the buffered proposal. Every proposed itinerary in the table passes the 2.25× distance screen. Demand is pinned one-direction average daily O-D market size, not projected loads.

| Direction | O-D/day | Current fastest | Proposed fastest | Result |
|---|---:|---|---|---|
| PIT→DAL | 80.5 | 4h32 | 3h51 | 41 minutes faster; earlier afternoon arrival |
| HOU→PIT | 57.3 | 5h25 | 4h27 | 58 minutes faster |
| PIT→RDU | 52.5 | 3h07 | 2h54 | 13 minutes faster |
| AUS→PIT | 51.1 | 4h59 | 4h27 | 32 minutes faster |
| MCI→PIT | 21.3 | 8h35, two stops | 3h37, one stop | New one-stop coverage; 4h58 faster |
| PIT→MCI | 21.3 | 5h00 | 3h17 | 1h43 faster |
| PIT→BHM | 12.8 | 7h30, two stops | 5h06, one stop | New one-stop coverage |
| PIT→GRR | 4.8 | 7h41, two stops | 4h35, one stop | New one-stop coverage |

The app gains 170 itinerary choices and 23 faster directional journeys, with zero lost choices, zero lost direct/one-stop coverage and zero slower fastest journeys. The 2.25× comparison identifies 21 improvements, including three extra coverage gains for short markets whose old app connections exceed the distance screen. Strong two-stop improvements also include OMA→PIT, PIT→TUL, PIT→ELP, PIT→LIT, PIT→JAN and PIT→LBB; they remain two-stop journeys.

PIT–DAY local demand is only 0.6 passengers/day each direction. This extension's case rests on connecting value and use of the existing hold, not local demand.

## Timing tradeoffs and two-way BHM option

The search exhausts all 210 minute-level combinations that fit unchanged R307 clocks, 40-minute turns and current DAY banks. Within these constraints, the best demand-weighted elapsed-time score departs PIT 12:43, reaches DAY 13:40 and returns 14:20–15:17. It puts PIT→DAL/RDU/MCI at exactly 30-minute transfers and PIT→BHM at 5h01. Moving one minute later to 12:44–13:41 produces a five-hour BHM trip but loses those three DAY-B5 connections. The recommended 12:38 departure gives five minutes of connection margin and a 45-minute aircraft turn, at the cost of five minutes of outbound elapsed time.

An earlier option uses PIT–DAY 12:25–13:22 and DAY–PIT 14:02–14:59 ET. It also passes full validation, with 61/40/107-minute turns. It permits BHM→DAY on F2070, 07:32 CT–10:03 ET, followed by the new 14:02 DAY–PIT flight: a 239-minute transfer and 6h27 total travel. This is longer than the existing 6h04 one-stop via JAX, but gets passengers into PIT at 14:59 instead of 21:19. Its PIT→BHM journey is 5h19. It improves inbound HOU/AUS/MCI/RFD→PIT more, while reducing outbound time savings. No existing choice or coverage is lost and no fastest journey slows.

The user selected the buffered timing for DAY connections and a 45-minute aircraft turn. The earlier option is not accepted. Both preserve the PHF flights and the fast PIT→DAL connection that the direct BHM extension disrupted.

## Reproduction

- `python scripts/review_schedule_7_v1_3_0_r307_day.py`
- `node scripts/audit_schedule_7_v1_3_0_r307_day.mjs`
- `python scripts/review_schedule_7_v1_3_0_r307_day.py --validate`

These commands and proposal overlays reproduce the historical review at commit `c3f51b03aa326cc5933c0754be764030566cac21`, before acceptance; they are pinned to that seven-retiming draft. Saved evidence is under `outputs/schedule_7_v1_3_0_r307_day/`. Current accepted flying uses the round-three overlay and release configuration instead. Review scripts reject an accepted or stale baseline before overwriting historical reports.
