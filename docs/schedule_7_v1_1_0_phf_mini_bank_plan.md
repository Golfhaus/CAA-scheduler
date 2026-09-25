# Schedule 7 v1.1.0 PHF mini-bank plan

Schedule 7 v1.1.0 begins from released v1.0.0 at commit `5154a58`.
The first optimization round adds north-south connectivity through PHF while
preserving the released network as much as possible.

## Scope and guardrails

- North of PHF: PWM, MHT, BDL, ALB, ROC, BUF, and PIT.
- South of PHF: DAB, MLB, PGD, SRQ, VPS, BHM, and PNS.
- Use small PHF banks in the gaps between the seven released banks. Prefer a
  released bank feeding a mini-bank and a mini-bank feeding the next released
  bank.
- First use idle time on already-scheduled aircraft. Unused CRJ700 or CRJ900
  capacity may be considered later for larger cities.
- Do not remove existing flying, expand physical gate/stand inventory, waive a
  curfew, or add fleet silently.
- Stop for review before a proposal displaces an existing flight, changes a
  different line, or needs additional fleet.
- Route 309 remains deferred to the later western-network effort.

## Resolved policy decision

For the remainder of Schedule 7, the normal percentile-tier hub-count cap may
receive a city-specific exception without another approval checkpoint when the
additional hub is geographically reasonable, materially advances the active
initiative, and the added service passes all downstream checks. The cap remains
in force everywhere else.

Use the existing operating-policy override mechanism for each affected city.
Each exception must name `tiered_service_minimums`, identify the city finding,
state the applicable initiative as its reason, and expire after Schedule 7.
No additional user approval is required for a qualifying exception, but every
exception remains explicit and auditable rather than becoming a blanket
relaxation.

## Feasibility checkpoint 01

Two self-contained CRJ700 opportunities pass timetable, curfew, route,
gate/stand, and full operating validation against the v1.0.0 schedule.

### Route 307 — CLT hold and PIT service

The existing CLT-PHF leg moves from 15:15-16:21 to 08:29-09:35 on the same
route. No flight is removed and no additional CLT-PHF frequency is created.
The aircraft then operates a new PHF-PIT round trip before continuing the
existing PHF-CHS flight.

| Sequence | Leg | Time |
| ---: | --- | --- |
| 1 | SYR-CLT | 05:50-07:37 (unchanged) |
| 2 | CLT-PHF | 08:29-09:35 (retimed) |
| 3 | PHF-PIT | 10:15-11:24 (new) |
| 4 | PIT-PHF | 16:46-17:55 (new) |
| 5 | PHF-CHS | 18:35-19:50 (unchanged) |

The late PIT return avoids creating another long PHF hold and feeds directly
into released bank PHF-B6.

### Route 312 — DAB-PHF-BDL relay

The existing BDL-DAB and DAB-BDL flights remain unchanged. Four legs use the
long DAB hold to add complete PHF round trips for both DAB and BDL.

| Sequence | Leg | Time |
| ---: | --- | --- |
| 1 | BDL-DAB | 04:30-07:07 (unchanged) |
| 2 | DAB-PHF | 07:47-09:35 (new) |
| 3 | PHF-BDL | 10:15-11:35 (new) |
| 4 | BDL-PHF | 12:45-14:05 (new) |
| 5 | PHF-DAB | 14:45-16:33 (new) |
| 6 | DAB-BDL | 21:00-23:37 (unchanged) |

### PHF bank use

- `PHF-M1`, 09:35-10:35: two arrivals (CLT and DAB) and two departures
  (PIT and BDL). It lies wholly between PHF-B2 and PHF-B3.
- `PHF-M3`, 14:05-15:05: one arrival (BDL) and one departure (DAB). It lies
  wholly between PHF-B4 and PHF-B5.
- PIT-PHF arrives in PHF-B6 at 17:55 and turns to the existing PHF-CHS
  departure at 18:35.

The mini-banks are deliberately undersized at this checkpoint. Later additions
can fill them toward the requested roughly seven-flight scale without changing
their approved windows.

