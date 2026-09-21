# Schedule 7 v0.2.0 implementation plan

Schedule 7 v0.2.0 is an optimization review package. Its size is an output of
demand, network value, physical capacity, fleet availability, and operating
rules. The 1,406-leg v0.1.0 result is neither a target nor a hard ceiling. New
city-pairs are permitted when they have credible demand and remain feasible
through every downstream construction stage.

This work is isolated on `codex/schedule-7-v0.2.0-optimization`. Draft PR #22,
its branch, and the main branch are out of scope.

## Architecture and interaction order

| Order | Stage | Responsibility | Work level |
|---:|---|---|---|
| 1 | Build configuration and policy | Pin fixed inventory, demand, fleet, scoring, and solver behavior | Configuration and schema |
| 2 | Frequency and fleet allocation | Select markets and frequencies using demand, connectivity, diminishing returns, station capacity, and downstream cost | Solver-level selection |
| 3 | Bank placement | Fit selected hub events into capacity-aware bank windows | Solver-level timing envelope |
| 4 | Exact materialization | Choose five-minute flight times and continuous aircraft cycles while enforcing gate-touch throughput, curfews, turns, RONs, and fleet limits | Solver-level construction |
| 5 | Gate assignment | Keep RONs at gates when possible; split only the long holds needed to protect passenger touches | Bounded physical assignment |
| 6 | Operating validation | Reject passenger handling on stands and any gate/stand inventory overrun | Non-waivable hard stops |
| 7 | Productive-utilization search | Evaluate demand-supported missions in remaining idle windows without moving anchored work | Post-feasibility solver search |
| 8 | Canonicalization and export | Assign durable identifiers and produce the review package only after hard stops pass | Deterministic packaging |

The order is intentional. Towing can free a gate occupied by a long hold, but it
cannot make a passenger touch use a stand. If a passenger peak still exceeds
compatible gates after feasible towing, allocation or timing must change the
flight plan. Productive-utilization additions run after that plan is feasible so
they cannot be mistaken for automatic utilization targets.

## Incremental milestones

### A. Fixed physical inventory and conditional towing

- Treat configured gate and stand counts as authoritative.
- Never serialize a synthesized row beyond those counts.
- Fail construction when passenger touches cannot fit gates or towable long
  holds cannot fit the configured stands.
- Keep a RON continuously on its gate when all claims fit.
- Split a RON into arrival touch, stand middle, and departure touch only when
  that split prevents passenger handling on a stand.
- Minimize split count, then required stands, with deterministic tie-breaking.
- Regress CHS as a no-unnecessary-tow case and PHF 731/108/109, AUS
  328/503/504, and DAB 163/162/156 as review examples.

### B. Gate-aware flight selection and network balance

- Use station and hub passenger-gate throughput during frequency selection.
- Compare competing increments using local demand, connecting contribution,
  bank contribution, network coverage, routing cost, and downstream capacity.
- Apply diminishing value to repeated frequencies.
- Allow replacement or new hub markets where policy permits.
- Penalize marginal JAX, BHM, and MCI additions while rewarding feasible PHF,
  DAY, and SYR opportunities and useful NEC/MAC/LEC-to-FLP coverage.
- Preserve mandatory service and credible demand; do not equalize hubs by quota.

Station screening is a necessary early bound, not a substitute for exact timing.
An apparently valid daily total can still create an infeasible five-minute peak,
so exact materialization remains authoritative.

### C. Productive aircraft utilization

- Search idle windows before RON and during ROD for round trips or continuous
  missions that return before an anchored departure.
- Score demand and network value before utilization; idle time is allowed.
- Preserve curfews, turns, gate capacity, stands, required RON locations, fleet
  limits, bank commitments, and downstream routing continuity.
- Regress Route 731 at PHF and Route 538 at DAB as opportunity searches, not
  requirements to add a flight.

### D. Package and review

- Generate a complete Schedule 7 v0.2.0 candidate and all diagnostic artifacts.
- Confirm no PHOS, no physical-inventory synthesis, and no non-waivable hard
  stop.
- Run the full Python and JavaScript regression suites.
- Push the review package to the implementation branch and update its draft PR.
- Do not merge it to main.

## Resolved behavior decisions

- Total leg count is endogenous; 1,406 is not a cap.
- New city-pairs are allowed when selected by demand and network value.
- Idle time is preferable to marginal flying without sufficient value.
- Gate and stand counts cannot be expanded by construction or export.
- Tows are ground movements represented by split occupancy claims, not flight
  legs or changes to the aircraft's required RON station.

## Consequential ambiguity

No user decision currently blocks implementation. The gate engine models tow
timing through the existing 45-minute arrival and 60-minute departure passenger
touch windows; it does not model a separate tug-travel duration or tug fleet.
Adding tug-resource constraints would materially expand the problem and is not
part of v0.2.0 unless later requested.

## Recovery record

The workspace disconnected during the first implementation attempt. The
recovered state contains the allocation, bank, exact-materialization, gate, and
validation changes plus a complete 1,028-leg exact-seed checkpoint, but not a
publishable canonical package. Productive-utilization source and tests from the
lost workspace must be reconstructed. Every milestone above will be committed
and pushed separately under the disconnect-resilient workflow.
