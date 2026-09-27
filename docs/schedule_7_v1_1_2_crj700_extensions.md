# Schedule 7 v1.1.2 CRJ700 route-extension checkpoint

This unpublished feasibility checkpoint extends the four CRJ700 route-days in
v1.1.1 that contained only one or two flights. It retains every released leg,
uses the same 54 CRJ700 aircraft-days, and does not alter the web-app schedule
manifest.

| Route | v1.1.1 | v1.1.2 feasibility | Rationale |
|---|---|---|---|
| 306 | CLT–SYR | CLT–BDL–CLT–SYR | Adds eastern frequency without forcing a seventh daily CLT–PHF flight. A tested SYR turn exceeded the fixed 16-gate passenger capacity. |
| 323 | SRQ–SYR | SRQ–SYR–PHF–SYR | Adds one PHF round trip through existing SYR-B4/B5 and PHF-M3/B5 windows. |
| 344 | SRQ–SYR–MCI | SRQ–SYR–MCI–HRL–MCI | Keeps the aircraft west once it reaches MCI and raises MCI–HRL to three round trips. |
| 350 | ELP–MCI–ELP | ELP–MCI–ELP–MCI–ELP | Keeps the route western and raises ELP–MCI to three round trips. |

## Checkpoint result

- 956 legs, up from 948
- 179 routes and 22 lines, unchanged
- 54 CRJ700 aircraft-days, unchanged
- zero structural failures, effective operating errors, or hard-stop failures
- fixed physical gate and stand inventory passes
- 33 stand claims, unchanged; total stand time falls from 21,761 to 21,037 minutes
- PHF remains at 9 stand claims and 5,616 stand minutes

This checkpoint is local only. It is not listed in `web/schedules.json` and must
not be published to the app until the user explicitly approves publication.
