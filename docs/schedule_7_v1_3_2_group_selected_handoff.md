# Schedule 7 v1.3.2 — holistic low-utilization CRJ200 optimization handoff

**October 16, 2026 — unpublished working draft.** `main` / web app remain **v1.3.1**; the five-round historical checkpoint remains available at **1,221 flights**; the standard cumulative v1.3.2 draft canonical and the validated working schedule both contain **1,229 flights**. A separately staged and fully validated **1,229-flight** working schedule is available at [`outputs/schedule_7_v1_3_2_group_selected/canonical_schedule.json`](../outputs/schedule_7_v1_3_2_group_selected/canonical_schedule.json). This is the pinned reference checkpoint for further optimization; the standard draft builder was updated October 16 and reproduces an exactly matching canonical. Do not substitute it into the released app.

## User-directed priority

**Optimize useful aircraft flying on R160, R176, R146, R158 and R107 as a holistic group.** R125 was already upgraded with PVD–BWI and can remain unchanged. Reducing aircraft is a *secondary nice-to-have*, never a reason to drop valuable network coverage or add otherwise unattractive flying. No publication approval.

## Adopted into the staged working draft

- **R144** (approved earlier): original JAN–MCI–OKC–MCI–SHV sectors retained, JAN–JAX–JAN at 04:30 CT and evening MCI–BNA–MCI added; four to eight flights, **5h38 → 12h04** block. Earlier [review](schedule_7_v1_3_2_r144_review.md); native gate/maintenance validation passed. This precedes the five-route group but is part of the combined working baseline.
- **R146** (line AI/day 3): advance MCI–FSD 30 min to 18:25–19:36 CT; add FSD 20:16–MCI 21:27 / MCI 22:15–FSD 23:26 CT. Five to seven flights; **5h27 → 7h49** block; R146 passes native gate/maintenance, gains ten reasonable coverage markets, loses one small ATW–FSD market (0.7 O-D/day). [Review](schedule_7_v1_3_2_group_optimization_review.md).
- **R176** (line AN/day 9): GSO–PHF advanced 45 minutes to 09:15–10:11 ET; insert PHF 10:51–GSO 11:47 / GSO 12:27–PHF 13:23; shift PHF–CAE eight minutes to 14:03–15:18. Six to eight flights, **6h11 → 8h03** total block, **5h16 → 7h08** critical-period block. Individual native checks pass; **16 reasonable market coverage gains, no losses, 33 improved/15 slower fastest journeys**. Local PHF/GSO O-D is modest (0.7–0.8/day), but connecting value is significant: DAL–GSO 25.6/day, PIE–GSO 13.4/day, HOU–GSO 9.4/day underlying directional market demand (not forecast loads). Some GSO-origin paths to DAL/HOU become 45 minutes slower.
- **R158** (line AM/day 2): replace late ALB–SYR–ALB flights 2053/2054 with ALB 18:09–RDU 19:52 / RDU 20:32–ALB 22:15 ET. Seven flights remain seven; **6h15 → 8h13** block, **5h31 → 7h58** critical-period block. Both directions of ALB–RDU have about **35 O-D/day**, more commercially meaningful than the ALB–SYR late turn. Individual native checks pass; **one new reasonable direct-coverage market RDU–ALB (34.6/day), no losses; two faster and three slower**. R158 remains overnight in ALB with improved overnight margin.

R146 overlay in `config/optimizations/schedule_7_v1_3_2_r146_selected.json`; R176 and R158 overlays in `config/optimizations/schedule_7_v1_3_2_r176_selected.json` and `config/optimizations/schedule_7_v1_3_2_r158_selected.json`. Builder `scripts/stage_schedule_7_v1_3_2_group_selected.py` applies the last two atop the earlier validated 1,227-flight R144/R146 draft, reproduces the **1,229-flight** canonical, structural/overnight/planning/operating/gates exports, asserts fixed fleet/stands, and never touches `main`.

