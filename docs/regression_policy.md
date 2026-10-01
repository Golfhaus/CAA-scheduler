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
