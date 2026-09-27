# Schedule regression policy

Routine CI for patch and minor Schedule releases validates the current engine,
web console, and latest released schedule only. The latest schedule must be the
default entry in `web/schedules.json`, reproduce operationally from its pinned
release configuration, and pass structural, operating, planning, gate, stand,
and app build checks. Interchangeable physical gate/stand row numbers are
normalized for comparison; claims, movements, timing, and row type must match.

Historical schedule reconstruction is not part of routine patch/minor CI.
Schedule 6 baseline regression and superseded Schedule 7 optimization-release
regression are enabled only when `FULL_SCHEDULE_REGRESSION=1`.

The `Full Schedule Regression` GitHub Actions workflow sets that flag and runs:

- when started manually before a major release; or
- when a major-version tag matching `v*.0.0` is pushed.

Assertions already retired as archival incompatibilities remain skipped even in
the full workflow. They document obsolete golden output rather than supported
behavior.
