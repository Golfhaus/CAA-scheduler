# Schedule 7 v1.2 handoff

> Release update, October 1, 2026: the approved cumulative changes are now
> published as v1.2.0. See `schedule_7_v1_2_0_release.md` and
> `regression_policy.md` for current release and testing policy. The
> feasibility/default statements below describe the original draft stage.


This document is the starting context for Schedule 7 v1.2 work. It records the
current released baseline, durable decisions made during the v1.1.x series,
the optimization tactics that proved useful, and the expected development and
release workflow. Read it before proposing or implementing v1.2 changes.

## Authoritative baseline

- Repository: `Golfhaus/CAA-scheduler`
- Branch to start from: current remote `main`
- Released baseline: `schedule_7_v1_1_6`
- Release commit: `e1389dbf5691f6b51dea8edf9f73857296cec3c5`
- Canonical schedule: `data/schedules/schedule_7_v1_1_6/canonical_schedule.json`
- Release configuration: `config/optimizations/schedule_7_v1_1_6.json`
- Release notes: `docs/schedule_7_v1_1_6_bhm_morning.md`
- Published manifest: `web/schedules.json`
- Demand-data pin: `bts-db1c-6mo-jul2025-apr2026-v7`

The v1.1.6 release contains 1,080 legs, 179 routes, and 23 lines without an
increase in fleet inventory. It has zero effective operating errors and zero
hard-stop failures. Systemwide stand use is 21 claims and 6,188 minutes,
including three PHF claims totaling 446 minutes and four BHM claims totaling
290 minutes.

The GitHub Pages application exposes `schedule_7_v1_1_6` as its default
schedule. Both CI and Pages deployment passed for the release commit.

## Read these files first

1. `docs/schedule_7_v1_2_handoff.md` — this handoff.
2. `docs/schedule_7_v1_1_6_bhm_morning.md` — the most recent release and its
   three optimization rounds.
3. `docs/regression_policy.md` — current test scope for patch, minor, and major
   releases.
4. `instructions/CAA_Build_Instructions_TEMPLATE_v2_0.md` and
   `instructions/additions/BUILD_INSTRUCTIONS_ADDITION.md` — operating policy.
5. `config/optimizations/schedule_7_v1_1_6.json` and its three referenced
   overlays — the reproducible release chain.
6. `docs/schedule_7_v1_1_0_phf_mini_bank_plan.md` through
   `docs/schedule_7_v1_1_5_phf_extensions.md` when an optimization touches a
   route, bank, or tactic introduced earlier in the v1.1 series.
7. `docs/web_console.md` and `web/schedules.json` before changing the app or
   publishing a release.

The per-release notes are not disposable narrative: they explain why timings,
bank exceptions, gate moves, and route extensions were selected. Consult the
relevant note before undoing or retiming prior work.

## Durable scheduling decisions

### Scope and versioning

- Schedule 7 is the active schedule. Schedule 6 is archival. Schedule 6 data
  may remain published for reference, but optimization, normal validation, and
  application flows do not need to process it unless a future major-release
  regression explicitly calls for historical coverage.
- Begin v1.2 from the released v1.1.6 canonical schedule, never from a
  feasibility checkpoint or an older Schedule 7 package.
- Keep v1.2 work as unpublished feasibility overlays until the user explicitly
  says to publish. The user may add several rounds before making that decision.
- Do not change the default schedule, release status, or application manifest
  during feasibility work.
- Ask before making a significant network, fleet, bank, curfew, gate/stand, or
  policy tradeoff. Small timing changes needed to make an approved tactical
  idea work are normally acceptable, but document them.

### Hard operating boundaries

- Fleet quantities belong to the schedule configuration. Do not add an
  aircraft-day or infer extra fleet capacity without explicit approval.
- Curfews are hard stops. Do not silently waive them.
- Fixed gate and stand inventories are hard physical limits. Passenger
  handling on a stand is not an acceptable way to make a proposal fit.
- Preserve legal aircraft continuity, minimum turns, route/line integrity,
  and rolling maintenance-base RON requirements.
- Mixed-fleet service across pairings is permitted. Single-fleet service seen
  in earlier schedules was a result of aircraft assignment, not policy.
- Hub-count exceptions are permitted when geographically reasonable and when
  they materially support the optimization objective.
- Section 2.6b's 240-plus-minute city departure-gap check applies only between
  04:30 and 21:00 local time. Do not count the overnight period.
- Explicit, narrow bank-alignment exceptions may be acceptable when their
  operational value exceeds a small edge miss, but they must be user-approved,
  recorded as overrides, and verified not to create gate or connection harm.

### Connection and service model

- The current connection model is intentionally retained. Additional
  connectivity was deferred to future versions rather than forced into
  v1.1.6. v1.2 may revisit it when the user identifies the objective.
- The timetable shows all nonstops. It shows up to six shortest one-stop
  itineraries per destination; two-stop options fill remaining space only when
  fewer than six one-stop options exist. Connections occur over configured
  hubs, including BHM.
- Optimize for useful frequency, bank connectivity, geography, and demand,
  not raw leg count. Do not force a flight solely to occupy available aircraft
  time. If existing flying is geographically western, keep extensions western
  unless a broader objective justifies a change.
- Preserve existing destinations and terminating/RON cities when practical.
  Moving a terminator later is acceptable when it adds useful flying and still
  satisfies curfew, next-day continuity, and maintenance-base requirements.

### Gates, stands, RONs, and RODs

- Avoid towing an aircraft to a stand when a gate reassignment or productive
  extension can keep the operation within fixed capacity.
- A day hold is ROD; an overnight hold is RON. Gate output and the UI must not
  label a daytime gate-stand-gate move as RON.
