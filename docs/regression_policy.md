# Latest schedule regression policy

As approved by the user on October 1, 2026, regression testing concerns the
latest released schedule only. Schedule 6, superseded Schedule 7 versions,
the v1.1 series, and rejected feasibility alternatives do not require
reconstruction or regression testing, including at major releases.

Run `bash scripts/run_latest_regression.sh`. Routine CI and the manually
dispatched Latest Schedule Regression workflow use this command. Fixtures
resolve the app's default entry in `web/schedules.json`; release reproduction
uses the pinned configuration recorded in that canonical schedule. Older
canonical inputs may remain necessary to build the latest overlay chain;
using them as release inputs does not test their old release packages.

Coverage includes complete release reproduction, structure, operating rules,
physical gates/stands, overnight turns, planning, approved service gains,
connection accounting, app build, and UI helpers. Interchangeable physical
gate/stand row numbers are normalized for reproducibility comparisons; claims,
movements, timing, and row type must match. Rare UI states use small synthetic
fixtures rather than archived schedule packages.

Old data remains available in the app for reference. Superseded regression
classes remain skipped as historical documentation. The former full-history
workflow now runs latest-only checks and no longer runs automatically for
major-version tags.


## Publication workflow

Deploy Pages runs the current-release regression command in a required
`validate` job for the same commit being published. The site `build` job
requires validation to succeed, and `deploy` requires the build to succeed.
Validation failures therefore leave the existing website in place. The build
uses a fresh checkout so generated validation outputs cannot alter the
published snapshot. This gate applies to both pushes to `main` and manual
Pages deployments.

The completed v1.3.2, v1.3.3, v1.4.0 and v1.4.1 release-packaging workflows
are manual-only historical tools. They no longer run on ordinary pull-request
updates or pushes. CI remains automatic for pushes and pull requests.


## Known v1.3.1 maintenance defect during v1.3.2 review

The corrected validator must report exactly AC/AO/AQ as never reaching a
qualifying RON and reject rebuilding v1.3.1 as a valid new release. Latest
regression explicitly tests this rejection instead of recreating the false
pass in its historical report. All other native, physical and UI checks remain
in force. The same CI command additionally reproduces and validates the pinned
v1.3.2 maintenance draft with zero effective errors, verifies the approved flight replacements and unchanged inventory, and audits itinerary preservation except the explicitly accepted CHS–SFB nonstop pair removed in the R501 repair. Historical release files are
not rewritten. At publication, the latest fixtures must move to v1.3.2 and full
release-artifact reproduction resumes against the corrected release.
