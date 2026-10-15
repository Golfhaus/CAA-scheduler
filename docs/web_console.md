# Web console

Milestone 0.5 extends the responsive GitHub Pages application with local schedule setup. Published schedule inspection remains static, and draft configurations stay entirely in the browser unless the user exports a JSON file. No token, database, server process, or LLM is required.

## Views

- **Schedule Setup** creates an explicit build configuration for the next schedule. It captures schedule identity, Mainline/Skunkworks mode, previous-schedule or blank starting point, schedule-specific fleet composition, connection limits, pinned instructions/reference inputs, proposed airport changes, and notes. Preflight runs on every change and classifies blockers and warnings. Drafts persist in browser storage and can be exported/imported as portable JSON.

- **Overview** shows network counts, per-schedule fleet utilization, structural fidelity, curfew state, and the largest blocking rule groups.
- **Planning** exposes the fresh demand-derived proposal: schedule-specific fleet counts and aircraft-minute budgets, proposed market frequencies and fleet assignments, generated hub-bank windows, complete aircraft-cycle/RON checks, configured-versus-required fleet fit, historical comparisons, city demand, computed hub qualifications, and explicit remaining construction boundaries.
- **Routings** searches the full canonical construction record and filters by fleet, line, departure airport, or arrival airport. Results can show 50, 250, 500, or all rows.
  **All Routings** retains this table. **Routing Details** selects a route by number and day/line, then charts its Inflight, Gate and Stand activity. Flight blocks show flight numbers; hover, keyboard focus or tap exposes local endpoint cities/times or the actual city and gate/stand position. Chart geometry uses the starting airport's time zone to preserve flight duration across time zones. The operating-day view includes clipped pre-originator and post-terminator overnight claims, with no inferred physical assignments.
- **Validation** separates structural fidelity from operating-policy compliance. It filters by status or text, expands exact evidence, and links findings to affected routings or airports.
- **Instructions** displays the build-instruction sections, §2.6 checks, standing lessons, and additions generated from the repository's Markdown sources. Every `§` and `Lesson` reference in Validation opens the exact catalog entry. The source link exposes the underlying Markdown for the current GitHub/ChatGPT editing workflow and provides the foundation for later in-app editing.
- **Timetable** sorts the complete flight list by departure time. Selecting an origin switches to itinerary mode: all non-stops and up to six shortest one-stop options per destination are shown, with shortest two-stop options filling any remaining space up to six. Connections occur only over configured hubs, with BHM treated as a connection hub. The filter can limit results to non-stops or a maximum of one stop.
- **Gates** renders each airport's gates and stands from 03:00 to 03:00 with 24-hour labels, including claims that cross midnight. Every claim is tappable and keyboard accessible. The Stands card is red when the operating report identifies passenger handling on a stand, and only the exact affected turn or RON/ROD arrival/departure segment receives red text and a fleet-colored warning border; an overnight stand segment remains unmarked.

The interface uses the airline's navy, blue, and orange palette, remains usable on phone-sized screens, provides visible keyboard focus, honors reduced-motion preferences, and keeps status meaning in text rather than color alone.

## Operating-day chart standard

Every chart showing progression through the operating day uses the shared
`web/operating-day-timeline.mjs` grid and `.operating-day-timeline` styles.
Show every hour as a two-digit 24-hour label (`03`, `04`, …), with subtle
alternating hour shading and thin hourly boundaries behind the activity.
Center each hour label over its entire hour band, rather than its start boundary.
Keep full times, time zones and day offsets in tooltips and accessible text;
retain the chart's existing time zone and unwrapped midnight geometry.

Gates and Routing Details use this standard. New time-based charts should reuse
the same grid and axis/band renderers in `web/app.mjs`, rather than choose a new
tick interval or independent shading. Chart width responds to the available
space, with a minimum of 3rem per hour so a 40-minute turn has room for a
complete three-digit route label. Readability takes priority over reducing
horizontal scrolling, including on phones. Longer route
days add only the width needed for the extra hours. Horizontal scrolling stays
inside the chart panel on narrow screens.

