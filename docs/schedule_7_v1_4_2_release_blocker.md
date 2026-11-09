# Historical Schedule 7 v1.4.2 candidate blocker (October 21, 2026)

**Historical checkpoint.** The 1,274-flight candidate described here was blocked by gate conflicts. v1.4.1 was the application default at that checkpoint. The final 1,272-flight package subsequently passed the release gate and became the application default on October 21, 2026. See the [published v1.4.2 release notes](schedule_7_v1_4_2_release.md).

## Authorized policy
`operatingPolicy.hubCountCeilingEnabled=false` is intended **only for Schedule 7 v1.4.2 and later Schedule 7 variants**. The validator defaults to true when the flag is absent, preserving the existing ceiling for Schedule 8 and other schedules. Flight-count floors and all physical/gate/curfew rules are untouched. The standing instructions template should not be globally amended for Schedule 8.

## Candidate scope
- Tactical flight 1357 BLV–MCI +6 minutes; 1077 MCI–BNA -11 minutes.
- R177 DAY–SRQ–DAY added as CRJ200 AF line day 7, yielding 12-day AF and 1,268-flight validated provisional checkpoint.
- R178 SYR–RDU–SYR as a CRJ200 AC additional day, with coordinated HVN–SYR #1879 retiming -50 minutes and SYR bank corrections. Gate/structure continuity can pass; fifth RDU hub is enabled only under the Schedule 7 scoped policy.
- R359 BNA–BHM flying as a CRJ700 AH additional day to improve BNA–ECP and BNA–OMA connections. Multiple six-, four-, and two-flight patterns were screened. All patterns tested have physical inventory/gate conflicts at BNA and/or BHM without altering fixed capacities.

## Cumulative blocker
Full cumulative 4-leg R359 candidate check in GitHub Actions run 39602425646: **1,274 legs, 191 routes, 17 lines; structural and overnight pass; six effective operating errors** concentrated in `passenger_touch_on_stand` and `fixed_physical_inventory` at BHM/BNA. A gate-optimized pattern reached **one remaining BNA gate error**, but did not pass. Later alternative timing screens also failed fixed BHM/BNA capacity. These findings blocked publication of this candidate.

## Follow-up proposed at the checkpoint
The proposed follow-up was to reconstruct existing BNA/BHM flight occupations, particularly the R512 BNA turn at 19:00–19:40, R129/R705 and BNA RONs, within fixed gate counts. A narrower R359 service plus BNA–MCI retime #1080 for BNA–OMA was commercially viable and still needed to clear native gate checks. The review called for passenger-itinerary comparisons and latest-release regression after a clean canonical candidate was available.

Development scripts and passenger studies remain in nonmergeable analysis PR #43, not in this clean release branch.
