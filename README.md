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
    -> pinned six-month airport O-D demand plan
    -> exact 100/100 multi-hub assignment reproduction
    -> fresh frequency + fleet proposal within schedule-specific aircraft-minutes
    -> curfew-safe bank placement for all proposed hub flying
    -> complete aircraft-cycle and RON feasibility report
    -> deterministic curfew-safe topology repair inside the selected fleet
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
- `data/schedules/schedule_6_v2_2_5/demand_plan.json`
- `data/schedules/schedule_6_v2_2_5/frequency_fleet_plan.json`
- `data/schedules/schedule_6_v2_2_5/hub_bank_plan.json`
- `data/schedules/schedule_6_v2_2_5/aircraft_route_plan.json`
- `data/schedules/schedule_6_v2_2_5/routing_repair_plan.json`

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
  --demand-version bts-db1c-6mo-jul2025-apr2026-v3
python -m caa_scheduler build-demand-plan \
  data/schedules/schedule_6_v2_2_5/canonical_schedule.json \
  config/demand_data/bts_db1c_6mo_v3.json \
  demand_plan.json
python -m caa_scheduler build-frequency-plan \
  data/schedules/schedule_6_v2_2_5/canonical_schedule.json \
  data/schedules/schedule_6_v2_2_5/demand_plan.json \
  config/demand_data/bts_db1c_6mo_v3.json \
  frequency_fleet_plan.json
python -m caa_scheduler build-bank-plan \
  data/schedules/schedule_6_v2_2_5/canonical_schedule.json \
  data/schedules/schedule_6_v2_2_5/frequency_fleet_plan.json \
  config/demand_data/bts_db1c_6mo_v3.json \
  hub_bank_plan.json
python -m caa_scheduler build-route-plan \
  data/schedules/schedule_6_v2_2_5/canonical_schedule.json \
  data/schedules/schedule_6_v2_2_5/frequency_fleet_plan.json \
  data/schedules/schedule_6_v2_2_5/hub_bank_plan.json \
  config/demand_data/bts_db1c_6mo_v3.json \
  aircraft_route_plan.json
python -m caa_scheduler build-routing-repair \
  data/schedules/schedule_6_v2_2_5/canonical_schedule.json \
  data/schedules/schedule_6_v2_2_5/frequency_fleet_plan.json \
  data/schedules/schedule_6_v2_2_5/hub_bank_plan.json \
  config/demand_data/bts_db1c_6mo_v3.json \
  routing_repair_plan.json
```

`baseline` verifies reproducibility and therefore succeeds when structural/planning validation, demand-plan parity, topology repair, and both golden exports match. `validate-operating` is the enforcement command: it exits nonzero while unoverridden hard findings remain.

## Compile a candidate schedule

Export an approved configuration from **Schedule Setup**, add it to a working branch, and run:

```bash
python -m caa_scheduler build-candidate path/to/build_config.json
```

For a previous-schedule start, the compiler resolves the pinned canonical baseline from `data/schedules/<scheduleId>/canonical_schedule.json`. It writes an isolated package under `builds/<buildId>/` containing a copy of the approved input, validation reports, demand plan, fresh frequency/fleet proposal, generated hub-bank plan, the first-pass aircraft-route diagnostic, and the topology repair plan. Canonical, timetable, and gate outputs are added only after every construction gate passes. The manually dispatched **Build candidate schedule** GitHub Action runs the same command and retains the package as an artifact for 30 days.

If Python preflight fails, blank-start planning is requested, or an airport addition lacks the future planning stage, no candidate is emitted. If any non-waivable hard-stop check fails—including curfew enforcement—the diagnostic reports are written but the canonical, timetable, and gate outputs are suppressed. Other operating findings produce a review-required candidate rather than being silently waived.

## Current boundary

Milestone 0.7.5 now has a deterministic planning, demand, bank, aircraft-cycle, and topology-repair boundary. Python reconstructs the historical plan, processes the complete pinned 105-city demand data, reproduces all 100 non-hub assignments, generates a fresh frequency/fleet proposal, defines all 24 hub banks, and preserves the original independent-placement diagnostic. A separate repair search then retains all 1,430 legs in continuous fleet-homogeneous route days using 209 of the 225 aircraft selected for this schedule. It produces zero curfew violations, covers every non-exempt destination with a RON endpoint, and passes the rolling target-RON window. Aircraft quantities still come only from each schedule's build configuration; no fleet count is inferred from policy or added by repair.

The first routing pass remains an intentional diagnostic: its independent bank placements imply 409 aircraft against the selected 225 and one target-RON cadence failure. `routing_repair_plan.json` now proves that the topology itself fits with 16 aircraft remaining, without dropping service or relaxing a curfew. It is not yet canonical timing: only 309 of 1,190 hub-touching feasibility legs happen to sit in the approved bank cores. Candidate publication therefore remains blocked while the next construction step jointly materializes the repaired route order and bank timing, then assigns canonical Line/Day/Route, pairing, and flight identifiers. Blank starts and airport additions remain blocked until that materialization is complete.

## Repository visibility

GitHub Free supports private repositories, but GitHub Pages requires a public repository on that plan. This repository is therefore intended to be public. Credentials, access tokens, and private operating data must never be committed. If future inputs need to remain private, the architecture should split them into a private engine/data repository and publish only sanitized web assets to the public Pages repository.
