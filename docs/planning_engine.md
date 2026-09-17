# Planning engine

Milestone 0.7 introduces a deterministic planning layer between schedule setup and aircraft routing. It preserves a reconstruction of Schedule 6 v2.2.5, independently processes the pinned raw-demand inputs, produces a fresh frequency and fleet proposal, and places proposed hub flying into generated bank windows without mutating the historical schedule.

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

## Fresh frequency and fleet allocation

`frequency_fleet_plan.json` is defined by [`schemas/frequency_fleet_plan.schema.json`](../schemas/frequency_fleet_plan.schema.json). Legacy v1–v3 plans start with the existing canonical market set. The v4 network boundary instead retains historical point-to-point markets, guarantees inter-hub coverage, and keeps only the effective hub/focus assignments permitted by each city's percentile tier. The v5 pin retains that boundary and adds per-fleet planning envelopes, a three-round-trip inter-hub ceiling, a single-fleet-per-market requirement, and a versioned routing reserve. Its reconciliation section records every city decision and every removed historical service market.

The calculation applies the standing rules directly:

- percentile-tier minimum flight totals, with at least one round trip to every assigned hub;
- square-root-damped demand shares for additional frequency;
- no more than six round trips per market;
- no discretionary point-to-point additions and no more than 10% point-to-point legs overall;
- largest-to-smallest fleet assignment by two-way market demand; and
- aircraft-minute capacity using great-circle block-time formulas plus the minimum turn.

The four fleet performance profiles and the 900-minute planning envelope live in the fingerprinted planning policy. Aircraft quantities do not: they are read exclusively from the schedule configuration. An unknown configured fleet requires a policy profile before allocation can proceed.

For the accepted Schedule 7 inputs, the v5 proposal passes all seven planning checks with 235 candidate markets, 703 round trips, 1,406 legs, and 9.0% point-to-point flying. It removes 131 historical hub/focus markets outside the effective tier boundary and uses an existing BHM market as one permitted slot for 20 cities in the documented FLP, GCP, OZK, and TEX groups. The accepted 1,430-leg ceiling remains fixed; a 12-round-trip reserve withholds only lowest-priority optional flying so the timed result can satisfy the selected fleet counts after spacing takes precedence over utilization.

Aircraft-minute allocation is not timed routing. Filling the planning envelope does not waive or pre-approve curfews, banks, gate capacity, RON placement, turn feasibility, or routing continuity. Those constraints remain authoritative when the proposal is materialized into canonical legs.

## Hub-bank generation and placement

`hub_bank_plan.json` is defined by [`schemas/hub_bank_plan.schema.json`](../schemas/hub_bank_plan.schema.json). The bank placer reads each hub's bank count and 60-minute core width from the pinned operating policy. It searches versioned five-minute phase candidates against the actual inter-hub fleet/block-time proposal; exact bank clock times are generated outputs, never fixed schedule constants.

Spoke arrivals target ten minutes into a core and hub departures target fifty minutes into it, preserving the 40-minute minimum turn. Inter-hub legs are placed only when the same local-time flight fits a departure bank at its origin and an arrival bank at its destination. Every proposed origin departure is checked against the normal/red-eye rules during placement. A violation is never accepted or waived: unplaceable service blocks the plan, while an actual curfew violation is marked as a hard stop.

For the Schedule 6 planning inputs, the generated plan defines all 24 required banks and places all 1,190 proposed hub-touching legs with 1,224 bank-touch assignments and zero curfew violations. The remaining 240 focus-city/point-to-point legs intentionally remain untimed until aircraft routing can place them around the banked work.

## Aircraft-cycle and RON feasibility

`aircraft_route_plan.json` is defined by [`schemas/aircraft_route_plan.schema.json`](../schemas/aircraft_route_plan.schema.json). The route planner minimum-cost matches every banked arrival to a same-fleet departure at the same station, inserts non-hub round trips into compatible layovers, and creates curfew-safe standalone cycles when no existing layover can hold a trip. It then evaluates service coverage, route continuity, the 40-minute turn floor, schedule-specific fleet capacity, curfews, destination RON coverage, and the rolling target-city RON window.

This stage never changes `schedule.fleetCounts`. It reports `configuredAircraft`, `requiredAircraft`, and `shortfall` separately for every fleet. Curfew enforcement is a hard stop at both bank placement and routing.

