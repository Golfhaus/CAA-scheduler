# Read-only web console

Milestone 0.4 moves schedule inspection into a responsive GitHub Pages application. It is intentionally static: the browser reads version-controlled JSON, and no token, database, server process, or LLM is required.

## Views

- **Overview** shows network counts, per-schedule fleet utilization, structural fidelity, curfew state, and the largest blocking rule groups.
- **Routings** searches the full canonical construction record and filters by fleet, line, departure airport, or arrival airport. Results can show 50, 250, 500, or all rows.
- **Validation** separates structural fidelity from operating-policy compliance. It filters by status or text, expands exact evidence, and links findings to affected routings or airports.
- **Instructions** displays the build-instruction sections, §2.6 checks, standing lessons, and additions generated from the repository's Markdown sources. Every `§` and `Lesson` reference in Validation opens the exact catalog entry. The source link exposes the underlying Markdown for the current GitHub/ChatGPT editing workflow and provides the foundation for later in-app editing.
- **Timetable** sorts the complete flight list by departure time. Selecting an origin switches to itinerary mode: all non-stops and up to six shortest one-stop options per destination are shown, with shortest two-stop options filling any remaining space up to six. Connections occur only over configured hubs, with BHM treated as a connection hub. The filter can limit results to non-stops or a maximum of one stop.
- **Gates** renders each airport's gates and stands from 03:00 to 03:00 with 24-hour labels, including claims that cross midnight. Every claim is tappable and keyboard accessible. The Stands card is red when the operating report identifies passenger handling on a stand, and only the exact affected turn or RON/ROD arrival/departure segment receives red text and a fleet-colored warning border; an overnight stand segment remains unmarked.

The interface uses the airline's navy, blue, and orange palette, remains usable on phone-sized screens, provides visible keyboard focus, honors reduced-motion preferences, and keeps status meaning in text rather than color alone.

## Data flow

`web/schedules.json` lists each published schedule and its five source files: canonical schedule, structural report, operating report, timetable, and gate plan. It also pins the primary build-instruction Markdown, any additions, and the generated catalog destination. The build command copies the static application and schedule data, then rebuilds the instruction catalog directly from those Markdown sources.

```bash
python -m caa_scheduler build-web --output dist
```

Adding another schedule requires a manifest entry and its generated data files; the browser application itself does not change.

## Deployment

The Pages workflow builds the static directory on every push to `main`, uploads the supported Pages artifact, and deploys it to the `github-pages` environment. CI separately rebuilds the site and runs Python and JavaScript helper tests on pull requests.

The repository must be configured once under **Settings → Pages → Build and deployment** with **GitHub Actions** selected as the source. The workflow deliberately does not carry a personal access token or attempt to change repository settings.

The console remains read-only through Milestone 0.4. Instruction changes currently use the normal GitHub/ChatGPT workflow: edit the Markdown source, review the diff, and deploy the regenerated catalog. In-app instruction editing can later write the same Markdown through the secure build/publish service rather than introducing a second storage format. Construction, repairs, draft storage, and workflow kickoff belong to later milestones.
