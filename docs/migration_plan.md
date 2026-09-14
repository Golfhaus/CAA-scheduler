# Migration milestones

## 0.1 — Golden schedule foundation

Status: complete.

- Import Schedule 6 v2.2.5 from the `Routings` worksheet.
- Pin the corresponding city-information snapshot.
- Generate canonical schedule JSON.
- Run structural validation.
- Reproduce the existing timetable JSON byte for byte.
- Run the complete pipeline in GitHub Actions.

## 0.2 — Gate-engine consolidation

Status: complete.

- Move `build_claims`, cyclical overlap handling, waypoint splitting, and gate assignment into one module.
- Remove the duplicated implementations in the current chart and JSON scripts.
- Export gate JSON from the canonical schedule.
- Compare Schedule 6 v2.2.5 to the frozen gate JSON by city, claim, placement, and peak use.

## 0.3 — Operating-rule validator

Status: complete.

- Add per-schedule fleet-plan and aircraft-day checks.
- Add curfews and allowed operating windows.
- Add turn-duration and routing/RON rules.
- Implement the current two-part Section 2.6 policy without the obsolete hub multiplier.
- Add hub-bank, frequency-ceiling, point-to-point, runway, gate, and stand checks.
- Separate errors from explicit, versioned overrides.

## 0.4 — Read-only web console

Status: complete.

- Load a canonical schedule in GitHub Pages.
- Show overview, routings, validation, timetable, and gate-utilization views.
- Link every validation failure to the affected flights or station.

## 0.5 — Schedule setup and preflight

Status: complete.

- Create a portable, schema-backed `build_config.json` in the web console.
- Store fleet types and counts explicitly for every schedule.
- Pin the baseline, instructions, city data, operating policy, and demand snapshot.
- Capture Mainline/Skunkworks mode, connection limits, network changes, and notes.
- Persist drafts in the browser and support normalized JSON import/export.

## 0.6 — Candidate compiler

Status: complete.

- Revalidate `build_config.json` in Python before any schedule work.
- Seed a candidate only from its explicitly selected canonical schedule.
- Apply schedule identity, schedule-specific fleet counts, connection limits, destination removals, and compatible status changes without mutating the baseline.
- Rerun structural and operating validators and package candidate outputs.
- Suppress canonical/timetable/gate outputs when a non-waivable hard stop fails.
- Run the same compiler through a manually dispatched GitHub Action.

## 0.7 — Deterministic construction planner

- Replace hardcoded paths, pickle files, import-time data loading, and mutable module globals.
- Reconnect demand, multi-hub assignment, fleet allocation, bank placement, routing, and repair logic behind one callable build command.
- Add golden tests before changing optimization behavior.

## 1.0 — Schedule Builder

- Add reviewable network, fleet-allocation, bank, and routing planning tables to the Schedule 7 setup workflow.
- Launch builds through GitHub Actions.
- Store working drafts outside the permanent main branch.
- Publish an immutable version through an explicit Finalize action.
- Add a thin authenticated service only when the Pages app needs secure workflow triggering or draft/job state.
