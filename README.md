# CAA Scheduler

CAA Scheduler is the migration target for Coastal American Airways schedule construction. It moves the durable schedule state and deterministic processing out of an LLM conversation and into version-controlled code and data.

## Milestone 0.3

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

Run the regression tests with:

```bash
python -m unittest discover -s tests -v
```

Either consumer file can also be rebuilt directly from canonical JSON:

```bash
python -m caa_scheduler export-timetable \
  data/schedules/schedule_6_v2_2_5/canonical_schedule.json timetable.json
python -m caa_scheduler export-gates \
  data/schedules/schedule_6_v2_2_5/canonical_schedule.json gates.json
python -m caa_scheduler validate-operating \
  data/schedules/schedule_6_v2_2_5/canonical_schedule.json \
  --output operating_validation_report.json
```

`baseline` verifies reproducibility and therefore succeeds when structural validation and both golden exports match. `validate-operating` is the enforcement command: it exits nonzero while unoverridden hard findings remain.

## Current boundary

Milestone 0.3 expresses the current operating policy as pinned JSON and evaluates schedule-specific fleet counts, hard-stop curfews, routing/RON continuity, turn times, §2.6, frequency, point-to-point share, numbering, and gate/stand constraints. It also implements runway, percentile-tier, and bank checks that report `not_evaluated` until their missing inputs are present. See [Operating-rule validation](docs/operating_validation.md).

The v2.2.5 golden schedule is intentionally **not** declared operating-rule clean. Exact historical preservation and current-policy compliance are separate questions. The report captures the known baseline findings without silently waiving them; the next read-only web-console milestone will make those findings navigable.

## Repository visibility

GitHub Free supports private repositories, but GitHub Pages requires a public repository on that plan. This repository is therefore intended to be public. Credentials, access tokens, and private operating data must never be committed. If future inputs need to remain private, the architecture should split them into a private engine/data repository and publish only sanitized web assets to the public Pages repository.
