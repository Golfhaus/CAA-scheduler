# Schedule 7 v1.4.3 — controlled AH reassignment analysis

**Research checkpoint, October 22, 2026. No publication or promotion.**

Baseline is the independently preserved `data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json`, 1,286 flights. Separate experimental `scripts/v143_seven_route_rebuild_candidate.py` constructs a 1,292-flight scenario with R313 CLT–JAX, R338 PHF–RDU, R345 CLT–BWI; the previous native/coverage gate returned zero effective operating errors and zero one-stop losses above 8 pax/day. Preserve both.

## Workflow containment

PR #46 remains **closed, unmerged**, and its `analysis/schedule-7-v1.4.3-utilization` branch remains available. Research workflows in the branch have been converted to manual `workflow_dispatch` triggers, including the draft saver, AH exchange screen, and existing v1.4.2 packaging workflows. Do not reintroduce blanket `pull_request` triggers or automatic research branch commits. Trigger one named, consolidated candidate regression intentionally after staging validated changes.

## AH line reassignment geometry (clock minutes at station)

The original R319 day 9 pair:
- #1951 SYR→PHF dep **13:15**, arr **14:40**
- #1952 PHF→SYR dep **15:25**, arr **16:50**
- Pair occupies **215 minutes** (170 flying + 45 PHF turn), plus a minimum 40-minute turn **before and after** the pair for insertion into another aircraft-day, requiring **295 minutes** of available ground window.

Potential AH recipients:
- **R316 day 5:** #1309 arrives SYR **11:12**, #1335 departs SYR **13:15**; gap **123 minutes**, shortfall **172 minutes**. Direct transfer is impossible without relocating significant BNA flying, which is separately protected.
- **R320 day 10:** #1302 arrives SYR **13:21**, #1307 departs SYR **16:50**; gap **209 minutes**, shortfall **86 minutes**. A coupled shift of #1307 SYR→CLT and #1102 CLT→BDL later by at least 86 minutes could create a valid ground window in principle. That might upset SYR bank B5, CLT connections, CLT gates and BDL terminator/RON requirements. It is **not validated or accepted**. R320 is the best *next receiver to screen*, since it visits SYR already and retains the same line, though the bank changes may be prohibitive.
- **R313 day 2** has an early CLT 208-minute hold and a PHF 179-minute hold, not a SYR stop; moving the pair there requires replacing other legs, not an isolated insertion.

A genuine pair migration requires: remove #1951/#1952 from R319, preserve both flight numbers/markets as service on the new route-day, carry revised arrival/departure banks with the legs, renumber contiguous route sequences, preserve AH overnight endpoints, and rerun full physical gate, planning, structural, and market-coverage validation. The target pair must not be duplicated or silently removed.

## Passenger safeguard

For each directional O-D market with **more than 8 pax/day**, verify at least one nonstop-or-one-stop itinerary remains in both the geographically reasonable and unrestricted itinerary views; longer timings can be accepted with quantified tradeoffs. `scripts/v143_rebuild_guard.mjs` enforces that floor. Curfews, fixed gates and stands, physical aircraft continuity and required turns remain hard stops.

## Follow-up execution order

1. Build **R319→R320** coupled-shift research candidate, using shifts >=86m for #1307 and #1102 and time-of-day bank repair. Run full native checks; do not change accepted canonical.
2. If feasible, audit all higher-demand connection losses, especially SYR→CLT and CLT→BDL. If not feasible, reject explicitly and move to more extensive AH flight exchanges.
3. Revisit R303 on AA separately; advancing PNS→MCI alone materially worsens several PNS flows. Protect that existing flight's feeder bank.
4. Only consolidate accepted changes after native and demand audits; retain the 1,286-flight revert point and separate 1,292-flight experiment.
