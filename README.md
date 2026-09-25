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
    -> independent-direction full-bank-window lower bound
    -> exact five-minute aircraft cycles with all non-hub flying integrated
    -> canonical Line/Day/Route, pairing, and flight identifiers
    -> generated-source provenance + full structural/operating/gate validation
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
- `data/schedules/schedule_6_v2_2_5/bank_materialization_diagnostic.json`
- `data/schedules/schedule_6_v2_2_5/exact_materialization_plan.json`

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
python -m caa_scheduler diagnose-bank-materialization \
  data/schedules/schedule_6_v2_2_5/canonical_schedule.json \
  data/schedules/schedule_6_v2_2_5/frequency_fleet_plan.json \
  data/schedules/schedule_6_v2_2_5/hub_bank_plan.json \
  config/demand_data/bts_db1c_6mo_v3.json \
  bank_materialization_diagnostic.json
python -m caa_scheduler build-exact-materialization \
  data/schedules/schedule_6_v2_2_5/canonical_schedule.json \
  data/schedules/schedule_6_v2_2_5/frequency_fleet_plan.json \
  data/schedules/schedule_6_v2_2_5/hub_bank_plan.json \
  data/schedules/schedule_6_v2_2_5/routing_repair_plan.json \
  config/demand_data/bts_db1c_6mo_v3.json \
  exact_materialization_plan.json
```

`baseline` verifies reproducibility and therefore succeeds when structural/planning validation, demand-plan parity, topology repair, and both golden exports match. `validate-operating` is the enforcement command: it exits nonzero while unoverridden hard findings remain.

## Compile a candidate schedule

For long or approval-gated builds, use the resumable phases in
[`docs/staged_regeneration.md`](docs/staged_regeneration.md) instead of one
uninterrupted candidate command.

Export an approved configuration from **Schedule Setup**, add it to a working branch, and run:

```bash
python -m caa_scheduler build-candidate path/to/build_config.json
```

The accepted Schedule 7 v1.0.0 configuration is pinned at `config/candidates/schedule_7_v1_0_0.json` with fleet counts MAX9 35, CRJ900 45, CRJ700 65, and CRJ200 80.

For a previous-schedule start, the compiler resolves the pinned canonical baseline from `data/schedules/<scheduleId>/canonical_schedule.json`. It writes an isolated package under `builds/<buildId>/` containing a copy of the approved input, validation reports, demand plan, fresh frequency/fleet proposal, generated hub-bank plan, the first-pass aircraft-route diagnostic, topology repair, bank-materialization lower bound, exact-cycle plan, and canonicalization report. A passing exact plan receives canonical identifiers and an exclusive generated-source provenance chain before full validation is rerun. Reviewable canonical, timetable, and gate outputs are written unless structural validation or a non-waivable hard stop blocks them. The manually dispatched **Build candidate schedule** GitHub Action runs the same command and retains the package as an artifact for 30 days.

If Python preflight fails, blank-start planning is requested, or an airport addition lacks the future planning stage, no candidate is emitted. If any non-waivable hard-stop check fails—including curfew enforcement—the diagnostic reports are written but the canonical, timetable, and gate outputs are suppressed. Other operating findings produce a review-required candidate rather than being silently waived.

## Current boundary

Milestone 0.7.10 adds construction-time Section 2.6 pairing spacing to the strict, auditable planning, demand, bank, topology-repair, exact-materialization, and canonicalization pipeline. Python reconstructs the historical plan, processes the complete pinned 105-city demand data, reproduces all 100 non-hub qualifications, and applies the current percentile-tier service caps before frequency allocation. Aircraft quantities still come only from each schedule's build configuration; no fleet count is inferred from policy or silently added by repair.

The exact optimizer's numerical stack is pinned in `pyproject.toml`. SciPy/HiGHS releases can materially change bounded mixed-integer solve behavior, so changing the SciPy or NumPy versions is an explicit engine change that must regenerate and revalidate the golden artifacts.

The v5 planning pin retains the v4 network boundary: it removes 131 historical hub/focus markets outside the effective tier assignments, preserves historical point-to-point markets, and retains BHM in one allowed slot for 20 cities in the documented FLP, GCP, OZK, and TEX groups. It also gives inter-hub markets a three-round-trip ceiling, keeps each market on one fleet, proves inter-hub spacing capacity during bank-phase selection, and enforces pairing spacing inside the exact optimizer. The accepted 1,430-leg ceiling remains unchanged, but 12 lowest-priority optional round trips are reserved from allocation because filling the ceiling cannot satisfy both the selected fleet counts and higher-priority spacing rules. Mandatory and tier service remain intact at 1,406 legs.

`exact_materialization_plan.json` selects one five-minute time for all 1,406 legs, aligns all 1,100 hub-touching legs, integrates all 306 non-hub legs, and produces real aircraft cycles using 221/225 aircraft. The selected fleet use is MAX9 34/35, CRJ900 44/45, CRJ700 65/65, and CRJ200 78/80. Canonicalization turns those cycles into 40 lines, 221 operating-day routes, and 470 directed pairings while preserving all 1,160 bank touches and replacing legacy workbook provenance with generated-source fingerprints.

Full validation now passes structure, curfews, minimum turns, numbering, bank alignment, rolling target-city RON cadence, every percentile-tier service envelope, and Section 2.6 pairing spacing. The former 236 spacing findings are eliminated; PHF–SAV uses the policy's single allowed short-gap exception and every gap remains above the 30-minute hard floor. A gate allocator defect that could reuse a reserved touch slot is also fixed, eliminating all 26 reported physical double-bookings. The proposal remains review-required for genuine gate/stand construction work at 17 stations: 260 passenger touches use stands, seven cities exceed configured stand capacity, and five exceed combined peak capacity. These findings do not authorize extra aircraft, gates, stands, or curfew waivers.

## Repository visibility

GitHub Free supports private repositories, but GitHub Pages requires a public repository on that plan. This repository is therefore intended to be public. Credentials, access tokens, and private operating data must never be committed. If future inputs need to remain private, the architecture should split them into a private engine/data repository and publish only sanitized web assets to the public Pages repository.
