# Planning engine

Milestone 0.7 introduces a deterministic planning layer between schedule setup and aircraft routing. Its first release deliberately reconstructs the final plan already represented by Schedule 6 v2.2.5; it does not claim to reproduce an unavailable raw-demand calculation.

## Durable planning snapshot

`planning_snapshot.json` is defined by [`schemas/planning_snapshot.schema.json`](../schemas/planning_snapshot.schema.json). It records:

- the schedule ID and pinned demand-data version;
- the aircraft count selected for each fleet in that schedule;
- aircraft-days used, leg counts, block minutes, minimum-turn minutes, and the resulting lower bound of required aircraft-minutes;
- directional market frequencies separated by fleet;
- departure totals by station;
- the hub assignments preserved in canonical city metadata;
- required hub-bank counts from the pinned operating policy; and
- explicit limitations describing inputs that are not yet available.

Fleet counts are never supplied by a planner constant. They come from `schedule.fleetCounts`, which in candidate builds is copied from the approved `build_config.json`.

The reconstructed aircraft-minute lower bound is block time plus the minimum required turn between consecutive legs within every aircraft-day. It is more informative than the legacy flat flights-per-day capacity proxy, but it is not yet a routing feasibility proof. The routing and operating validators remain authoritative for the candidate actually produced.

## Reconstructed migration plan

`reconstruct_planning_snapshot()` groups canonical legs by fleet, origin, and destination. That produces the durable JSON equivalent of the final v2.2.5 `fleet_routes.pkl` contents while retaining provenance and validation. Station totals are derived from the same canonical legs, eliminating a separate file that had already drifted from v2.2.5.

The baseline has 1,383 legs, 928 directional fleet/market rows, 105 station totals, and four schedule-specific fleet types. Four snapshot checks verify that all canonical legs, cities, and configured fleets are represented.

## Multi-hub qualification

`compute_multihub_assignments()` is a pure function. It accepts city metadata, an explicit intergroup-demand dataset, city market sizes, and versioned planning rules. It has no hardcoded filesystem paths, import-time data loading, pandas dependency, pickle input, or mutable global state.

The preserved legacy thresholds and city-percentile caps now live in [`config/policies/planning_rules_v1.json`](../config/policies/planning_rules_v1.json). The formerly embedded post-BHM-annotation table is normalized as [`data/reference/intergroup_demand_v2.json`](../data/reference/intergroup_demand_v2.json), with its own schema. The function is covered by a deterministic regression test. It will not be applied to a real new schedule until the complete airport O-D demand input is also pinned in the repository or another approved input store.

## Commands and build integration

Reconstruct a standalone snapshot with:

```bash
python -m caa_scheduler reconstruct-plan \
  canonical_schedule.json planning_snapshot.json \
  --validation-output planning_validation_report.json \
  --demand-version <pinned-version>
```

The golden-baseline and candidate commands generate the same two planning artifacts automatically. If a candidate violates a hard stop such as a curfew, its canonical, timetable, and gate outputs remain suppressed. The planning snapshot and diagnostic validation reports are retained so the failed build can be investigated.

## Next construction stages

The remaining Milestone 0.7 work is intentionally staged:

1. normalize and pin the complete airport O-D data;
2. reproduce demand allocation and final fleet assignment from those inputs;
3. define and place hub-bank windows;
4. construct aircraft lines, days, routes, and RONs without global state; and
5. add deterministic repair candidates followed by full structural, operating, gate, and curfew validation.

Each stage needs a golden comparison before the subsequent stage is permitted to write a publishable candidate.
