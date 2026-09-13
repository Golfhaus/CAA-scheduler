# Canonical schedule v1

The canonical schedule is the authoritative representation of a Coastal American Airways schedule. Consumer files, workbooks, gate views, opportunity products, and future web-app views are derived from it.

## Design choices

- `schedule` records the identity, lifecycle status, and connection-window settings for the build.
- `provenance` pins the exact source files by filename and SHA-256 digest. A build never silently changes because a newer reference file appeared. For v2.2.5 it also records the gate artifact used to recover operational sub-minute timing lost by the workbook export.
- `gatePlan` records version-specific ground-handling decisions, including the viewer label and deliberate long-hold stand splits.
- `operatingPolicy` embeds the exact versioned rule values used for validation; its source file and SHA-256 digest are pinned in `provenance`.
- `cities` is the schedule's operational city snapshot. It contains the metadata needed by downstream validators and exporters while retaining the source-file digest for full traceability.
- `legs` is a flat, ordered collection. Each leg preserves Route, Line, Fleet, Day, Pairing, Flight, origin, destination, departure, and arrival from the workbook.
- `schedule.fleetCounts` records the fleet size selected for that individual schedule; it is a build input, not a global policy constant.
- `sequenceWithinRoute` makes routing order explicit. Array order is retained for deterministic import, but validators and future tools do not need to infer sequence from workbook row position.
- `departure` and `arrival` remain `HH:MM` strings because that is the established timetable contract.
- `departureMinute` and `arrivalMinute` are the operational numeric times consumed by deterministic scheduling and gate logic. `arrivalMinute` may exceed 1440 when a leg lands after midnight. This prevents both overnight-day loss and sub-minute rounding loss.

## v2.2.5 timing recovery

The legacy workbook contains rounded display strings, while the published gate JSON retains exact numeric times for 24 of the 105 cities. During the one-time baseline import, each flight is matched to its gate arrival and departure claim using route, station, adjacent station, and rounded clock time. All 1,383 legs match within one minute. The source artifact and SHA-256 digest are recorded under `provenance.gateTimingBaseline`.

This adapter is migration-only. Future schedules will create operational minute values directly and will not need a prior gate export.

## Identifiers

For the v2.2.5 baseline, Flight numbers are unique, so each leg receives an ID such as `flight-1001`. Future construction code should create a stable leg ID before assigning a public Flight number if draft legs need to exist without one.

## Derived products

The v0.1 timetable exporter deliberately reproduces the existing Pages contract:

- cities sorted by airport code;
- flights sorted by Flight number;
- only `code`, `name`, `isHub`, and `isFocusCity` in city records;
- only `origin`, `dest`, `dep`, `arr`, `flight`, and `fleet` in flight records.

This lean output remains a view. Editing it does not edit the canonical schedule.

The gate exporter likewise remains a view. One shared gate engine now owns cyclical overlap checks, claim construction, waypoint splitting, physical assignment, movement links, and peak demand. See [Gate engine](gate_engine.md).

The operating validation report is also derived. It separates hard failures, review warnings, unavailable checks, and explicitly approved finding-level overrides. See [Operating-rule validation](operating_validation.md).
