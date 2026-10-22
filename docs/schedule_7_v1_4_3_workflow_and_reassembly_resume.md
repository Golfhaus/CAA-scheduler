# Schedule 7 v1.4.3 — notification cleanup and reassembly restart

Date: October 22, 2026. Development PR #46 is closed without merging; branch `analysis/schedule-7-v1.4.3-utilization` remains preserved. Production `main` still has `schedule_7_v1_4_2` as default.

## GitHub Actions guardrails

The v1.4.3 exploratory workflows, draft-saving workflow and obsolete v1.4.2 release packaging workflow on this development branch are configured with `workflow_dispatch` rather than automatic `pull_request` triggers. **Do not reintroduce per-commit research workflows**. The new `.github/workflows/v143-on-demand-validation.yml` is a single manual sequence that reconstructs the accepted 1,286-leg draft, builds the 1,292-leg experimental draft, runs native checks, enforces the >8 passengers/day one-stop floor, and reports passenger travel-time tradeoffs. It does not commit or publish a schedule.

The old per-experiment scripts and result docs remain versioned; no destructive cleanup.

## Reassembly constraint from full canonical inventory

Source: `data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json`.

- R319 AH day9 existing SYR→PHF→SYR flights #1951/#1952 occupy 13:15–16:50 (215 minutes including the 45-minute PHF turnaround). Rehoming the intact pair in another SYR stand needs **~295 minutes** if retaining a conservative 40-minute turn on each side.
- R316 AH day5, SYR hold #1309 arrival 11:12 to #1335 departure 13:15, is **123 minutes**, well below the necessary window. Thus simply moving R319's pair to R316 is infeasible without reassigning or significantly retiming #1335 SYR→BNA and its downstream BNA/PHF flying.
- The **largest CRJ700 SYR hold elsewhere** is R320 AH day10 at SYR, 13:21–16:50 (**209 minutes**), still too short even before considering safe bookend turns; R306 AA day6 SYR hold is 205 minutes.
- Across *all* existing CRJ700 route-days, internal stands at SYR/PHF/CLT/SAV/BNA/MCI longer than 230 minutes are only **R345 CLT 243 minutes** and **R325 MCI 238 minutes**. There is no unused long hub hold into which a complete existing AH SYR–PHF–SYR pair can simply be inserted.
- Genuine swapping therefore requires reconstructing a **multi-leg suffix or entire aircraft-day** (and possibly the adjacent day's originator/terminator), not simply relabeling a paired flight.

## Preserved baselines and next step

- Accepted draft: 1,286 flights, 191 routes, 17 aircraft lines, 14 prior newly added flights; revert point unchanged.
- Experimental cumulative builder: 1,292 flights with R313 CLT–JAX, R338 PHF–RDU and R345 CLT–BWI, native checks passed and zero >8 daily-pax one-stop coverage losses in prior checks. Not promoted.
- Next: search for matched aircraft-day suffix swaps on the AH line which keep terminal station identity, reconstruct R316 and R319 together, and validate exact gates, curfews, and protection guard before saving a modified candidate. Preserve existing PNS connectors on R303.