For the current Schedule 6 planning proposal, all 1,430 proposed legs enter continuous cycles, every destination receives an overnight, and no departure violates a curfew. The independent bank placements are not yet fleet-feasible: the first-pass cycles require 409 aircraft versus 225 configured, and one cycle misses the rolling target-RON cadence. This is a preserved diagnostic, not a suggested fleet order. Candidate publication remains blocked until deterministic repair retimes or reassigns the work within the selected fleet.

## Topology repair

`routing_repair_plan.json` is defined by [`schemas/routing_repair_plan.schema.json`](../schemas/routing_repair_plan.schema.json). It keeps the first-pass bank-cycle artifact intact, rebuilds each balanced directed fleet graph, searches deterministic Euler orderings for every connected component, partitions them into curfew-safe 03:00–03:00 route days, and uses available route-day endpoints to satisfy destination and rolling target-city RON requirements. Search bounds affect ordering only; every aircraft limit is read from `schedule.fleetCounts`.

On the v2.2.5 planning proposal, the repair retains all 1,430 legs in 209 route days against 225 configured aircraft: MAX9 29/35, CRJ900 39/45, CRJ700 62/65, and CRJ200 79/80. All seven topology checks pass, including the non-waivable curfew check, destination RON coverage, and the rolling target-RON window.

This is a feasibility witness, not published schedule timing. It intentionally reports `pending_bank_alignment`: 309 of 1,190 hub-touching legs currently fall in the approved cores. The next materializer must jointly retime those legs within the generated bank windows while preserving the proved route order, fleet limits, turns, curfews, and RONs. No canonical flight numbers or Line/Day/Route identifiers are assigned before that check passes.

## Bank-materialization lower bound

`bank_materialization_diagnostic.json` is defined by [`schemas/bank_materialization_diagnostic.schema.json`](../schemas/bank_materialization_diagnostic.schema.json). It corrects an important ambiguity in the first bank plan: the two directions of a daily market frequency are independently assigned to bank cores. A round-trip frequency guarantees service in both directions; it does not require both directions to use the same numbered bank or the same aircraft.

The diagnostic builds every curfew-safe bank-window option for all 1,190 hub-touching legs and solves a continuous aggregate time-flow relaxation. It enforces the 40-minute turn floor and reserves a RON-capable connection at all 99 required destinations. Because the same flight may use different five-minute points inside its window for different relaxed connections, the result is a lower bound: exceeding a configured fleet would prove infeasibility, while fitting does not yet prove an exact integer routing.

For the current proposal, the relaxed bank/turn/RON lower bound fits every configured fleet: MAX9 22/35, CRJ900 32/45, CRJ700 48/65, and CRJ200 67/80, or 169/225 in aggregate. This retracts the provisional target-time-only CRJ200 shortfall: §1.6a requires events to land inside a bank core, not at the generated +10/+50 targets. That result clears the lower-bound gate for the exact materialization stage below.

## Exact cycle materialization

`exact_materialization_plan.json` is defined by [`schemas/exact_materialization_plan.schema.json`](../schemas/exact_materialization_plan.schema.json). A time-expanded integer model chooses one five-minute departure time for every proposed leg. Aircraft inventory is conserved at every station, the 40-minute turn floor is enforced before an arrival becomes available again, every hub event remains inside an approved core, and fleet capacity comes directly from the schedule configuration.

The v5 exact plan schedules all 1,406 legs, including all 306 non-hub legs, in 221 of 225 configured aircraft: MAX9 34/35, CRJ900 44/45, CRJ700 65/65, and CRJ200 78/80. The model enforces the Section 2.6 hard floor and near-target threshold as it chooses times. Exception variables are created only when candidate-time capacity proves that a pairing with four or more departures mathematically requires the policy's one allowed short gap. The current plan has zero spacing violations and one permitted exception on PHF–SAV; its 35-minute gap remains above the 30-minute hard floor. The resulting successor cycles provide a real overnight at all 99 required destinations, with one deterministic same-station successor swap clearing the rolling target-RON cadence.

## Multi-hub qualification

`compute_multihub_assignments()` is a pure function. It accepts city metadata, an explicit intergroup-demand dataset, city market sizes, and versioned planning rules. It has no hardcoded filesystem paths, import-time data loading, pandas dependency, pickle input, or mutable global state.

