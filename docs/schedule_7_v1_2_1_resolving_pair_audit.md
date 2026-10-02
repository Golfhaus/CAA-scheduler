# Existing aircraft for directional coverage remedies

Read-only analysis of the cumulative, unpublished v1.2.1 draft. All 181 route-days were screened for prefixes, suffixes and interior holds at the endpoints of SAT–MCI, JAN–MCI, CAE–PHF and PIT–SYR. No canonical schedule, configuration or published app was changed.

## Feasible evening extensions

All times in this table are Central. Demand results are for each pair added independently, using the existing full-capture, uncapped relative-choice O-D/one-stop/two-stop model. They are opportunity units, not predicted passenger loads; values above aircraft capacity are possible. Joint operating feasibility of all three pairs also passes.

| Route / aircraft / line-day | Existing finish | Trial outward flight | Trial return flight | Opportunity outward / return | Interpretation |
|---|---|---|---|---:|---|
| 508 / CRJ900 / AB8 | SAT 19:11 | SAT 20:19 → MCI 22:15 | MCI 22:55 → SAT 00:51 next day | 14.4 / 274.7 | Strong late inbound opportunity; outward leg has no connecting opportunity. Does not resolve the missing morning MCI→SAT period or daytime SAT outbound group coverage. |
| 131 / CRJ200 / AD21 | JAN 17:18 | JAN 19:05 → MCI 20:48 | MCI 21:28 → JAN 23:11 | 3.8 / 28.9 | Weak pair. Only 2.0 units connect onward from JAN (MAF and DSM); 27.1 connect inbound on the return. Morning inbound gap remains. |
| 163 / CRJ200 / AE13 | JAN 20:03 | JAN 20:43 → MCI 22:26 | MCI 23:06 → JAN 00:49 next day | 1.8 / 15.5 | Marginal extension. No outward connecting opportunity; defer. |

Structural, planning, bank/spacing, physical gate/stand, departure-window and next-day-turn checks pass with existing flight clocks retained. No passenger handling on stands is introduced. Next-day turns are respectively 7h54, 8h59 and 5h41. Aircraft performance remains unavailable in the source data; crew legality and economics are not established by the schedule validators.

## Promising aircraft time that cannot be used directly

- **307, CRJ700, AA7, PIT hold 11:24–16:46 Eastern:** PIT 12:09→SYR 13:15 / SYR 13:55→PIT 15:01 fits the hold and has isolated opportunity 223.1/121.8. The full gate allocator fails at SYR. All 19 tested timings satisfying both banks and pairing spacing fail the mandatory passenger-touch gate lower bound there. This would improve secondary midday intervals, rather than the main early inbound or late outbound gaps.
- **322, CRJ700, AH11, SYR hold 05:36–11:20 Eastern:** the morning SYR→PIT→SYR bank-compatible loop conflicts with existing PIT→SYR flight 1607 at 09:32. All three tested bank-compatible timings fail pairing spacing. A separate trial delaying flight 1607 to 10:01 restores the proposed 09:31 flight's 30-minute separation, but leaves only 11 minutes before flight 2111's SYR departure at 11:18; it fails the 40-minute turn requirement. It is not a single-flight timing fix.
- **122, CRJ200, AD12, SYR hold 05:38–11:08 Eastern:** no bank-compatible round trip fits the existing return deadline of 10:28.
- **CAE–PHF:** endpoint holds top out at 3h04, versus about 4h30 needed for flying and three turns. Existing originators/terminators cannot accommodate a normal-window round trip.
- **Morning SAT/JAN options:** SAT Route 509's 08:45 originator is at least 57 minutes short of a prefix round trip; JAN Route 132's 08:10 originator is at least 66 minutes short, even before bank alignment. Remaining MCI interior holds top out at 3h59 and cannot support either market's round trip.

The timing search uses a five-minute grid plus exact bank boundaries, normal departure windows, same fleet and overnight endpoints, minimum 40-minute aircraft turns and 40–240-minute away turns. No claim of exhaustively optimizing every minute or every possible retiming is made. The reproducible script writes its results only to ignored analysis output at `builds/schedule_7_v1_2_1_resolving_pairs.json`.
