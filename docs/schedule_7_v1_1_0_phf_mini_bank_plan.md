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

## Feasibility checkpoint 03

The remaining eight target cities fit on three new CRJ700 aircraft-days already
available inside the released fleet count. No released leg moves or disappears,
and CRJ700 use increases from 51 to 54 against the fixed count of 65.

The routes deliberately pair southern arrivals with northern departures. Their
09:35 PHF arrivals connect to 10:45 northern departures in 70 minutes. The
northern returns reach PHF at 14:11 or 14:27 and connect to the two 17:15
southern departures in 168-184 minutes. Both directions remain inside the
30-240-minute connection window.

All times below are local.

### Route 352 — PGD, MHT, and MLB

| Sequence | Leg | Time |
| ---: | --- | --- |
| 1 | PHF-PGD | 04:37-06:46 |
| 2 | PGD-PHF | 07:26-09:35 |
| 3 | PHF-MHT | 10:45-11:56 |
| 4 | MHT-PHF | 12:56-14:27 |
| 5 | PHF-MLB | 17:15-19:10 |
| 6 | MLB-PHF | 19:50-21:45 |

### Route 353 — SRQ, ALB, and VPS

| Sequence | Leg | Time |
| ---: | --- | --- |
| 1 | PHF-SRQ | 04:41-06:48 |
| 2 | SRQ-PHF | 07:28-09:35 |
| 3 | PHF-ALB | 10:45-12:08 |
| 4 | ALB-PHF | 12:48-14:11 |
| 5 | PHF-VPS | 17:15 ET-18:19 CT |
| 6 | VPS-PHF | 18:59 CT-22:03 ET |

### Route 354 — PNS and ROC

| Sequence | Leg | Time |
| ---: | --- | --- |
| 1 | PHF-PNS | 04:39 ET-05:47 CT |
| 2 | PNS-PHF | 06:27 CT-09:35 ET |
| 3 | PHF-ROC | 10:45-12:08 |
| 4 | ROC-PHF | 12:48-14:11 |

### Bank use

- `PHF-M0`, 04:30-05:30: three early southern departures.
- `PHF-M1`, 09:35-10:35: three new southern arrivals bring the complete bank
  to seven operations.
- `PHF-B3`, 10:45-11:45: three northern departures use the released bank.
- `PHF-M3`, 14:05-15:05: three northern arrivals bring the complete bank to
  eight operations.
- `PHF-M5`, 16:25-17:25: the MLB and VPS departures join the BUF departure.
- `PHF-M7`, 21:45-22:15: the MLB and VPS returns finish the operating day.

The cumulative checkpoint is expressed as the round-one overlay followed by
`config/optimizations/schedule_7_v1_1_0_round_2.json`. The overlay engine now
supports guarded creation of new aircraft routes and rejects duplicate route
numbers, duplicate line/day identities, unknown fleets, duplicate leg IDs, and
station-discontinuous route definitions.

### Combined validation result

- 948 legs, 179 routes, and 22 lines.
- Structural validation passes.
- Zero effective operating errors and zero hard-stop failures.
- Curfews, 40-minute turns, pairing spacing, route continuity, line continuity,
  and fleet capacity all pass.
- Fixed physical gate/stand inventory passes at every station.
- PHF peaks at 22 aircraft against 16 gates plus 8 stands.
- Conditional stand holds increase from 45 to 52; every passenger arrival and
  departure remains at a gate.
- Endpoint peaks are 2 positions at MHT, ALB, ROC, MLB, PGD, SRQ, and PNS and
  1 position at VPS, all inside fixed inventory.
- MLB, PGD, PNS, ROC, SRQ, and VPS use explicit Schedule-7-only hub-count
  exceptions. ALB and MHT remain inside their ordinary caps.
- Review-class findings increase by three: two deliberate long PHF holds and
  the new three-route Line AS falling below the standing 9-12-route guideline.
  None is an operating error or hard stop.

## v1.1.0 release package

The cumulative overlays are released as `schedule_7_v1_1_0` with a
reproducible release configuration and command. The package regenerates the
canonical schedule, timetable, gate schedule, structural and operating
validation, reconstructed planning snapshot, and a pair-by-pair PHF connection
audit. Upstream demand-allocation artifacts are intentionally omitted because
they were not rerun for the approved overlay.

The connection audit distinguishes network coverage from timed connectivity:

- All 14 initiative cities have a direct PHF round trip.
- 34 of 98 directional north-south pairs meet the 30-240-minute connection
  window.
- North-to-south coverage is 14 of 49 directional pairs.
- South-to-north coverage is 20 of 49 directional pairs.

The selected-bank-cluster model is approved for this version. It does not
represent universal pairwise north-south connectivity; additional pairwise
coverage is deferred to future Schedule 7 versions.

## Release decision

The selected-bank-cluster model is the final v1.1.0 release. The archival
Schedule 6 baseline is not rerun. Additional pairwise PHF connectivity remains
future-version work rather than a blocker for v1.1.0.
