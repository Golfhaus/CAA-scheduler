# v1.3.2 CRJ200 holistic consolidation screen — October 16, 2026

**Scope:** R160, R176, R146, R158, R107 and R125, measured on the validated R144-augmented draft at `outputs/schedule_7_v1_3_2_r144_accepted/canonical_schedule.json`.

## Verified staging
GitHub Actions run [38932945687](https://github.com/Golfhaus/CAA-scheduler/actions/runs/38932945687) succeeded and committed the R144 staged canonical. It contains **1,225 legs**, including four new R144 flights 2227–2230. CI for commit `020b9a7` also passed. R144 artifacts are staged **outside** the official cumulative five-round canonical. Do not publish or substitute them for main until the cumulative builder, tests, and network regression are updated.

## Baseline
The six targets are all CRJ200; they occupy five distinct lines **AC, AE, AI, AM, AN**. Their local-clock block durations, validated by the cross-line diagnostic on the R144 canonical:

| Route | Line/day | Legs | Block | 06:00–22:00 block (origin-local) |
| --- | --- | ---: | ---: | ---: |
| R160 | AM/4 | 6 | 5h44 | 5h04 |
| R176 | AN/9 | 6 | 6h11 | 5h16 |
| R146 | AI/3 | 5 | 5h27 | 5h17 |
| R158 | AM/2 | 7 | 6h15 | 5h31 |
| R107 | AC/7 | 6 | 5h47 | 5h47 |
| R125 | AE/4 | 9 | 9h20 | 8h06 |

These lines contain, respectively, 10 (AC), 11 (AE), 12 (AI), 12 (AM), and 9 (AN) route-days. Eliminating one target route-day does not free an aircraft; an entire circulating aircraft line with its start/end station cycle and maintenance visits must be made redundant. The target set is 6 route-days embedded among **54** route-days on these five lines. Cross-line suffix exchanges by themselves do not change 76 CRJ200 aircraft used.

## Search findings
The diagnostic found **nine** same-day cross-line arrival/departure handoffs at PHF, SYR and DAY with 40–180 minute ground time. These are splice *candidates* only; they neither match entire multi-day vehicle cycles nor establish an aircraft-release case. Stronger candidates include R160 at PHF to AC day 4 (41 minutes), R158 at DAY to AC or AE day 2 (42 minutes), and R107 at SYR to AM/AN day 7 (41 minutes). Reconstruct all impacted cycles and validate gates, planned flights, maintenance-base overnights, terminal stations and geographic O-D before accepting any swap.

Simple 40-minute minimum-turn insertions at existing long holds are also challenging: longest target mid-route holds run only about 172–197 minutes, and a round trip must accommodate two flight blocks, a 40-minute outer-station turn and **both** the preceding and following 40-minute turns. In particular, R146 has no >=145 minute intermediate hold; R125's previously added PVD–BWI means it is already comparatively productive. Avoid very short weak-demand out-and-back sectors created solely to raise block hours.

## Recommendation and decision threshold
Pursue **two tracks**:
1. Short-term targeted route-wide rebuilds on R160/R176/R146/R158/R107 using bank re-timing and commercially supported reroutes, evaluated collectively for gate competition and connection coverage.
2. A separate, larger CRJ200 fleet-line compression spanning all 54 affected route-days, not merely these six, if the actual objective is to release an entire aircraft. Quantify line-level aircraft used before/after, not just flights moved between route numbers.

Do not label a splice, shortened ground hold or route deletion as a fleet reduction until an end-to-end circulating-line model passes all checks. No optimized six-route overlay was accepted or validated in this stage. Published `main` remains v1.3.1.
