# Canonical schedule v1

The canonical schedule is the authoritative representation of a Coastal American Airways schedule. Consumer files, workbooks, gate views, opportunity products, and future web-app views are derived from it.

## Design choices

- `schedule` records the identity, lifecycle status, and connection-window settings for the build.
- `provenance` pins the exact source files by filename and SHA-256 digest. A build never silently changes because a newer reference file appeared.
- `cities` is the schedule's operational city snapshot. It contains the metadata needed by downstream validators and exporters while retaining the source-file digest for full traceability.
- `legs` is a flat, ordered collection. Each leg preserves Route, Line, Fleet, Day, Pairing, Flight, origin, destination, departure, and arrival from the workbook.
- `sequenceWithinRoute` makes routing order explicit. Array order is retained for deterministic import, but validators and future tools do not need to infer sequence from workbook row position.
- Clock values remain `HH:MM` strings because that is the established timetable contract. Day offsets can be added as a backward-compatible schema extension when overnight airborne legs require them.

## Identifiers

For the v2.2.5 baseline, Flight numbers are unique, so each leg receives an ID such as `flight-1001`. Future construction code should create a stable leg ID before assigning a public Flight number if draft legs need to exist without one.

## Derived products

The v0.1 timetable exporter deliberately reproduces the existing Pages contract:

- cities sorted by airport code;
- flights sorted by Flight number;
- only `code`, `name`, `isHub`, and `isFocusCity` in city records;
- only `origin`, `dest`, `dep`, `arr`, `flight`, and `fleet` in flight records.

This lean output remains a view. Editing it does not edit the canonical schedule.
