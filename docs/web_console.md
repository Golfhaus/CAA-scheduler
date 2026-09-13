# Read-only web console

Milestone 0.4 moves schedule inspection into a responsive GitHub Pages application. It is intentionally static: the browser reads version-controlled JSON, and no token, database, server process, or LLM is required.

## Views

- **Overview** shows network counts, per-schedule fleet utilization, structural fidelity, curfew state, and the largest blocking rule groups.
- **Routings** searches the full canonical construction record by flight, airport, route, line, pairing, day, or fleet.
- **Validation** separates structural fidelity from operating-policy compliance. It filters by status or text, expands exact evidence, and links findings to affected routings or airports.
- **Timetable** presents the published passenger-facing flight view with origin, destination, fleet, and text filters.
- **Gates** renders each airport's gates and stands across a cyclic 24-hour timeline, including claims that cross midnight.

The interface uses the airline's navy, blue, and orange palette, remains usable on phone-sized screens, provides visible keyboard focus, honors reduced-motion preferences, and keeps status meaning in text rather than color alone.

## Data flow

`web/schedules.json` lists each published schedule and its five source files: canonical schedule, structural report, operating report, timetable, and gate plan. The build command copies the static application plus only those declared files into a clean deployment directory.

```bash
python -m caa_scheduler build-web --output dist
```

Adding another schedule requires a manifest entry and its generated data files; the browser application itself does not change.

## Deployment

The Pages workflow builds the static directory on every push to `main`, uploads the supported Pages artifact, and deploys it to the `github-pages` environment. CI separately rebuilds the site and runs Python and JavaScript helper tests on pull requests.

The console remains read-only through Milestone 0.4. Construction, repairs, draft storage, and workflow kickoff belong to later milestones.
