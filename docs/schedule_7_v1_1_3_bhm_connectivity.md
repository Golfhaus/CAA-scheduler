# Schedule 7 v1.1.3 BHM connectivity checkpoints

Schedule 7 v1.1.3 begins from released v1.1.2. It was developed through four
unpublished feasibility checkpoints, then released as the application's
default schedule. The initiative makes BHM more useful as a secondary
connecting point for the Florida Peninsula (`FLP`) group.

## Round 1 — MCI/DAY feed and new PIE/SFB service

The first feasibility checkpoint adds ten legs to four CRJ200 route-days. It
does not add an aircraft-day, change a route origin or terminator, or alter the
application's released-schedule manifest.

| Route | v1.1.3 feasibility path | Purpose |
|---|---|---|
| 117 | MCI–OMA–MCI–BHM–SFB–BHM–MCI–PIA | Converts the long MCI hold into MCI feed and a new BHM–SFB round trip. |
| 128 | TUL–BHM–PIE–BHM–DAB–BHM–HRL–BHM–SGF | Converts the morning BHM hold into a new BHM–PIE round trip. |
| 139 | DAY–TOL–DAY–BHM–DAY–SBN–DAY–TRI | Uses the DAY hold to add a BHM feeder without changing the TRI terminator. |
| 162 | COU–MCI–CID–MCI–BHM–MCI–DSM | Implements the requested MCI–BHM extension and moves the DSM terminator later. |

The midday BHM wave has MCI and DAY arrivals at 13:14 and 12:33, followed by
the SFB departure at 13:54. SFB returns at 17:38 and connects to MCI at 18:18.
The later Route 162 movement reaches BHM at 15:45 and returns to MCI at 20:56,
after which the aircraft terminates at DSM at 22:26.

PIE and SFB increase BHM's directly served FLP destinations from four to six:
DAB, EYW, PGD, PIE, SFB, and SRQ. The new timing adds usable BHM connections
from MCI to SFB, from DAY to SFB, from SFB to MCI, and from PIE to DAY while
retaining the existing BHM connection opportunities.

## Checkpoint result

- 980 legs, up from 970 in v1.1.2
- 179 routes and 22 lines, unchanged
- zero structural failures, effective operating errors, or hard-stop failures
- all planning-reconstruction checks pass
- fixed physical gate and stand inventory passes with every passenger touch at a gate
- 31 stand claims and 18,789 stand minutes, down from 32 and 19,729 in v1.1.2
- MCI falls from 8 stand claims / 4,822 minutes to 6 / 4,139
- PHF remains unchanged at 9 stand claims and 5,616 minutes

The extra late MCI work is represented by one 20:45–21:45 mini-bank. PIE and
SFB use explicit Schedule-7 focus-city exceptions because BHM is a deliberate
additional connecting point for FLP traffic.

The new MCI–BHM flights use CRJ200 aircraft while the released MCI–BHM market
also has CRJ700 service. Mixed-fleet service across a pairing is permissible by
default; single-fleet patterns are an aircraft-assignment outcome rather than an
operating-policy requirement.

## Round 2 — PHF/FLL and reverse DAY feed

Round 2 uses two additional early terminators without retiming any released or
Round 1 flight.

| Route | Cumulative v1.1.3 path | Purpose |
|---|---|---|
| 138 | HSV–DAY–MSN–DAY–TRI–DAY–BHM–DAY | Extends the 15:33 DAY terminator and gives FLL passengers a 44-minute BHM connection to DAY. |
| 715 | SFB–RDU–SFB–PHF–BHM–FLL–BHM–PHF | Extends the 10:51 PHF terminator with new BHM–FLL service and returns to PHF at 20:35. |

FLL is the highest-demand FLP city that lacked BHM service. Its new BHM round
trip also creates 40-minute through connections in both directions with PHF.
The PHF arrival at BHM additionally connects to SFB in 98 minutes. FLL's BHM
arrival connects onward to MCI in 68 minutes and DAY in 44 minutes.

The cumulative checkpoint serves seven of the nine FLP destinations from BHM:
DAB, EYW, FLL, PGD, PIE, SFB, and SRQ. GNV and MLB remain unserved from BHM;
their low demand and the more intrusive late-day patterns required to add them
did not justify forcing them into this round.

### Cumulative checkpoint result

- 986 legs, up from 970 in v1.1.2
- 179 routes, 22 lines, and all fleet aircraft-day counts unchanged
- zero structural failures, effective operating errors, or hard-stop failures
- all planning-reconstruction checks pass
- fixed physical gate and stand inventory passes with every passenger touch at a gate
- 31 stand claims and 17,519 stand minutes, down from 32 and 19,729 in v1.1.2
- MCI remains at 6 stand claims / 4,139 minutes after Round 1
- DAY falls to 1 stand claim / 1,003 minutes
- PHF remains at 9 stand claims while stand time falls to 5,126 minutes
- BHM uses 1 stand claim for 97 minutes

