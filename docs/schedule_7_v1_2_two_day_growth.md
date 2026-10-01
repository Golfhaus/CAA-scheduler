# Two-spare-MAX9 DAY/JAX growth draft

> Release update, October 1, 2026: the approved cumulative changes are now
> published as v1.2.0. See `schedule_7_v1_2_0_release.md` and
> `regression_policy.md` for current release and testing policy. The
> feasibility/default statements below describe the original draft stage.


This supersedes the one-spare options as the current growth proposal. It
adds a consecutive two-day sequence at the SFB boundary of MAX9 Line A,
preserving all existing flights, times, numbers, fleets, pairings and bank
assignments. The user explicitly requested two spare MAX9s, a two-day
Line A insertion, second flights before additional service to markets with
more flights, and preferably four daily flights each way between DAY and JAX.

## Daily service gains

| Pairing | Before, each direction | After, each direction |
|---|---:|---:|
| DAY–JAX | 1 | 4 |
| JAX–SFB | 1 | 2 |
| JAX–FLL | 1 | 2 |
| DAY–CMH | 1 | 2 |
| DAY–CAK | 1 | 2 |
| DAY–IND | 1 | 2 |
| DAY–RFD | 3 | 3 |

Both new route-days operate **every calendar day**, occupied by different
aircraft positions in the rotation. They do not alternate service days.
Three new MAX9 flights plus the unchanged CRJ700 yield four daily flights
in each direction on the inter-hub pairing.

PGD, PIE and SRQ at JAX and PIT at DAY remain at one flight each way in
this draft. RFD's fourth flight is deferred under the requested priority.
Serving all nine one-flight spoke markets and adding three inter-hub round
trips would require 24 new legs, 1,640 block minutes and at least 880
same-day turn minutes: 42 aircraft operating hours before bank waits.
The two-day insertion cannot accommodate that full set under the departure
windows. The selected five markets balance JAX's two strongest opportunities
with three underserved DAY markets. This is a tested candidate, not a proof
of global optimality across every possible insertion and timing.

## Two-day sequence

Insert after the current A day 2 / Route 702 terminates at SFB at 19:25.
The new days become A day 3 / Route 703 and A day 4 / Route 704. Existing
A days 3–11 become 5–13. Existing MAX9 routes at or above 703 shift upward
by two, retaining consecutive numbering; B's day sequence is unchanged.

All proposed times are Eastern. Flight numbers are draft assignments.

| New day | Route | Flight | From | To | Departure | Arrival |
|---|---:|---:|---|---|---|---|
| 1 / A3 | 703 | 2083 | SFB | JAX | 04:30 | 05:18 |
| 1 / A3 | 703 | 2084 | JAX | DAY | 06:15 | 08:04 |
| 1 / A3 | 703 | 2085 | DAY | CAK | 09:10 | 10:02 |
| 1 / A3 | 703 | 2086 | CAK | DAY | 10:42 | 11:34 |
| 1 / A3 | 703 | 2087 | DAY | JAX | 12:14 | 14:03 |
| 1 / A3 | 703 | 2088 | JAX | FLL | 14:50 | 16:00 |
| 1 / A3 | 703 | 2089 | FLL | JAX | 16:40 | 17:50 |
| 1 / A3 | 703 | 2090 | JAX | DAY | 18:36 | 20:25 |
| 2 / A4 | 704 | 2091 | DAY | JAX | 05:09 | 06:58 |
| 2 / A4 | 704 | 2092 | JAX | DAY | 07:38 | 09:27 |
| 2 / A4 | 704 | 2093 | DAY | CMH | 10:07 | 10:49 |
| 2 / A4 | 704 | 2094 | CMH | DAY | 11:29 | 12:11 |
| 2 / A4 | 704 | 2095 | DAY | IND | 13:20 | 14:07 |
| 2 / A4 | 704 | 2096 | IND | DAY | 14:47 | 15:34 |
| 2 / A4 | 704 | 2097 | DAY | JAX | 16:16 | 18:05 |
| 2 / A4 | 704 | 2098 | JAX | SFB | 18:47 | 19:35 |

The following existing route starts at SFB at 05:25. The three new overnight
boundaries provide 545 minutes at SFB, 524 at DAY, and 590 at SFB. The first
new day has 619 block minutes / 15:55 aircraft operating span; the second
has 553 block minutes / 14:26 span. Crew assignments and relief are a
separate planning requirement.

| Direction | Daily departures after insertion |
|---|---|
| JAX–DAY | 06:15 MAX9, 07:38 MAX9, 15:45 CRJ700, 18:36 MAX9 |
| DAY–JAX | 05:09 MAX9, 08:00 CRJ700, 12:14 MAX9, 16:16 MAX9 |

