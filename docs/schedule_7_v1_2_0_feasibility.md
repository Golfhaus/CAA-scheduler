# Schedule 7 v1.2.0 feasibility

## Round 1 — CRJ900 line compliance

The user approved the full line rearrangement on September 29, 2026. This
unpublished checkpoint starts exclusively from released `schedule_7_v1_1_6`.
The application manifest and released packages remain untouched. No MAX9
promotion is approved yet. The wider v1.2 objective is to use existing fleet
inventory productively while retaining 4–6 spare aircraft per fleet; aircraft
sizing must reflect useful demand rather than simply filling capacity.

The original CRJ900 lines AB/AG/AJ/AP contained 1/19/6/2 route-days. They are
reclosed as AB (10 days), AG (9 days), and AJ (9 days), using all 28 existing
CRJ900 aircraft-days. Seven simultaneous suffix exchanges preserve every
scheduled flight and market:

| Original routes | Exchange airport |
|---|---|
| 501 / 525 | SFB |
| 502 / 526 | MCI |
| 503 / 519 | JAX |
| 506 / 512 | JAX |
| 509 / 516 | PHF |
| 515 / 527 | SYR |
| 517 / 528 | SYR |

Fourteen original route-days exchange their latter portions; the other fourteen
retain their flight sequences. Every flight keeps its ID, flight number,
pairing, aircraft type, market, and bank assignment. Flight times are unchanged
except SFB–ABE (`ABE-SFB-CRJ900-01-IN`), which moves from 20:50–23:07 to
21:00–23:17. The former timing left only 30 minutes after the exchanged
inbound aircraft reached SFB at 20:20, ten minutes short of the required turn.
21:00 is within the normal destination departure window; no waiver is added.

The new CRJ900 route numbers are consecutive within each line. Use stable
flight IDs to trace historical release-note decisions across this renumbering.
The v1.1.5 late SYR–ORH / early ORH–SYR flights remain unchanged, as does the
v1.1.6 SAT–SFB extension. Their aircraft-day affiliations change where necessary.
Route numbers below refer to the released v1.1.6 originals and this checkpoint.

| Original route | New route | Line | Day |
|---|---|---|---|
| 501 | 501 | AB | 1 |
| 526 | 502 | AB | 2 |
| 503 | 503 | AB | 3 |
| 520 | 504 | AB | 4 |
| 502 | 505 | AB | 5 |
| 521 | 506 | AB | 6 |
| 522 | 507 | AB | 7 |
| 523 | 508 | AB | 8 |
| 524 | 509 | AB | 9 |
| 525 | 510 | AB | 10 |
| 504 | 511 | AG | 1 |
| 505 | 512 | AG | 2 |
| 506 | 513 | AG | 3 |
| 513 | 514 | AG | 4 |
| 514 | 515 | AG | 5 |
| 515 | 516 | AG | 6 |
| 528 | 517 | AG | 7 |
| 518 | 518 | AG | 8 |
| 519 | 519 | AG | 9 |
| 507 | 520 | AJ | 1 |
| 508 | 521 | AJ | 2 |
| 509 | 522 | AJ | 3 |
| 517 | 523 | AJ | 4 |
| 527 | 524 | AJ | 5 |
| 516 | 525 | AJ | 6 |
| 510 | 526 | AJ | 7 |
| 511 | 527 | AJ | 8 |
| 512 | 528 | AJ | 9 |

## Verification

- 1,080 legs, 179 routes, and 22 lines systemwide.
- Structural and reconstructed-planning checks pass.
- Zero effective operating errors and zero hard-stop failures.
- All three CRJ900 lines close across their overnight boundaries and include
  a hub/focus-city RON: AB at MCI; AG at PHF/SYR; AJ at BHM.
- Rolling maintenance-base RON validation passes without grace.
- Existing fleet counts and 28 CRJ900 aircraft-days remain unchanged; 17 CRJ900
  aircraft are spare. CRJ200/CRJ700/MAX9 operations are unchanged.
- Systemwide stand use remains 21 claims and 6,188 minutes. Gate export uses
  fixed physical inventory and passenger-touch checks pass.
- Banks, cities, operating policy, and approved exceptions are unchanged.
- Other fleets' pre-existing line-length warnings are outside this round's scope.

## Demand ranking after rearrangement

Pinned data: `bts-db1c-6mo-jul2025-apr2026-v7`. Each route's raw score sums the
directional daily O&D market demand associated with its flown legs; a line's
score averages those sums across its route-days. This is a market-strength
proxy, not expected onboard passengers, and repeated market service repeats
its raw market demand in this score.

| Line | Routes | Legs | Raw demand / route | Raw demand / leg | Frequency-divided O&D / route | Frequency-divided O&D / leg |
|---|---:|---:|---:|---:|---:|---:|
| AG | 9 | 48 | 227.689 | 42.692 | 93.242 | 17.483 |
| AJ | 9 | 48 | 217.444 | 40.771 | 86.271 | 16.176 |
| AB | 10 | 56 | 213.030 | 38.041 | 131.368 | 23.459 |

The frequency-divided comparison distributes each directional market's local
O&D evenly across all existing departures, including other aircraft types.
It omits connecting passengers and different demand by departure time.
AG leads the requested raw ranking; AB leads the frequency-divided comparison.
Both are surfaced before selecting a line for MAX9 conversion. No conversion
has been implemented. A nine-day conversion would provisionally increase
MAX9 use from 21 to 30 of 35 aircraft, leaving five spare, before checking
MAX9 block times, turns, gate effects, continuity, and maintenance requirements.

## Reproduction and regression

Run `python scripts/build_schedule_7_v1_2_feasibility.py`. The runner applies
`config/optimizations/schedule_7_v1_2_0_round_1.json` to the released v1.1.6
canonical file and writes draft-only review outputs under
`builds/schedule_7_v1_2_0_feasibility_01/`. This generated directory is ignored
by git and can be rebuilt from the committed overlay and source pins.
No released-status packaging function is used during feasibility work.

Focused checks: `python tests/test_v120_crj900_lines.py`. Routine regression
continues to cover the current engine, web console, and latest released v1.1.6
package. Historical reconstruction and Schedule 6 are excluded.

## Generalized tactics

- A line-length warning can require aircraft continuity changes even when every
  individual flight is operationally valid; zero errors does not imply all
  rotation guidelines are satisfied.
- Exchange suffixes at a shared station to change overnight successors while
  preserving the passenger timetable. Verify both new turns and full gate effects.
- Reclose and normalize rotations before ranking whole lines for fleet promotion.
- Check hub/focus-city overnight coverage independently of broader maintenance-
  target RON coverage; an outstation maintenance base alone is not the same rule.
- Preserve stable leg IDs and document route-number mappings through rotation
  changes so earlier bank and capacity decisions remain traceable.
