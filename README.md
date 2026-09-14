# CAA Scheduler

CAA Scheduler is the migration target for Coastal American Airways schedule construction. It moves the durable schedule state and deterministic processing out of an LLM conversation and into version-controlled code and data.

## Milestone 0.7 — planning foundation

The migration baseline now proves this pipeline:

```text
v2.2.5 workbook + pinned city data
    -> canonical schedule JSON
    -> validation report
    -> timetable JSON
    -> exact comparison with the published v2.2.5 timetable data
    -> gate assignment JSON
    -> exact comparison with the published v2.2.5 gate data
    -> operating-rule validation with evidence and explicit overrides
    -> build-instruction catalog generated from editable Markdown
    -> GitHub Pages operating console
    -> schedule-specific setup + deterministic preflight
    -> portable build_config.json
    -> Python candidate compiler + repeated preflight
    -> structural and operating reports
    -> durable planning snapshot + planning validation
    -> timetable/gate candidate exports only after hard stops pass
```

The workbook remains a source for this one-time migration and will later become an export. The canonical JSON is the authoritative schedule representation going forward.

## Run the baseline build

From the repository root:

```bash
python -m caa_scheduler baseline \
  --config config/baselines/schedule_6_v2_2_5.json
```

This writes:

- `data/schedules/schedule_6_v2_2_5/canonical_schedule.json`
- `data/schedules/schedule_6_v2_2_5/timetable.json`
- `data/schedules/schedule_6_v2_2_5/gates.json`
- `data/schedules/schedule_6_v2_2_5/validation_report.json`
- `data/schedules/schedule_6_v2_2_5/operating_validation_report.json`
- `data/schedules/schedule_6_v2_2_5/planning_snapshot.json`
- `data/schedules/schedule_6_v2_2_5/planning_validation_report.json`

Run the regression tests with:

```bash
python -m unittest discover -s tests -v
node --test tests/*.mjs
```

## Build the web console

```bash
python -m caa_scheduler build-web --output dist
python -m http.server --directory dist 8000
```

The site loads the pinned canonical schedule and its generated reports directly. Its schedule manifest makes additional versions additive rather than requiring UI code changes. GitHub Actions publishes the console to [Golfhaus.github.io/CAA-scheduler](https://golfhaus.github.io/CAA-scheduler/).

Either consumer file can also be rebuilt directly from canonical JSON:

```bash
python -m caa_scheduler export-timetable \
  data/schedules/schedule_6_v2_2_5/canonical_schedule.json timetable.json
python -m caa_scheduler export-gates \
  data/schedules/schedule_6_v2_2_5/canonical_schedule.json gates.json
python -m caa_scheduler validate-operating \
  data/schedules/schedule_6_v2_2_5/canonical_schedule.json \
  --output operating_validation_report.json
python -m caa_scheduler reconstruct-plan \
  data/schedules/schedule_6_v2_2_5/canonical_schedule.json \
  planning_snapshot.json \
  --validation-output planning_validation_report.json \
  --demand-version unavailable-in-migration-baseline
```

`baseline` verifies reproducibility and therefore succeeds when structural validation and both golden exports match. `validate-operating` is the enforcement command: it exits nonzero while unoverridden hard findings remain.

## Compile a candidate schedule

Export an approved configuration from **Schedule Setup**, add it to a working branch, and run:

```bash
python -m caa_scheduler build-candidate path/to/build_config.json
```

For a previous-schedule start, the compiler resolves the pinned canonical baseline from `data/schedules/<scheduleId>/canonical_schedule.json`. It writes an isolated package under `builds/<buildId>/` containing a copy of the approved input, build report, structural/operating/planning validation reports, the planning snapshot, canonical candidate, timetable, and gate data. The manually dispatched **Build candidate schedule** GitHub Action runs the same command and retains the package as an artifact for 30 days.

If Python preflight fails, blank-start planning is requested, or an airport addition lacks the future planning stage, no candidate is emitted. If any non-waivable hard-stop check fails—including curfew enforcement—the diagnostic reports are written but the canonical, timetable, and gate outputs are suppressed. Other operating findings produce a review-required candidate rather than being silently waived.

## Current boundary

Milestone 0.7 has begun with a deterministic planning boundary. Python now reconstructs the final directional market/fleet plan, station totals, preserved hub assignments, hub-bank requirements, and an aircraft-minute lower bound directly from canonical JSON. This replaces the missing `fleet_routes.pkl` and stale standalone station totals for migration purposes. Fleet capacity still comes only from the schedule-specific build configuration, and curfews remain non-waivable hard stops. The Planning tab exposes this snapshot in the Pages console. See [Planning engine](docs/planning_engine.md), [Candidate compiler](docs/candidate_engine.md), [Web console](docs/web_console.md), and [`planning_snapshot` schema](schemas/planning_snapshot.schema.json).

This remains a seed-and-validate compiler, not yet the full demand-to-routing optimizer. The v2.2.5 market plan is explicitly marked as a canonical reconstruction: its scheduled frequencies are not mislabeled as raw demand allocation. Blank starts, airport additions, fresh demand allocation, bank placement, route construction, and automated repair remain blocked until those deterministic stages and their pinned inputs are reconnected. The v2.2.5 golden schedule is intentionally **not** declared operating-rule clean. Exact historical preservation and current-policy compliance remain separate questions.

## Repository visibility

GitHub Free supports private repositories, but GitHub Pages requires a public repository on that plan. This repository is therefore intended to be public. Credentials, access tokens, and private operating data must never be committed. If future inputs need to remain private, the architecture should split them into a private engine/data repository and publish only sanitized web assets to the public Pages repository.