## Feasibility and standing guideline

The draft has 1,096 legs, 181 routes and 20 lines. MAX9 use becomes 23 of
35, leaving 12 spare. A has 13 days and B has 10. The explicit two-day
insertion into the existing 11-day A line authorizes this specific length;
the ordinary 9–12 standing guideline is unchanged and remains visible as
an operating warning. The feasibility runner accepts the narrow, documented
Line A length authorization in this proposal rather than disabling the
general check.

Structural, planning and overnight validations pass. There are zero
effective operating errors and zero hard-stop failures, with no new
bank exceptions or curfew waivers. All passenger handling fits physical
gates. Systemwide stand use stays at 20 claims / 5,552 minutes, exactly
the approved draft's count and minutes.

Recovery margins need attention. DAY–JAX at 12:14 is one minute before
DAY Bank 4 closes at 12:15 and follows a minimum 40-minute turn. JAX–SFB
at 18:47 leaves two minutes before the existing 18:49–19:25 full-gate
period. Arriving DAY at 20:25 instead of 20:12 avoids an otherwise
impermissible passenger touch on a stand. These timings fit the frozen
schedule but are sensitive to operational delay.

## Two-stop connection accounting

The earlier screen considered nonstops and one-stops. An inter-hub flight
also carries passengers connecting on **both** ends, for example
MKE–DAY–JAX–SFB. The new analysis therefore compares both the baseline
and candidate against all eligible zero-, one- and two-stop choices
through all six hubs/focus cities. It does not alter timetable display
rules or published connection policy.

Both transfers must have 30–240-minute waits. All visited airports must
be distinct, and total circuity must be at most 2.25. The choice weight
is `0.35^stops / elapsed² / circuity²` for connecting trips and
`1 / block²` for nonstops. The two-stop penalty is an explicit heuristic
extension of the prior one-transfer penalty, not calibrated behavior.
Each directional daily demand pool is allocated once across all its choices.
On a two-stop itinerary, the middle flight receives **through opportunity
once**, rather than separately counting the passenger in both inbound and
outbound totals.

| New inter-hub flight | One-stop-only proxy | Expanded proxy | Through opportunity |
|---|---:|---:|---:|
| JAX–DAY 06:15 | 56.7 | 184.1 | 127.1 |
| JAX–DAY 07:38 | 102.1 | 536.8 | 431.4 |
| JAX–DAY 18:36 | 19.9 | 19.7 | 0.0 |
| DAY–JAX 05:09 | 10.8 | 10.6 | 0.0 |
| DAY–JAX 12:14 | 180.9 | 707.2 | 497.5 |
| DAY–JAX 16:16 | 80.7 | 640.2 | 538.4 |

The early DAY departure has almost no inbound feed. The late JAX departure
arrives DAY after useful onward departures. They are commercially weak
rotation/availability legs used to reach four daily flights each way.
Expanding the connection model does not repair these two slots.

Existing flights also share the expanded demand pool. For example, the
unchanged 08:00 DAY–JAX CRJ700 falls from 562.7 to 366.1 opportunity units
when all new flights compete. This is reallocation and added itinerary
coverage, not evidence that frequency additions create new travelers.

All demand values assume full CAA capture and omit feeder seat caps,
fares/yields, operating costs and seasonality. Some values exceed aircraft
seating, so they are opportunity comparisons rather than predicted loads.
Airport catchment overlap and ground travel alternatives remain material.
CAK, CMH and IND would receive their first MAX9 service in this schedule.
Pinned airport data lacks runway and payload inputs, and physical gate
counts do not establish stand/gate geometry compatibility. These airport
compatibility checks remain unevaluated. Do not declare the weak availability legs commercially viable
solely because the aircraft and gates fit.

## Reproduction

Run `python scripts/build_schedule_7_v1_2_two_day_growth.py` to regenerate
the proposal, complete feasibility package, and joint two-stop analysis.
The overlay is `config/proposals/schedule_7_v1_2_0_two_day_growth.json`;
outputs are under `builds/schedule_7_v1_2_0_two_day_growth`.
The two approved overlays remain the ordinary builder's default; this
growth draft is built explicitly for review. Published v1.1.6, its default
manifest and app behavior are unchanged.

`tests/test_v120_two_day_growth.py` checks unchanged service and physical
inventory, exactly two new aircraft-days, four daily trunk flights each
way, second service on the selected one-flight markets, retained RFD
frequency, spacing, operating/planning/overnight validity, no additional
stand use, and single-count two-stop middle-leg allocation.
