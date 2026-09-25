# Staged schedule regeneration

Long candidate builds must be run as approval-gated, resumable phases. Complete
one phase, inspect its durable artifacts, report the result, and wait for an
explicit `proceed` before starting the next phase.

Use a separate directory for each phase so a failed or disconnected command
cannot remove the last reviewable package.

## Phase 1: prepare deterministic inputs

This phase runs demand, frequency, bank, route, and routing-repair construction.
It never invokes the exact MILP solver.

```bash
PYTHONPATH=src python -m caa_scheduler build-candidate \
  builds/schedule_7_v0_2_0/build_config.json \
  --output builds/schedule_7_v0_2_0/stages/pre_exact \
  --stop-after-pre-exact
```

Completion requires `regeneration_progress.json` to report phase `pre_exact`
and status `complete`. Preserve `candidate_seed.json`,
`frequency_fleet_plan.json`, `hub_bank_plan.json`, and
`routing_repair_plan.json` together.

## Phase 2: populate exact fleet seeds

If no compatible completed checkpoint exists, run one fleet per invocation.
Each successful invocation updates the same checkpoint and exits normally.

```bash
PYTHONPATH=src python -m caa_scheduler build-exact-materialization \
  builds/schedule_7_v0_2_0/stages/pre_exact/candidate_seed.json \
  builds/schedule_7_v0_2_0/stages/pre_exact/frequency_fleet_plan.json \
  builds/schedule_7_v0_2_0/stages/pre_exact/hub_bank_plan.json \
  builds/schedule_7_v0_2_0/stages/pre_exact/routing_repair_plan.json \
  config/demand_data/bts_db1c_6mo_v7.json \
  builds/schedule_7_v0_2_0/stages/exact/exact_materialization_plan.json \
  --seed-checkpoint builds/schedule_7_v0_2_0/stages/exact/exact_seed_checkpoint.json \
  --seed-fleets-per-run 1 \
  --progress
```

Repeat only after reviewing the checkpoint's `completedFleets`. A compatible
checkpoint may be supplied directly instead. Compatibility is determined by
the fingerprint embedded in the checkpoint, not by its filename or by a broad
demand-manifest hash.

## Phase 3: exact global repair and post-solve optimization

Omit `--seed-fleets-per-run` after all fleet seeds exist. This is the only
potentially expensive MILP phase. It is bounded and must end with either a
written exact plan or an explicit blocked result.

```bash
PYTHONPATH=src python -m caa_scheduler build-exact-materialization \
  builds/schedule_7_v0_2_0/stages/pre_exact/candidate_seed.json \
  builds/schedule_7_v0_2_0/stages/pre_exact/frequency_fleet_plan.json \
  builds/schedule_7_v0_2_0/stages/pre_exact/hub_bank_plan.json \
  builds/schedule_7_v0_2_0/stages/pre_exact/routing_repair_plan.json \
  config/demand_data/bts_db1c_6mo_v7.json \
  builds/schedule_7_v0_2_0/stages/exact/exact_materialization_plan.json \
  --seed-checkpoint builds/schedule_7_v0_2_0/stages/exact/exact_seed_checkpoint.json \
  --progress \
  --provisional-preview
```

Post-solve-only policy changes, including line rebalancing, are excluded from
the seed fingerprint. They therefore reuse compatible exact timing rather than
re-solving the network.

When a prior exact plan contains exactly the current solver-leg inventory and
the RON assignments are unchanged, refresh only the post-solve policy instead
of reconstructing the global model:

```bash
PYTHONPATH=src python -m caa_scheduler build-exact-materialization \
  builds/schedule_7_v0_2_0/stages/pre_exact/candidate_seed.json \
  builds/schedule_7_v0_2_0/stages/pre_exact/frequency_fleet_plan.json \
  builds/schedule_7_v0_2_0/stages/pre_exact/hub_bank_plan.json \
  builds/schedule_7_v0_2_0/stages/pre_exact/routing_repair_plan.json \
  config/demand_data/bts_db1c_6mo_v7.json \
  builds/schedule_7_v0_2_0/stages/exact/exact_materialization_plan.json \
  --reuse-exact-plan builds/schedule_7_v0_2_0/exact_materialization_plan.json \
  --provisional-preview
```

This mode rejects any missing, extra, or structurally changed solver leg. It
does not invoke a fleet or global MILP. It reapplies configured line transfers
and bridges, then reruns continuity, turn, curfew, RON, fleet, spacing, and
fixed-inventory validation.

## Phase 4: finalize and validate

Finalization accepts the separately reviewed exact plan and refuses it if the
schedule ID, planning-rules ID, or selected-leg count differs from the freshly
prepared inputs.

```bash
PYTHONPATH=src python -m caa_scheduler build-candidate \
  builds/schedule_7_v0_2_0/build_config.json \
  --output builds/schedule_7_v0_2_0/stages/final \
  --exact-plan builds/schedule_7_v0_2_0/stages/exact/exact_materialization_plan.json \
  --provisional-preview
```

Run focused tests after a targeted implementation change. Run the complete
Python and web regression suites only after finalization, before packaging the
review preview.

## Phase 5: build the private preview

Copy only the reviewed final package into the preview manifest, build
`dist-preview`, and start the private preview server. A provisional package
remains non-publishable while any hard stop is present.

## Completion report

After every phase, report:

- input commit and checkpoint fingerprint;
- completed phase and elapsed time;
- artifacts written and their validation status;
- leg, aircraft, gate-failure, and tow counts when available;
- blockers or changed findings;
- the exact next command, which is not run until approval.
