# Schedule 7 v1.1.2 route-extension checkpoints

## Round 1 — short CRJ700 routes

This first feasibility checkpoint extends the four CRJ700 route-days in
v1.1.1 that contained only one or two flights. It retains every released leg,
uses the same 54 CRJ700 aircraft-days, and does not alter the web-app schedule
manifest.

| Route | v1.1.1 | v1.1.2 feasibility | Rationale |
|---|---|---|---|
| 306 | CLT–SYR | CLT–BDL–CLT–SYR | Adds eastern frequency without forcing a seventh daily CLT–PHF flight. A tested SYR turn exceeded the fixed 16-gate passenger capacity. |
| 323 | SRQ–SYR | SRQ–SYR–PHF–SYR | Adds one PHF round trip through existing SYR-B4/B5 and PHF-M3/B5 windows. |
| 344 | SRQ–SYR–MCI | SRQ–SYR–MCI–HRL–MCI | Keeps the aircraft west once it reaches MCI and raises MCI–HRL to three round trips. |
| 350 | ELP–MCI–ELP | ELP–MCI–ELP–MCI–ELP | Keeps the route western and raises ELP–MCI to three round trips. |

## Checkpoint result

- 956 legs, up from 948
- 179 routes and 22 lines, unchanged
- 54 CRJ700 aircraft-days, unchanged
- zero structural failures, effective operating errors, or hard-stop failures
- fixed physical gate and stand inventory passes
- 33 stand claims, unchanged; total stand time falls from 21,761 to 21,037 minutes
- PHF remains at 9 stand claims and 5,616 stand minutes

This intermediate checkpoint is not listed separately in `web/schedules.json`;
its changes are incorporated into the final v1.1.2 release.

## Round 2 — MCI flying on Routes 101, 133, 152, 153, and 526

Round 2 chains from the CRJ700 checkpoint and adds 14 legs without changing any
released v1.1.1 leg. Routes 101, 133, and 152 gain useful flying, while the long
MCI ROD periods on Routes 153 and 526 are converted into revenue trips.

| Route | Round-2 path | Added MCI flying |
|---|---|---|
| 101 | TOL–DAY–BNA–DAY–ATW–MCI–MSN–MCI–ATW | One MSN round trip while preserving the ATW terminator |
| 133 | SHV–MCI–SDF–MCI | One SDF round trip |
| 152 | MCI–SHV–MCI–SBN–MCI | One SBN round trip |
| 153 | MCI–OMA–MCI–SDF–MCI–XNA–BHM–VPS | One SDF round trip inside the former MCI ROD |
| 526 | SAT–MCI–MSN–MCI–ATW–MCI–RDU | MSN and ATW round trips inside the former MCI ROD |

The additions create two daily MCI round trips each to MSN, ATW, and SDF, plus
one daily MCI round trip to SBN. Route 153's MCI ground time falls from 541 to
311 minutes. Route 526's MCI ground time falls from 639 to 198 minutes.

### Round-2 checkpoint result

- 970 legs, up from 956 after Round 1
- 179 routes and 22 lines, unchanged
- all CRJ200, CRJ700, and CRJ900 aircraft-day counts unchanged
- zero structural failures, effective operating errors, or hard-stop failures
- all four planning-reconstruction checks pass
- fixed physical gate and stand inventory passes with every passenger touch at a gate
- 32 stand claims and 19,729 stand minutes, down from 33 and 21,037 after Round 1
- MCI remains at 8 stand claims while stand time falls from 5,244 to 4,822 minutes
- PHF remains unchanged at 9 stand claims and 5,616 stand minutes

Round 2 was finalized with Round 1 as `schedule_7_v1_1_2`. The released package
is listed in `web/schedules.json` and is the app's default schedule.
