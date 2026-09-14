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
5. Run structural and operating validation.
6. Stop consumer export if a hard-stop check fails.
7. Otherwise write the canonical candidate, timetable, gates, and both validation reports.

Fleet counts have no engine default. The compiler copies `fleetCounts` directly from the build configuration, and the operating validator measures aircraft-day use against those values.

Curfew enforcement comes from the pinned operating policy. The departure-window check is marked `hardStop`; it cannot be waived. A curfew failure leaves diagnostic validation and build reports but suppresses `canonical_schedule.json`, `timetable.json`, and `gates.json`.

## Candidate states

| State | Meaning | Consumer outputs |
|---|---|---|
| `blocked_preflight` | Required or pinned setup data is invalid | No |
| `blocked_planning_input` | A blank start, airport addition, or policy-changing hub/focus edit needs a later planning stage | No |
| `blocked_hard_stop` | A non-waivable operating rule failed | No |
| `candidate_review_required` | Hard stops passed, but other structural/operating findings need repair | Yes |
| `candidate_ready` | All evaluated structural and error-level operating checks passed | Yes |

The Schedule 6 v2.2.5 seed currently produces `candidate_review_required`, because historical fidelity and current-policy compliance remain separate. This is expected and preserves every known finding for repair rather than silently overriding it.

## GitHub Actions

The **Build candidate schedule** workflow accepts a repository path to an approved configuration and uploads the isolated package as a 30-day artifact. It uses read-only repository permissions and does not commit or publish a candidate automatically.

## Deliberate boundary

This milestone compiles and evaluates a seed candidate. It does not claim that copying a prior routing is new schedule construction. Milestone 0.7 will reconnect demand allocation, multi-hub qualification, fleet assignment, bank placement, aircraft routing, and repair logic behind this same contract. Blank starts and airport additions remain explicit blockers until those inputs can be materialized deterministically.
