# Migration milestones

## 0.1 — Golden schedule foundation

- Import Schedule 6 v2.2.5 from the `Routings` worksheet.
- Pin the corresponding city-information snapshot.
- Generate canonical schedule JSON.
- Run structural validation.
- Reproduce the existing timetable JSON byte for byte.
- Run the complete pipeline in GitHub Actions.

## 0.2 — Gate-engine consolidation

- Move `build_claims`, cyclical overlap handling, waypoint splitting, and gate assignment into one module.
- Remove the duplicated implementations in the current chart and JSON scripts.
- Export gate JSON from the canonical schedule.
- Compare Schedule 6 v2.2.5 to the frozen gate JSON by city, claim, placement, and peak use.

## 0.3 — Operating-rule validator

- Add fleet capacity and aircraft-day checks.
- Add curfews and allowed operating windows.
- Add turn-duration and routing/RON rules.
- Implement the current two-part Section 2.6 policy without the obsolete hub multiplier.
- Add hub-bank, frequency-ceiling, point-to-point, runway, gate, and stand checks.
- Separate errors from explicit, versioned overrides.

## 0.4 — Read-only web console

- Load a canonical schedule in GitHub Pages.
- Show overview, routings, validation, timetable, and gate-utilization views.
- Link every validation failure to the affected flights or station.

## 0.5 — Deterministic construction engine

- Replace hardcoded paths, pickle files, import-time data loading, and mutable module globals.
- Express build inputs in a pinned configuration file.
- Reconnect demand, multi-hub assignment, fleet allocation, bank placement, routing, and repair logic behind one callable build command.
- Add golden tests before changing optimization behavior.

## 1.0 — Schedule Builder

- Add the Schedule 7 kickoff wizard and reviewable planning tables.
- Launch builds through GitHub Actions.
- Store working drafts outside the permanent main branch.
- Publish an immutable version through an explicit Finalize action.
- Add a thin authenticated service only when the Pages app needs secure workflow triggering or draft/job state.