**Combined validation:** [GitHub Actions successful run 38941800181](https://github.com/Golfhaus/CAA-scheduler/actions/runs/38941800181): full group native checks and routine regression successful; no extra line-days, no additional fleet or stand claims, zero effective operating errors. App-equivalent [network review](../outputs/schedule_7_v1_3_2_group_selected/network_review.json) versus the prior R144/R146 baseline: **17 geographic coverage gains, zero losses; 35 faster / 18 slower fastest journeys; no stop-count downgrades**. The improved results are not flight-load forecasts. Note that the earlier R144 and R146 passenger effects remain separately documented and are not included in the 17/0 or 35/18 incremental counts.

| Route | 1,227-flight pre-group selected baseline | Current 1,229-flight selected | Critical-period before → after |
| --- | ---: | ---: | ---: |
| R107 | 6 flights / 5h47 | unchanged | 5h47 → 5h47 |
| R125 | 9 flights / 9h20 | unchanged | 8h06 → 8h06 |
| R146 | 7 flights / 7h49 | unchanged after prior improvement | 6h28 → 6h28 |
| R158 | 7 flights / 6h15 | 7 flights / **8h13** | **5h31 → 7h58** |
| R160 | 6 flights / 5h44 | unchanged | 5h04 → 5h04 |
| R176 | 6 flights / 6h11 | 8 flights / **8h03** | **5h16 → 7h08** |

## Rejected alternatives; no unjustified extensions

- **R160**: late SYR–PWM duplication failed spacing; daytime SYR–ROC/BUF/ALB/AVP additions failed physical gates, spacing, and/or station service constraints. Replacing terminal SYR–PWM with SYR–PHF–PWM failed gate capacity. SYR–PIT–PWM and SYR–BDL–PWM passed native checks but lost **MCI–PWM reasonable coverage** (7.2 underlying O-D/day), downgraded 14 markets, and slowed important existing PWM connections. No R160 change selected.
- **R107**: late CAK–SYR–CAK return technically passed but had only ~1.3/1.4 directional O-D/day and **zero geographic coverage gains**, worsening BDL–CAK. Redirecting the final BDL/SYR sectors via PHF or DAY to CAK failed physical gate capacity and tiered service minimums. No R107 change selected.
- **R158**: short SYR–ROC round trip passed physical but net network was weak: five coverage gains, one loss (SBN–SYR) and 49 slower fastest journeys. Evening ALB–BWI replacement failed fixed gate inventory, ALB–PIT added no coverage, ALB–PHF failed bank alignment. ALB–RDU was materially stronger and chosen.
- **R176**: PHF–RDU/ROA physically passed but either lost geographic coverage or worsened more itineraries. PHF–BWI failed passenger-gate constraints. PHF–GSO produced the strongest balance, no coverage loss.
- **R125**: intentionally untouched; existing PVD–BWI daytime upgrade retained.

All rejected candidate evidence: `outputs/schedule_7_v1_3_2_daytime_screen/`, `outputs/schedule_7_v1_3_2_daytime_refined/`, `outputs/schedule_7_v1_3_2_r158_rebuild/`, and `outputs/schedule_7_v1_3_2_terminal_rebuild/`. Do not introduce a gate waiver or low-demand shuttle merely to improve utilization figures.

## Remaining integration work

The standard `scripts/build_schedule_7_v1_3_2_draft.py` now reproduces **1,229** flights and includes the selected R144/R146/R176/R158 additions. `--five-round-only` recreates the original 1,221-flight checkpoint for historical regression. The full cumulative `data/schedules/schedule_7_v1_3_2_draft/` artifacts have been regenerated, and an exact canonical/assignment comparison to the pinned 1,229-flight reference passed. Before any publication, run a final complete network comparison against released v1.3.1 and obtain explicit release authorization. Use the independently validated **1,229-flight** output as the reference checkpoint. **Do not publish to main without separate user approval.**