The preserved legacy thresholds and city-percentile caps remain in [`config/policies/planning_rules_v1.json`](../config/policies/planning_rules_v1.json); [`planning_rules_v2.json`](../config/policies/planning_rules_v2.json) adds frequency and fleet policy, [`planning_rules_v3.json`](../config/policies/planning_rules_v3.json) adds bank-phase search, and [`planning_rules_v4.json`](../config/policies/planning_rules_v4.json) adds strict tier reconciliation, the documented BHM substitution groups, the Schedule 7 proposal ceiling, and exact-grid inter-hub placement. [`planning_rules_v5.json`](../config/policies/planning_rules_v5.json) adds the routing reserve, single-fleet markets, inter-hub spacing capacity, and exact Section 2.6 enforcement. The formerly embedded post-BHM-annotation table is normalized as [`data/reference/intergroup_demand_v2.json`](../data/reference/intergroup_demand_v2.json). The updated 105-city six-month airport matrix is stored as `data/reference/airport_od_matrix_consolidated_v2.csv`. Fingerprinted v1–v5 manifests preserve every input combination. The calculation covers every active city and reproduces all 100 non-hub qualifications in v2.2.5, including CHS at JAX/PHF/DAY and BTR at JAX.

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
  config/demand_data/bts_db1c_6mo_v3.json \
  demand_plan.json
```

Create the fresh frequency and fleet proposal with:

```bash
python -m caa_scheduler build-frequency-plan \
  canonical_schedule.json \
  demand_plan.json \
  config/demand_data/bts_db1c_6mo_v3.json \
  frequency_fleet_plan.json
```

Generate bank windows and place the proposed hub flying with:

```bash
python -m caa_scheduler build-bank-plan \
  canonical_schedule.json \
  frequency_fleet_plan.json \
  config/demand_data/bts_db1c_6mo_v3.json \
  hub_bank_plan.json
```

Construct aircraft cycles and evaluate fleet/RON feasibility with:

```bash
python -m caa_scheduler build-route-plan \
  canonical_schedule.json \
  frequency_fleet_plan.json \
  hub_bank_plan.json \
  config/demand_data/bts_db1c_6mo_v3.json \
  aircraft_route_plan.json
```

Build the deterministic topology repair with:

```bash
python -m caa_scheduler build-routing-repair \
  canonical_schedule.json \
  frequency_fleet_plan.json \
  hub_bank_plan.json \
  config/demand_data/bts_db1c_6mo_v3.json \
  routing_repair_plan.json
```

Prove the independent-direction bank-flow lower bound with:

```bash
python -m caa_scheduler diagnose-bank-materialization \
  canonical_schedule.json \
  frequency_fleet_plan.json \
  hub_bank_plan.json \
  config/demand_data/bts_db1c_6mo_v3.json \
  bank_materialization_diagnostic.json

python -m caa_scheduler build-exact-materialization \
  canonical_schedule.json \
  frequency_fleet_plan.json \
  hub_bank_plan.json \
  routing_repair_plan.json \
  config/demand_data/bts_db1c_6mo_v3.json \
  exact_materialization_plan.json
```

The golden-baseline and candidate commands generate these planning artifacts automatically. Candidate construction resolves the demand version to exactly one manifest and verifies every source fingerprint; an unknown version or mismatch blocks publishable output. If a candidate violates a hard stop such as a curfew, its canonical, timetable, and gate outputs remain suppressed. The demand/planning snapshots and diagnostic validation reports are retained so the failed build can be investigated.

## Next construction stages

Milestone 0.7.10 enforces Section 2.6 during exact timing, reserves the optional capacity needed to fit the accepted fleet, and repairs gate allocation so a rescued passenger touch cannot share its reserved slot. Canonicalization still rotates each successor cycle to a deterministic 03:00 operating-day boundary, numbers MAX9 lines A–Z and CRJ lines from AA, assigns fleet-blocked routes, preserves historical directed-market pairings where possible, assigns demand-ranked four-digit flight numbers, and records an exclusive generated-source provenance chain.

The current 1,406-leg proposal remains intentionally review-required. Curfews, minimum turns, numbering, bank alignment, structural validation, rolling target-city RON cadence, every tier service envelope, and pairing spacing pass. The remaining Milestone 0.7 work is now explicit:

1. add passenger-touch gate capacity to construction or a deterministic repair stage;
2. keep all long holds and overnights within configured hard-stand and combined capacity.

Golden comparisons remain required before blank-start construction or airport additions are enabled.
