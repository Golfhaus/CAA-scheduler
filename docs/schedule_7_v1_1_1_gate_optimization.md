# Schedule 7 v1.1.1 gate-assignment optimization

Schedule 7 v1.1.1 is a gate-only patch based on the approved v1.1.0 selected
PHF bank-cluster model. It does not change the timetable, routes, fleet counts,
bank assignments, or north-south connection coverage.

## Problem

The fixed-inventory allocator could split a long gate claim during an early
greedy conflict rescue and retain the resulting stand tow even after a complete
gate recoloring made the split unnecessary. Route 339 at PHF exposed the issue:
its 13:16 arrival used Gate 16, moved to Stand 4 from 14:01 to 15:15, and moved
again to Gate 3 before its 16:15 departure.

## Patch

After establishing a feasible gate-and-stand assignment, the allocator now
tests every conditional stand middle in shortest-duration order. It rejoins the
arrival touch, stand middle, and departure touch into one continuous gate claim
whenever exact recoloring keeps all claims inside the fixed gate and stand
inventory. Forced stand splits remain untouched.

Route 339 now stays on one PHF gate for its complete 13:16-16:15 turn. The exact
gate number can change as the complete claim set is recolored; continuity, not
a particular numbered gate, is the invariant.

## Result

- No flight, route, fleet, bank, or connection change.
- Route 339's avoidable PHF stand tow is eliminated.
- PHF stand claims fall from 17 to 9.
- Systemwide stand claims fall from 52 to 33.
- Systemwide stand occupancy falls by 4,557 minutes, or 75 hours 57 minutes.
- Structural validation passes with zero effective operating errors and zero
  hard-stop failures.
- Every passenger arrival and departure remains gate-handled.

## Release

This gate-only patch is released once as v1.1.1. Further Schedule 7 changes
advance under v1.1.2.
