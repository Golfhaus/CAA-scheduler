# Candidate compiler

Milestone 0.6 establishes the boundary between browser-based Schedule Setup and deterministic Python processing.

## Command

```bash
python -m caa_scheduler build-candidate path/to/build_config.json
```

The compiler resolves a `previous_schedule` starting point from `data/schedules/<scheduleId>/canonical_schedule.json`. `--baseline` can select an explicit canonical file for testing, and `--output` can override the default `builds/<buildId>` directory.

The accepted Schedule 7 v0.1.0 configuration is stored at `config/candidates/schedule_7_v0_1_0.json`. Its schedule-specific fleet selection is MAX9 35, CRJ900 45, CRJ700 65, and CRJ200 80.

Each run replaces only the compiler's known files in that output directory. This prevents a newly blocked build from leaving an older canonical/timetable/gate candidate behind and making it look publishable.

## Processing order

1. Load `build_config.json` and its selected canonical baseline.
2. Repeat server-side preflight, including exact city/policy fingerprint comparison.
3. Deep-copy the baseline so the frozen source cannot be mutated.
4. Apply the new schedule identity, fleet counts, connection window, and supported network changes.
5. Reconstruct and validate the candidate's durable planning snapshot.
6. Resolve the exact demand-data version to one manifest, verify all source fingerprints, and recompute the demand/hub plan.
7. Allocate a fresh frequency and fleet proposal against the schedule-specific aircraft counts.
8. Generate hub-bank windows and place all proposed hub-touching flying without accepting a curfew violation.
9. Construct complete aircraft cycles, insert non-hub flying, and evaluate fleet, continuity, turn, curfew, and RON feasibility.
10. Independently assign directional frequencies to bank cores and solve a continuous time-flow lower bound with hard curfews and destination RONs.
11. Select exact five-minute times, integrate non-hub flying, construct integer aircraft cycles, and verify hard curfews and RON cadence.
12. Run structural and operating validation against the timed seed candidate.
13. Stop consumer export if a hard-stop or planning-input check fails.
14. Assign canonical lines, 03:00 operating days, fleet-blocked routes, pairings, and demand-ranked flight numbers from a passing exact plan.
15. Replace workbook provenance with a fingerprinted deterministic-construction chain and rerun full structural and operating validation.
16. Write the reviewable canonical candidate, canonicalization report, timetable, and gates unless structural validation or a non-waivable hard stop blocks them. Planning and diagnostic reports are retained in either case.

Fleet counts have no engine default. The compiler copies `fleetCounts` directly from the build configuration, and the operating validator measures aircraft-day use against those values.

Curfew enforcement comes from the pinned operating policy. The departure-window check is marked `hardStop`; it cannot be waived. A curfew failure leaves the demand/planning snapshots plus diagnostic validation and build reports but suppresses `canonical_schedule.json`, `timetable.json`, and `gates.json`.

## Candidate states

| State | Meaning | Consumer outputs |
|---|---|---|
| `blocked_preflight` | Required or pinned setup data is invalid | No |
| `blocked_planning_input` | A blank start, airport addition, or policy-changing hub/focus edit needs a later planning stage | No |
| `blocked_hard_stop` | A non-waivable operating rule failed | No |
| `candidate_review_required` | Hard stops passed, but other structural/operating findings need repair | Yes |
| `candidate_ready` | All evaluated structural and error-level operating checks passed | Yes |

The current fresh planning proposal advances through canonicalization as `candidate_review_required`. The first-pass route artifact retains the 409-aircraft/184-aircraft-short diagnostic. The bank-flow relaxation fits at 169/225, and exact materialization schedules all 1,430 legs—including 240 non-hub legs—in 208/225 aircraft. Canonicalization produces 23 lines, 208 routes, 736 directed pairings, flights 1001–2430, and all 1,224 bank-touch assignments. Curfews, minimum turns, numbering, bank alignment, and structural validation pass.

Full validation now identifies the next construction work rather than masking it: 222 same-pairing spacing findings, 45 percentile-tier hub-count findings caused by preserved historical extra-hub markets, and gate/stand findings at 13 stations, including 419 passenger touches assigned to stands. These are review failures, not permission to expand the fleet or waive curfews.

If a bounded exact solve does not return a feasible incumbent, the candidate build still writes `exact_materialization_plan.json` with `materializationStatus: blocked`, the solver failure in `diagnostics.solverFailure`, and `nextStep.action: retry_exact_materialization`. A missing artifact is never used to represent solver exhaustion. Blocked exact output cannot advance to canonical identifiers or publication.

## GitHub Actions

The **Build candidate schedule** workflow accepts a repository path to an approved configuration and uploads the isolated package as a 30-day artifact. It uses read-only repository permissions and does not commit or publish a candidate automatically.

## Deliberate boundary

This compiler still evaluates a seed candidate. It now emits a fresh demand-derived frequency/fleet proposal, bank plan, preserved first-pass diagnostic, topology repair, mathematical lower bound, passing exact-cycle plan, canonicalization report, and fully validated review candidate. Blank starts and airport additions remain explicit blockers until the newly exposed spacing, tier-cap, and gate/stand repair path is deterministic.
