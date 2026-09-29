# Schedule 7 v1.1.6 optimization

Schedule 7 v1.1.6 begins from released v1.1.5. Round 1 evaluates the late
originators on Routes 306, 339, 331, and 149 as potential feeders for BHM's
existing morning connection wave.

## Round 1 result

Three of the four aircraft can operate an early BHM round trip while preserving
their existing routes.

| Route | Prior originator | Added flying | Existing continuation |
| --- | --- | --- | --- |
| 306 | CLT-BDL at 12:00 | CLT-BHM 04:30-04:45; BHM-CLT 07:40-10:55 | CLT-BDL remains at 12:00 |
| 339 | SAV-PHF at 11:50 | SAV-BHM 04:30-04:43; BHM-SAV 07:45-09:58 | SAV-PHF remains at 11:50 |
| 149 | DAY-HOU at 10:00 | DAY-BHM 04:30-05:01; BHM-DAY 07:32-10:03 | DAY-HOU moves to 11:15 |
| 331 | BWI-PHF at 10:05 | Deferred | Existing route remains unchanged |

Route 149's DAY-HOU departure moves to 11:15. It still has a 67-minute turn at
HOU before the unchanged 14:00 HOU-DAY flight, and its 19:40 DAY-GRR terminator
is unaffected.

The added CLT, SAV, and DAY arrivals reach BHM before the 06:00 wave. They can
connect within the configured 30-240 minute window to the existing departures
for MCI, LBB, SRQ, PIE, AUS, DAL, and FLL. Their 07:32-07:45 returns can receive
connections from the existing SGF, XNA, TUL, HOU, and OKC arrivals. The result
is bidirectional connectivity rather than a one-way positioning exercise.

## Capacity treatment

BHM has six gates and four stands. The existing bank uses all six gates around
06:20, so the three added aircraft unload at gates and move to stands before the
peak. They return to gates in the order that existing departures release them:

| Route | Arrival gate touch | Stand hold | Departure gate touch |
| --- | --- | --- | --- |
| 339 | 04:43-05:28 | 05:28-06:45 | 06:45-07:45 |
| 306 | 04:45-05:30 | 05:30-06:40 | 06:40-07:40 |
| 149 | 05:01-05:46 | 05:46-06:32 | 06:32-07:32 |

BHM peaks at eight of its ten physical positions. It has four stand claims
totaling 290 minutes. Systemwide stand use changes from 21 claims and 8,440
minutes to 24 claims and 8,134 minutes: the three new BHM stand segments are
more than offset by shorter overnight holds at the origin cities.

## Why Route 331 is deferred

BWI has two gates and two stands. Its 04:35 and 05:05 originators already use
both gates during the window in which Route 331 would have to depart for BHM.
Adding a third passenger departure creates gate touches on stands and fails the
fixed-inventory rules. Waiting until a gate releases reaches BHM after the
available morning gate window and pushes the existing Route 331 sequence by
roughly 30-50 minutes. That broader re-bank is not justified for this tactical
round, so Route 331 remains unchanged.

## Generalized tactics

### Use late originators as pre-bank feeders

A route with a late first flight can make a useful early round trip when the
return preserves a legal turn into the original itinerary. The useful target
is a connection wave, not merely additional block time.

### Stagger returns against actual gate releases

At a full bank, schedule each held aircraft's return to a gate when a specific
bank departure releases capacity. This converts a nominally impossible peak
into a feasible gate-stand-gate sequence without increasing fixed inventory.

### Compare total stand time, not only claim count

Three additional short day-hold claims at BHM replace longer overnight holds
elsewhere. Claim count rises, but total stand minutes fall. Both measures are
needed to evaluate whether a towing pattern is operationally useful.

### Protect a constrained origin instead of forcing all candidates

An available aircraft is not enough if its origin station cannot support the
passenger gate touch. When a small station is already at fixed gate capacity,
defer the extension unless a wider bank or rotation change has independent
benefit.

## Draft status

The cumulative v1.1.6 feasibility draft has 1,068 legs across the same 179
routes, 23 lines, and fleet inventory as v1.1.5. Structural and planning
validation pass with zero effective operating errors and zero hard-stop
failures. It adds no §2.6 city-departure-gap finding. The draft remains
unpublished and is not exposed in the application manifest.

## Round 2: independent early-terminator extensions

Round 2 evaluates Routes 148, 525, and 346 independently because their
terminating cities do not support a useful common-bank strategy.

| Route | Prior terminator | Added flying | Final terminator |
| --- | --- | --- | --- |
| 148 | DAY at 15:32 | DAY-RFD-DAY, 17:30-20:28 | DAY |
| 525 | SAT at 15:56 | SAT-SFB-SAT, 16:45-22:35 | SAT |
| 346 | HRL at 16:22 | HRL-AUS-HRL, 17:02-19:52 | HRL |

Route 148 adds a third DAY-RFD round trip. RFD has approximately 24.0 daily
directional O&D passengers from DAY, the strongest practical late-day market
available to the aircraft. The departure uses DAY Bank 7 and the return reaches
Bank 8. An earlier departure would improve the returning connection window,
but every tested passenger touch before 17:30 exceeded DAY's fixed 16-gate
inventory. The selected timing is therefore capacity-bound rather than merely
turn-time-bound.