## Validation result

The checkpoint contains 922 legs, 176 routes, and 21 lines.

- Structural validation: pass (18/18 checks).
- Effective operating errors: zero.
- Hard-stop failures: zero.
- Fixed physical gate/stand inventory: pass at every station.
- PHF peak occupancy: 20 aircraft against 16 gates plus 8 stands, unchanged
  from the released peak.
- Endpoint peaks: PIT 2, DAB 1, BDL 3, and CLT 5; all fit their fixed physical
  inventory.
- DAB and PIT require the approved Schedule-7-only hub-count exceptions. BDL
  remains within its ordinary cap.
- The result remains `review`, rather than `pass`, because the released
  schedule already carries four warning-class reviews and runway screening is
  not evaluated where source data is absent. No new hard stop is hidden by
  those warnings.

## Feasibility checkpoint 02

The two BWI and two PHF early terminators can all accept productive missions
without additional aircraft or changes to their released legs. These missions
also remain compatible with the Route 307 and Route 312 checkpoint above.

### Routes 330 and 331 — complementary BWI-BHM-PHF triangles

The two routes operate opposite sides of the same triangle and still terminate
at BWI.

| Route | Added sequence | Times |
| ---: | --- | --- |
| 330 | BWI-BHM; BHM-PHF; PHF-BWI | 15:23-16:20; 17:00-19:50; 20:30-21:18 |
| 331 | BWI-PHF; PHF-BHM; BHM-BWI | 13:17-14:05; 14:45-15:35; 16:15-19:12 |

This creates a complete PHF-BHM round trip while using the otherwise-idle BWI
aircraft. BHM and BWI receive explicit Schedule-7-only hub-count exceptions.

### Routes 314 and 337 — PHF northern round trips

| Route | Added sequence | Times |
| ---: | --- | --- |
| 314 | PHF-PWM; PWM-PHF | 14:05-15:46; 16:26-18:07 |
| 337 | PHF-BUF; BUF-PHF | 16:25-17:48; 18:28-19:51 |

Both routes already terminate at PHF, so the missions preserve line continuity
and reduce their unproductive overnight gate holds.

### Expanded mini-bank use

- `PHF-M1`, 09:35-10:35: Route 307 and Route 312 turns.
- `PHF-M3`, 14:05-15:05: five operations from Routes 312, 314, and 331.
- `PHF-M5`, 16:25-17:25: the Route 337 departure to BUF.
- `PHF-M6`, 19:45-20:05: the BUF and BHM arrivals, feeding PHF-B7.

The complete checkpoint is expressed deterministically in
`config/optimizations/schedule_7_v1_1_0_round_1.json` and applied by
`caa_scheduler.optimization_overlay`. The overlay rejects a stale base timing,
cannot delete existing flying, inherits route/fleet identity from the released
schedule, and assigns new flight and pairing identifiers deterministically.

### Combined validation result

- 932 legs, 176 routes, and 21 lines; no additional aircraft.
- Structural validation passes.
- Zero effective operating errors and zero hard-stop failures.
- Curfews, 40-minute turns, pairing spacing, route continuity, line continuity,
  and fleet capacity all pass.
- Fixed physical gate/stand inventory passes at every station.
- PHF peaks at 21 aircraft against 16 gates plus 8 stands.
- Conditional stand holds increase from 44 to 45; none is passenger handling.
- BHM, BWI, DAB, and PIT use explicit Schedule-7-only hub-count exceptions.

## Next phase

Search other productive holds and the available CRJ700/CRJ900 capacity for the
remaining targets: MHT, ALB, ROC, MLB, PGD, SRQ, VPS, and PNS. Test them in this
order:

1. timetable and 40-minute-turn feasibility;
2. PHF gate feasibility;
3. endpoint gate feasibility;
4. complete operating validation;
5. full-cycle continuity and fleet use.

Only survivors advance. Any survivor that removes an existing leg, changes a
different line, or needs fleet beyond the released counts is held for an
explicit decision.
