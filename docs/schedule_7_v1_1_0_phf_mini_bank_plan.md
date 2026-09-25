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

## Next phase

Search the two BWI and two PHF early terminators for additional missions that
fit `PHF-M1` and `PHF-M3`, then test the remaining target cities in this order:

1. timetable and 40-minute-turn feasibility;
2. PHF gate feasibility;
3. endpoint gate feasibility;
4. complete operating validation;
5. full-cycle continuity and fleet use.

Only survivors advance. Any survivor that removes an existing leg, changes a
different line, or needs fleet beyond the released counts is held for an
explicit decision.
