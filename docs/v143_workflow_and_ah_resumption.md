# Schedule 7 v1.4.3 — quiet development resumption

Updated October 22, 2026.

## Preservation
- Published `main` continues to default to `schedule_7_v1_4_2`.
- Accepted `data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json` remains the 1,286-flight revert point.
- Separate `schedule_7_v1_4_3_rebuild_candidate` and `schedule_7_v1_4_3_ah_exchange_candidate` retain 1,292 flights each. Neither is published.
- GitHub draft PR #46 is **closed without merge**, development branch preserved.

## Notification reduction verified
- Audited 40 workflow files modified relative to `main`. The 39 release/research workflows are `workflow_dispatch` (manual) only, including former historical v1.4.2 release jobs.
- `.github/workflows/ci.yml` is the sole automatically triggered changed workflow; it runs only on `main` pushes or pull requests to `main`. With PR #46 closed, development commits don't automatically trigger that CI.
- No new periodic, push or pull-request research trigger was introduced during this resumption.
- A single manual aggregate run in `.github/workflows/v143-on-demand-validation.yml` now checks the preserved draft, 1,292-flight reconstruction, >8 pax one-stop protection, reciprocal AH swap and the resulting passenger-commercial audit.

## Stored AH reciprocal reassignment
This is a real movement of existing flight assignments, not extra flights:
- #1951 SYR→PHF: R319 → R317, 13:15 → 18:10.
- #1952 PHF→SYR: R319 → R317, 15:25 → 20:15.
- #2103 SYR→RFD: R317 → R319, 16:50 → 12:00.
- #2104 RFD→SYR: R317 → R319, 18:44 → 13:54.

The saved exchange remains experimental pending an explicitly invoked complete manual run and comparison of timing concessions and original 1,286-flight connectivity. Do not promote it automatically. A 1,292-flight 7-route builder and the stored snapshots provide reconstruction inputs; do not alter the accepted 1,286-flight draft in place.

## Next actions
Manually run one `v1.4.3 On-Demand Candidate Validation` for the development branch when necessary (select branch explicitly in GitHub Actions). Check zero operating errors, fixed gate/stand capacity, overnight line continuity, planning pass, and zero >8 pax/day one-stop losses in **both** itinerary models. Reject swap candidates that fail; evaluate high-demand timing tradeoffs for those that pass. When a candidate is ready, prepare a separate clean release PR; don't reopen the notification-heavy research PR until the workflow configuration is audited again.