- For a gate-stand-gate move, validate the complete path and each segment's
  exact timing. The app displays segment-specific information and highlights
  all linked blocks when any one part is selected.
- Evaluate both stand claim count and stand minutes. A few short claims can be
  preferable to a smaller number of very long holds, while eliminating a tow
  entirely is better when feasible.
- Treat the gate release time, not merely the aircraft's minimum turn, as a
  possible binding constraint on an extension.

## Proven optimization tactics

The v1.1 series established several reusable patterns:

- **Early-terminator extension:** use an aircraft that finishes early for one
  or more additional round trips, normally returning it to its existing RON
  city and reducing a long gate or stand hold.
- **Late-originator pre-bank feed:** operate an early round trip before a late
  first flight, targeting a useful connection bank and retaining recovery
  margin before the existing originator.
- **Reciprocal originator exchange:** two late-originating aircraft can fly
  early in opposite directions and effectively take each other's place.
- **Bank-tail utilization:** aircraft arriving near the end of a bank can
  depart directly into useful flying and return in or after a later bank.
- **Cross-day spoke RON:** send a late terminator to a nearby spoke and connect
  its early return to the following route in the same rotation line, provided
  the next-day turn and maintenance-base cadence remain legal.
- **Alternating-bank round trips:** fit more than one round trip into a long
  hub hold by returning in the bank immediately before the next departure.
- **Outstation residual hold:** when another full trip will not fit, place the
  unavoidable ground time at the less-constrained station instead of a full
  hub.
- **Surgical gate-wave retiming:** move a non-connecting or weakly connecting
  flight within its bank window to release one critical gate touch.
- **Demand per block minute:** when no bank objective dominates, compare useful
  demand to aircraft time rather than simply choosing the largest raw market.
- **Near-bank tradeoff:** a return a few minutes outside a bank can be better
  than sacrificing recovery margin before the route's existing continuation.

Run gate allocation after every meaningful timing or routing change. Several
apparently feasible extensions in v1.1 were constrained by simultaneous
passenger gate touches rather than aircraft time, curfew, or raw gate count.

## Known deferred opportunity

Route 331's early BWI-BHM round trip was evaluated for v1.1.6 and deferred.
BWI's two gates were already occupied by the 04:35 and 05:05 originators.
Leaving early enough to feed BHM created an impermissible passenger touch on a
stand; waiting for a gate missed BHM's available window and cascaded Route
331. Revisit it only as part of a wider BWI bank/rotation change with
independent value.

## Current application behavior to preserve

- Primary review tabs include Overview, Planning, Routings, Validation,
  Timetable, Gates, Instructions, and Sked Stats. Schedule Setup is visually
  separated at the end because it changes future-schedule configuration rather
  than reviewing the current schedule.
- Sked Stats contains Deps to Hubs and Extension Opps. Extension Opps lists
  originators latest-first, terminators earliest-first, and turns/RODs of at
  least two hours longest-first.
- Deps to Hubs is a city-by-hub/focus-city departure matrix. Self-pairs are
  grayed out; selecting a count opens the Timetable with matching filters.
- Routings includes Reset Filters, which preserves the Rows visibility choice.
  Originators use a subtle light-orange background and terminators a subtle
  light-blue background.
- Gates uses `123 -> 124` only for blocks that cross the 03:00 display border.
  Gate/stand cards show peak daily usage as used/capacity. Linked portions of
  a multi-block movement receive a black outline when one portion is selected.
- Gate infoboxes are segment-specific for gate-stand-gate moves and show the
  full path. Day holds are labeled ROD, not RON.
- Validation links `§` and `Lesson` references to the instruction text.
- Later Schedule 7 release packages intentionally omit some original planning
  artifacts such as `frequencyFleetPlan`. The app must continue to tolerate
  these optional files rather than assuming `fleetPlan` is always present.

## Development workflow for v1.2

1. Fetch remote `main` and create a dedicated v1.2 branch from the latest
   commit. Confirm that `web/schedules.json` still identifies
   `schedule_7_v1_1_6` as the default.
2. Inspect the relevant released route sequences, gates, banks, holds, demand,
   and prior optimization notes before proposing changes.
3. Implement each approved round as a new deterministic overlay under
   `config/optimizations/`, based cumulatively on v1.1.6 and earlier v1.2
   overlays. Keep feasibility schedule IDs distinct from the final release ID.
4. Add focused regression tests for the intended route/timing changes and for
   any newly approved exceptions.
5. Rebuild and verify structural, operating, planning, curfew, turn, gate,
   stand, fixed-inventory, Section 2.6, continuity, and maintenance-base RON
   results after each round. Report material tradeoffs and compare stand claims
   and minutes against v1.1.6.
6. Maintain a v1.2 release note as rounds are accepted, including generalized
   tactics learned from each suggestion.
7. Do not publish until explicitly instructed. At release time, create the
   final cumulative optimization config and generated schedule package, update
   `web/schedules.json`, update latest-release tests and routine CI, build the
   web console, commit, merge to `main`, and verify both CI and GitHub Pages.

For patch and minor releases, routine regression covers the engine, web
console, and latest released schedule only. Do not repeatedly reconstruct all
historical versions. Full historical regression is reserved for a major
release and is run manually or by a `v*.0.0` tag as documented in
`docs/regression_policy.md`.

## Collaboration expectations

- Work iteratively and explain the operational result of each round rather
  than only listing changed files.
- Look at each user suggestion for a generalized optimization tactic that can
  be reused elsewhere.
- If an idea cannot work cleanly, quantify how far it misses and identify the
  binding constraint instead of forcing it.
- Ask for clarification when a potentially useful change has a significant
  network, timing, or policy consequence.
- The user will explicitly say when the accumulated v1.2 work is ready to be
  published.
