# Schedule 7 v1.4.2 — physical-route hold fit screening

Baseline: released `schedule_7_v1_4_1`. Executed `python scripts/v142_hold_fitter.py` in GitHub Actions run 39535225819, completed successfully. This is a route-slot screening pass, not a new schedule validation or aircraft release.

**Result:** Neither proposed round trip can simply fit inside an existing route's same-station ground hold at the selected connection times.

| Proposed insertion | Longest existing station hold | Best candidate | Why rejected |
| --- | ---: | --- | --- |
| SYR–RDU–SYR (11:20–15:00) | 212 min (3h32) | R524 / line AJ day 5, 18:54–22:26 | Too late, and full proposed service needs 220 flight/turn minutes plus 40-min bookend turns |
| DAY–SRQ–DAY (10:00–15:35) | 164 min (2h44) | R140 / line AF day 8, 11:26–14:10 | Required service takes 335 minutes plus 80 min bookends; no fit |
| BHM–BNA–BHM (13:35–16:45) | 202 min (3h22) | R149 / line AI day 6, 15:45–19:07 | Hold is later than target and cannot fit two flights with 40-minute bookend turns |

**Actionable conclusion:** Additional flying will need deliberate route reconstruction (replacement of existing flying), an added route day integrated into cyclic aircraft lines, or up to three aircraft released from the spare pool. Simple insertions are infeasible; do not consume spares or alter released flights without complete cyclic, physical-gate, maintenance, bank and itinerary tests.

The tactical-only 1,266-flight v1.4.2 draft remains reproducible and separately validated with two MCI flight retimings. The conceptual three-aircraft service is not yet in its canonical.
