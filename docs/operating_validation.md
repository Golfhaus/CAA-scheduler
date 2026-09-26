# Operating-rule validation

Milestone 0.3 converts the standing Build Instructions v2.0 plus the turn-on-stand hard-stop addition into a deterministic, evidence-bearing report. Policy constants live in `config/policies/operating_rules_v2_0.json`; a canonical build embeds that policy and pins its SHA-256 digest.

Fleet size is deliberately not an operating-policy constant. Each schedule supplies its own `schedule.fleetCounts` build input, which is preserved in canonical JSON and evaluated against that schedule's aircraft-day use. Changing the fleet for a future schedule does not require a code or policy edit.

## Result states

| Status | Meaning |
|---|---|
| `pass` | The check ran and produced no findings. |
| `fail` | One or more unoverridden hard findings remain. |
| `warning` | The check ran and found items requiring human review. |
| `not_evaluated` | The rule is implemented, but required source data is absent. |
| `overridden` | Every finding has an exact, documented approval in the pinned policy. |

Overrides match both `checkId` and `findingId`; broad check-level waivers are not supported. Each override requires a reason and can identify an approver and expiration schedule. Unmatched or expired overrides are themselves reported as warnings. Hard-stop checks, including curfews, cannot be overridden.

## Implemented checks

- Active-city service coverage
- Fleet aircraft-day capacity
- Earliest departure, destination curfew, hub/focus curfew, and red-eye windows; violations are marked as hard stops
- Route continuity across consecutive days and wraparound
- Minimum turns and long-hold review
- Routes-per-line guideline
- Rolling target-city RON window and standing one-day grace
- Destination RON coverage
- Point-to-point share
- Per-direction market-frequency ceiling
- Section 2.6 Check A, including the 30-minute hard floor, station factor, 90% tolerance, one-exception allowance, and hub-bound exemption from the target formula
- Section 2.6 Check B maximum city departure service gaps within the 04:30–21:00 service day
- Route/flight numbering conventions
- Cyclic physical-slot conflicts, passenger handling on stands, configured stand capacity, and one-minute combined capacity
- Runway screening when runway data exists
- Percentile-tier service when demand percentiles exist
- Hub-bank counts, widths, touch completeness, station matching, and timing when bank definitions and assignments exist

## Schedule 6 v2.2.5 baseline

Structural validation passes and both published outputs remain byte-identical. The operating report separately records current-policy findings without changing the frozen schedule.

Section 2.6 Check B is a service-spacing rule: between 04:30 and 21:00, consecutive departures from a city should not be more than 240 minutes apart, regardless of destination. The overnight period and the gaps from the window edges to the first or final flight are excluded. The check remains warning-only and is not a curfew.

Curfews are different: the configured departure windows are enforced as hard-stop errors. A schedule with an unapproved departure outside those windows fails operating validation.

The unavailable checks are also deliberate evidence:

- runway lengths are blank throughout the pinned city snapshot;
- demand percentiles and proposed tier service remain separate in `demand_plan.json` and `frequency_fleet_plan.json` until timed canonical legs can be constructed from the proposal;
- the workbook does not preserve hub-bank definitions or per-leg bank assignments.

Future builds should supply these fields directly. A missing input must not be mistaken for a passed rule.

## Commands

```bash
python -m caa_scheduler validate-operating \
  data/schedules/schedule_6_v2_2_5/canonical_schedule.json \
  --output operating_validation_report.json
```

This command exits with status 1 when effective hard findings remain. The `baseline` command exits based on reproducibility, planning-snapshot consistency, demand-input validity, and golden export parity—not current-policy cleanliness—so the frozen historical schedule can remain a valid fixture while its current-policy deviations stay visible.
