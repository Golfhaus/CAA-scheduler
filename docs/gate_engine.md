# Gate engine

Milestone 0.2 replaces the separate chart and JSON copies of the legacy gate algorithm with `caa_scheduler.gates`. Both future validation and every gate-facing export must call this module.

## Deterministic flow

1. Group canonical legs by Line and Day while preserving canonical Line insertion order.
2. Build same-day turn claims and next-day RON claims, including the last-day-to-day-1 wraparound.
3. Add origin-only claims only after all arrival-side claims for the Line exist, preventing duplicate wraparound departures.
4. Pack short claims first using cyclic interval overlap.
5. Split a long claim only when it rescues a short claim or when the long claim would otherwise occupy a stand directly.
6. Keep explicit provenance for true stand-middle pieces so they cannot be split recursively or compacted back to a gate.
7. Compact any remaining gate-touch piece when a physical gate is free.
8. Serialize gate/stand rows, movement links, adjacent cities, and the 15-minute sampled peak used by the existing web app.

## Versioned ground-handling choices

Forced stand splits are data, not hardcoded exceptions. Schedule 6 v2.2.5 records the established BHM `103 -> 103` split in `gatePlan.forcedStandSplits`. A future repair UI will edit this structured plan and rerun validation.

## Golden result

For Schedule 6 v2.2.5 the exporter reproduces the frozen `gate_sked6_v2_2_5.json` file byte for byte: 105 cities and 1,463 assigned claim pieces, including row placement, gate/stand movement links, fleet colors, city order, and peak use.