## Opportunity tools in Sked Stats

**Service Coverage** ranks city pairs by pinned daily O-D demand in missing directions. It distinguishes one-way and two-way gaps, fastest available trips, missing shared hubs and timing gaps. An optional 2.25× great-circle-distance screen separates impractical detours from the current timetable's listed connections. Missing demand remains unavailable rather than becoming zero; schedules whose demand pin differs from the served snapshot retain coverage analysis without demand ranking.

**Connection Near-Misses** identifies the closest missed transfer for each missing direction, with 5/10/15/30-minute filters and larger options. Arrival and departure repair choices expose basic aircraft-turn, overnight, assigned-bank, departure-window and spacing-floor constraints. A read-only preview recomputes all direct/one/two-stop service and reports coverage gains/losses, lost itinerary choices and faster/slower journeys. It explicitly distinguishes a new one-stop trip from a faster trip. Previews are timing screens, not complete gate, spacing or maintenance validation; they never mutate the selected schedule.

**Bank Effectiveness** counts actual timed, geographically reasonable transfers. Per-flight onward/feed counts include other banks inside the connection window. Unique directional market O-D is counted once, not once per flight combination, and is not a passenger forecast. The bank arrival/departure matrix explains valid and missed transfers. BHM's unassigned flying remains inspectable without inventing bank assignments. Large whole-day matrices ask for a bank selection while retaining full-day feed counts.

City-pair, route and gate buttons connect these views to Timetable, Routing Details and Gates. Analysis loads only when requested, is cached per selected schedule and resets on schedule changes. The existing published schedule manifest and default remain unchanged by these UI features.

## Data flow

`web/schedules.json` lists each published schedule and its fourteen source files: canonical schedule, structural report, operating report, planning snapshot, planning validation, demand plan, frequency/fleet plan, hub-bank plan, aircraft-route plan, routing repair, bank-materialization diagnostic, exact materialization plan, timetable, and gate plan. It also pins the primary build-instruction Markdown, any additions, the demand-data manifest, and the generated catalog destination. The build command verifies and copies the demand manifest and all three fingerprinted sources, then rebuilds the instruction catalog directly from its Markdown sources.

```bash
python -m caa_scheduler build-web --output dist
```

Adding another schedule requires a manifest entry and its generated data files; the browser application itself does not change.

## Deployment

The Pages workflow builds the static directory on every push to `main`, uploads the supported Pages artifact, and deploys it to the `github-pages` environment. CI separately rebuilds the site and runs Python and JavaScript helper tests on pull requests.

The repository must be configured once under **Settings → Pages → Build and deployment** with **GitHub Actions** selected as the source. The workflow deliberately does not carry a personal access token or attempt to change repository settings.

Published schedules and instructions remain read-only. Schedule Setup writes only to browser-local storage and user-downloaded JSON; it cannot alter the repository or launch construction. Instruction changes continue through the normal GitHub/ChatGPT review workflow. Milestone 0.6 consumes an approved `build_config.json` through the Python candidate compiler and a manually dispatched GitHub Action. Secure kickoff directly from Pages and shared draft storage remain later work.

## Schedule Setup contract

The authoritative portable format is defined by `schemas/build_config.schema.json`. Fleet counts are required fields in every configuration and are not hard-coded in the UI or engine. Selecting a previous schedule copies its counts only as editable starting values.

Preflight currently verifies schedule identity, mode, baseline selection, fleet counts, connection limits, pinned instruction/city/policy/demand inputs, and the structural validity of airport changes. Airport additions receive a warning until metadata, demand, and runway screening are completed. Curfew compliance cannot be evaluated before flights exist, but the operating-policy pin is mandatory and curfew violations remain hard stops once construction runs.

Browser storage is intentionally a convenience layer, not an authoritative database. Export the JSON to move or review a draft; importing and re-exporting produces the same normalized document.

