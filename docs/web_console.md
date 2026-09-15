# Web console

Milestone 0.5 extends the responsive GitHub Pages application with local schedule setup. Published schedule inspection remains static, and draft configurations stay entirely in the browser unless the user exports a JSON file. No token, database, server process, or LLM is required.

## Views

- **Schedule Setup** creates an explicit build configuration for the next schedule. It captures schedule identity, Mainline/Skunkworks mode, previous-schedule or blank starting point, schedule-specific fleet composition, connection limits, pinned instructions/reference inputs, proposed airport changes, and notes. Preflight runs on every change and classifies blockers and warnings. Drafts persist in browser storage and can be exported/imported as portable JSON.

- **Overview** shows network counts, per-schedule fleet utilization, structural fidelity, curfew state, and the largest blocking rule groups.
- **Planning** exposes the fresh demand-derived proposal: schedule-specific fleet counts and aircraft-minute budgets, proposed market frequencies and fleet assignments, generated hub-bank windows, complete aircraft-cycle/RON checks, configured-versus-required fleet fit, historical comparisons, city demand, computed hub qualifications, and explicit remaining construction boundaries.
- **Routings** searches the full canonical construction record and filters by fleet, line, departure airport, or arrival airport. Results can show 50, 250, 500, or all rows.
- **Validation** separates structural fidelity from operating-policy compliance. It filters by status or text, expands exact evidence, and links findings to affected routings or airports.
- **Instructions** displays the build-instruction sections, §2.6 checks, standing lessons, and additions generated from the repository's Markdown sources. Every `§` and `Lesson` reference in Validation opens the exact catalog entry. The source link exposes the underlying Markdown for the current GitHub/ChatGPT editing workflow and provides the foundation for later in-app editing.
- **Timetable** sorts the complete flight list by departure time. Selecting an origin switches to itinerary mode: all non-stops and up to six shortest one-stop options per destination are shown, with shortest two-stop options filling any remaining space up to six. Connections occur only over configured hubs, with BHM treated as a connection hub. The filter can limit results to non-stops or a maximum of one stop.
- **Gates** renders each airport's gates and stands from 03:00 to 03:00 with 24-hour labels, including claims that cross midnight. Every claim is tappable and keyboard accessible. The Stands card is red when the operating report identifies passenger handling on a stand, and only the exact affected turn or RON/ROD arrival/departure segment receives red text and a fleet-colored warning border; an overnight stand segment remains unmarked.

The interface uses the airline's navy, blue, and orange palette, remains usable on phone-sized screens, provides visible keyboard focus, honors reduced-motion preferences, and keeps status meaning in text rather than color alone.

## Data flow

`web/schedules.json` lists each published schedule and its eleven source files: canonical schedule, structural report, operating report, planning snapshot, planning validation, demand plan, frequency/fleet plan, hub-bank plan, aircraft-route plan, timetable, and gate plan. It also pins the primary build-instruction Markdown, any additions, the demand-data manifest, and the generated catalog destination. The build command verifies and copies the demand manifest and all three fingerprinted sources, then rebuilds the instruction catalog directly from its Markdown sources.

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
