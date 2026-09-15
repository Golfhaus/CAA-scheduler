# Candidate compiler

Milestone 0.6 establishes the boundary between browser-based Schedule Setup and deterministic Python processing.

## Command

```bash
python -m caa_scheduler build-candidate path/to/build_config.json
```

The compiler resolves a `previous_schedule` starting point from `data/schedules/<scheduleId>/canonical_schedule.json`. `--baseline` can select an explicit canonical file for testing, and `--output` can override the default `builds/<buildId>` directory.

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
11. Run structural and operating validation against the timed seed candidate.
12. Stop consumer export if a hard-stop or planning-input check fails.
13. Otherwise write the canonical candidate, timetable, and gates. Planning and diagnostic reports are retained in either case.

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

The current fresh planning proposal produces `blocked_planning_input`. The first-pass route artifact retains the 409-aircraft/184-aircraft-short diagnostic, while the repair artifact proves that all 1,430 legs fit in 209 of the 225 selected aircraft with zero curfew or RON failures. The bank-flow diagnostic removes the accidental same-bank direction pairing and uses the full 60-minute cores required by §1.6a. Its relaxed bank/turn/RON lower bound fits every configured fleet at 169 whole-aircraft equivalents in aggregate. The remaining work is non-hub integration and exact whole-flight cycle materialization—not a larger or rebalanced schedule fleet.

## GitHub Actions

The **Build candidate schedule** workflow accepts a repository path to an approved configuration and uploads the isolated package as a 30-day artifact. It uses read-only repository permissions and does not commit or publish a candidate automatically.

## Deliberate boundary

This compiler still evaluates a seed candidate. It now emits a fresh demand-derived frequency/fleet proposal, a complete timed bank plan, the preserved first-pass aircraft-cycle diagnostic, a passing fleet/curfew/RON topology repair, and a mathematical full-window materialization lower bound. It does not substitute proposed legs into canonical JSON until non-hub integration, route order, and exact bank timing are materialized together. Blank starts and airport additions remain explicit blockers until that stage is deterministic.