Route 525 adds the first SAT-SFB round trip. At approximately 131.1 daily
directional O&D passengers, SFB is by far SAT's strongest unserved market that
fits the remaining aircraft day. The 21:00 SFB departure is exactly at the
normal destination cutoff and returns the aircraft to SAT at 22:35 without a
curfew exception.

Route 346 adds the first HRL-AUS round trip. AUS is HRL's strongest unserved
feasible market at approximately 24.1 daily directional O&D passengers. Its
short block time produces the best demand per added aircraft minute and returns
the aircraft to HRL at 19:52.

The round adds six legs and 578 productive block minutes. All three aircraft
still finish at their prior RON cities, so the following Routes 149, 526, and
347 remain unchanged.

### Round 2 capacity and policy result

The cumulative draft reaches 1,074 legs without adding an aircraft-day, route,
line, operating override, or §2.6 finding. Structural, planning, curfew, turn,
gate, stand, fixed-inventory, and operating-error checks pass.

DAY stand use falls from one claim and 673 minutes after Round 1 to zero because
Route 148 now returns after the peak. Systemwide stand use falls from 24 claims
and 8,134 minutes to 23 claims and 7,461 minutes. RFD, SAT, SFB, HRL, and AUS
remain within their existing physical inventories, and no passenger handling
occurs on a stand.

### Round 2 generalized tactics

#### Let the fixed gate release determine the extension start

Minimum aircraft turn time is not always the binding constraint. Route 148
could physically leave DAY at 16:12, but DAY cannot support another passenger
gate touch until 17:30. Starting at the first capacity-safe minute prevents an
apparently useful extension from creating a hidden stand operation.

#### Use a curfew boundary when it unlocks a materially stronger market

The SAT-SFB round trip works only because the return leaves SFB at 21:00, the
last minute of its normal departure window. Exact-boundary placement is useful
when it enables a substantially stronger market and retains adequate recovery
time at the RON city.

#### Prefer demand per block minute when no bank objective applies

At a non-hub terminator with several point-to-point choices, raw demand alone
does not measure aircraft productivity. HRL-AUS combines the highest available
demand with a short sector and an early return, making it stronger than longer
alternatives with similar or lower demand.

## Round 3: PHF early hub round trips

Round 3 uses three late PHF originators for simultaneous 04:30 departures to
DAY, SYR, and JAX. Each aircraft returns before its existing originator.

| Route | Added flying | PHF return | Existing originator | PHF turn | Margin above minimum |
| --- | --- | --- | --- | --- | --- |
| 330 | PHF-DAY-PHF | 08:20 | PHF-BWI at 09:15 | 55 min | 15 min |
| 338 | PHF-SYR-PHF | 08:25 | PHF-PVD at 09:15 | 50 min | 10 min |
| 719 | PHF-JAX-PHF | 08:22 | PHF-SFB at 09:10 | 48 min | 8 min |

Route 330 arrives at DAY at 05:59 and departs at 06:51. The return timing is
the user-selected compromise between a minimum turn and waiting for DAY Bank 2.
It reaches PHF at 08:20, five minutes before PHF Bank 2, and retains fifteen
minutes of recovery above the minimum turn before the existing originator.

Route 338 arrives at SYR at 05:53 and departs at 07:02. The return departure is
between SYR Banks 1 and 2, an explicitly approved bank exception, but reaches
the opening of PHF Bank 2 at 08:25.

Route 719 arrives at JAX at 06:06 and uses the minimum 40-minute turn requested
by the user, departing at 06:46. It returns to PHF at 08:22, three minutes
before Bank 2, rather than delaying the JAX departure solely for alignment.

The round adds six legs and 536 productive block minutes. The cumulative draft
now has 1,080 legs with no additional aircraft-day, route, or line. Structural,
planning, curfew, turn, gate, stand, fixed-inventory, and §2.6 spacing checks
pass. Four explicit bank-alignment overrides record the selected Route 330,
338, and 719 timing tradeoffs.

PHF stand use falls from five claims and 1,719 minutes after Round 2 to three
claims and 446 minutes. Systemwide stand use falls from 23 claims and 7,461
minutes to 21 claims and 6,188 minutes. DAY, SYR, JAX, and PHF remain within
their fixed physical inventories, and the three added round trips can operate
simultaneously without passenger handling on stands.

### Round 3 generalized tactic

#### Treat near-bank alignment as a tradeoff, not an absolute

A small bank miss can be preferable when waiting would consume nearly all of
the recovery margin before an existing originator. Record the exception
explicitly, verify that it does not create gate or connection harm, and retain
the faster turn when its operational value exceeds a cosmetic bank alignment.

## Release

Rounds 1 through 3 are published together as Schedule 7 v1.1.6. The release
contains 1,080 legs across the same 179 routes, 23 lines, and fleet inventory.
It passes structural and planning validation with zero effective operating
errors and zero hard-stop failures. Systemwide stand use is 21 claims and
6,188 minutes, including three PHF claims totaling 446 minutes. The application
exposes `schedule_7_v1_1_6` as the default package; feasibility checkpoints
remain internal.