The cumulative checkpoint is defined by the Round 1 overlay followed by
`config/optimizations/schedule_7_v1_1_3_round_2.json`. Neither draft schedule is
listed in `web/schedules.json`; v1.1.2 remains the released application default.

## Round 3 — second FLL frequency from an MCI terminator

Route 524 previously ended at MCI at 10:41 after a single SAT–MCI flight. Round
3 extends it as SAT–MCI–BHM–FLL–BHM–MCI and returns the aircraft to its original
MCI terminator at 22:40. No prior flight is retimed.

The second BHM–FLL round trip is separated from Route 715's frequency by 184
minutes outbound and 186 minutes inbound. MCI passengers reach the second FLL
departure through BHM in 123 minutes; the return connects back to MCI in 40
minutes. The later FLL arrival at BHM also feeds the established late DAB, PGD,
and EYW departures.

This alternative was preferred over forcing GNV or MLB service. FLL is a
98th-percentile market, while adding either remaining unserved FLP destination
required longer late-day patterns for substantially lower demand.

### Cumulative Round 3 result

- 990 legs, up from 970 in v1.1.2
- 179 routes, 22 lines, and all fleet aircraft-day counts unchanged
- zero structural failures, effective operating errors, or hard-stop failures
- fixed physical gate and stand inventory passes
- 30 stand claims and 17,268 stand minutes, down from 32 and 19,729 in v1.1.2
- MCI falls to 5 stand claims / 3,888 minutes
- DAY remains at 1 stand claim / 1,003 minutes
- PHF remains at 9 stand claims / 5,126 minutes
- BHM remains at 1 stand claim / 97 minutes

The later Route 524 arrival uses a 22:15–23:15 MCI mini-bank. The cumulative
candidate is defined by the three v1.1.3 overlays in order. All three remain
unpublished and absent from `web/schedules.json`.

## Round 4 — productive use of the longest CRJ200 daytime holds

Round 4 evaluates the six longest CRJ200 ROD holds from Round 3. Four holds
produce useful new BHM feed without forcing marginal flying; the two rejected
holds are described below.

| Route | Cumulative v1.1.3 path | Purpose |
|---|---|---|
| 164 | JAN–MCI–OMA–BHM–OMA–MCI–MAF | Converts the OMA hold into BHM feed, with 40-minute OMA–SFB and FLL–OMA connections. The later OMA–MCI–MAF sequence remains banked and curfew-safe. |
| 102 | ATW–DAY–ATW–BHM–ATW–DAY–AVL | Adds ATW feed to the FLL and SFB departures and carries the PGD arrival back to ATW without retiming existing flying. |
| 130 | CID–MCI–ICT–BHM–ICT–MCI–CRP | Adds ICT access to the later FLL departure and returns DAB/EYW traffic to ICT without changing the existing ICT–MCI–CRP sequence. |
| 161 | FAR–MCI–FSD–BHM–FSD–MCI–COU | Adds FSD feed to SFB/FLL and a 40-minute PGD–FSD connection without retiming existing flying. |

The added Route 164 departure would otherwise create a seventh simultaneous
passenger touch against BHM's six gates. Route 156's existing BHM–TUL–BHM–ECP
sequence therefore moves earlier: BHM–TUL departs at 17:10 instead of 18:00,
and the route terminates at ECP at 22:55. This preserves the fixed gate/stand
inventory and substitutes the stronger FLL–OMA opportunity for the former
FLL–TUL connection.

Route 158 was not extended. A through MCI–BHM–GNV–BHM–MCI pattern fit the
aircraft-day only by stacking new MCI–BHM and MCI–DSM departures inside the
same-pairing spacing limits; a simple MCI–BHM turn duplicated already abundant
MCI feed. Route 165 was also left unchanged because Route 102 supplies the
useful ATW–BHM frequency without forcing a second ATW trip across DAY and SYR
bank boundaries.

### Cumulative Round 4 result

- 998 legs, up from 970 in v1.1.2
- 179 routes, 22 lines, and all fleet aircraft-day counts unchanged
- zero structural failures, effective operating errors, or hard-stop failures
- all planning-reconstruction checks pass
- fixed physical gate and stand inventory passes
- 29 stand claims and 16,822 stand minutes, down from 32 and 19,729 in v1.1.2
- MCI remains at 5 stand claims / 3,888 minutes
- DAY remains at 1 stand claim / 1,003 minutes
- PHF remains at 9 stand claims / 5,126 minutes
- BHM remains at 1 stand claim / 97 minutes

The released schedule is defined by the four v1.1.3 overlays in order. It is
listed in `web/schedules.json` as the application's default schedule; the four
feasibility checkpoint IDs remain unpublished.
