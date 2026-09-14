# Planning engine

Milestone 0.7 introduces a deterministic planning layer between schedule setup and aircraft routing. It reconstructs the final plan already represented by Schedule 6 v2.2.5 and independently processes the pinned raw-demand inputs. It does not yet claim that the historical scheduled frequencies were freshly generated from that demand.

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

The preserved legacy thresholds and city-percentile caps now live in [`config/policies/planning_rules_v1.json`](../config/policies/planning_rules_v1.json). The formerly embedded post-BHM-annotation table is normalized as [`data/reference/intergroup_demand_v2.json`](../data/reference/intergroup_demand_v2.json). The updated 105-city six-month airport matrix is stored as `data/reference/airport_od_matrix_consolidated_v2.csv`. A fingerprinted manifest pins all three inputs and their versions. The resulting calculation covers every active city and reproduces all 100 non-hub assignments in v2.2.5, including CHS at JAX/PHF/DAY and BTR at JAX.

## Commands and build integration

Reconstruct a standalone snapshot with:

```bash
python -m caa_scheduler reconstruct-plan \
  canonical_schedule.json planning_snapshot.json \
  --validation-output planning_validation_report.json \
  --demand-version <pinned-version>
```

Validate and reproduce the demand-driven hub plan with:

```bash
python -m caa_scheduler build-demand-plan \
  canonical_schedule.json \
  config/demand_data/bts_db1c_6mo_v1.json \
  demand_plan.json
```

The golden-baseline and candidate commands generate these planning artifacts automatically. Candidate construction resolves the demand version to exactly one manifest and verifies every source fingerprint; an unknown version or mismatch blocks publishable output. If a candidate violates a hard stop such as a curfew, its canonical, timetable, and gate outputs remain suppressed. The demand/planning snapshots and diagnostic validation reports are retained so the failed build can be investigated.

## Next construction stages

The remaining Milestone 0.7 work is intentionally staged:

1. reproduce frequency allocation and final fleet assignment from the pinned demand inputs;
2. define and place hub-bank windows;
3. construct aircraft lines, days, routes, and RONs without global state; and
4. add deterministic repair candidates followed by full structural, operating, gate, and curfew validation.

Each stage needs a golden comparison before the subsequent stage is permitted to write a publishable candidate.
