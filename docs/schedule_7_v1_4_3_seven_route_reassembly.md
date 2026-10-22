# Schedule 7 v1.4.3 — seven-route reassembly authorization and regression gate

2026-10-21. **Exploratory only; DO NOT publish.** User authorizes broad reconstruction of routes **303, 313, 316, 319, 338, 339, 345**, including unassigning and reassembling flights and substantial retimings. The previous **1,286-leg, 191-route, 17-line v1.4.3 draft is a hard revert point** and must not be modified in place until construction and commercial validation succeed. Current released `main` remains v1.4.2.

## Highest-priority protected invariant

**No directional market with >8 underlying passengers/day may deteriorate from one-stop (or nonstop) service to needing 2+ stops or no service.** This is checked in both the geographically reasonable and all technically reachable itinerary models, on a direction-by-direction basis. `scripts/v143_rebuild_guard.mjs` now turns such a loss into a failing exit status; any above-threshold loss blocks release, regardless of other benefits. For markets **≤8 passengers/day**, losses can be considered but must still be reported. Longer minimum journey time without stop-count deterioration is acceptable when justified by offsetting demand/service improvements. No physical gate/stand, curfew, aircraft-turn, or cyclic-line violations may be waived.

## Line structure and scope

- R303 is AA day 3 (BHM→PNS).
- R313, R316, R319 are AH days 2, 5 and 9 (BDL→SAV; PVD→BNA; SRQ→ABE).
- R338, R339 are AK days 1 and 2 (PHF→SAV; SAV→CHS), cyclically adjacent at SAV.
- R345 is AS day 6 (SDF→PHF).

All seven may be reorganized jointly, but aircraft-day endpoints must remain connected with preceding/succeeding line days; line AH/AK/AS/AA identities cannot be silently interchanged, and new aircraft cannot be assumed. Rebuilding can move a flight across routes only if all other routes and full line turns remain valid.

## Initial construction experiments

1. Reproducible `scripts/v143_seven_route_rebuild_candidate.py` stages two previously native-feasible physical changes together:
   - R313 CLT→JAX 07:02–08:13, JAX→CLT 08:53–10:04, followed by existing #1379 CLT→PHF retimed to 10:50–11:56. Existing PHF→AVP #1745 **not** retimed, because its later departure materially damages SFB/RFD→AVP; this is a *commercial timing tradeoff* if the hard guard passes.
   - R338 PHF→RDU 13:53–14:43, RDU→PHF 15:23–16:13, followed by existing #1493 PHF→SAV retimed to 17:00–18:26. Preserves evening SAV→JAX and all other station visits, at cost of slower BDL/HPN/ALB/SYR→SAV trips if their stop count is preserved.
   - Combined candidate would add 4 legs, from 1,286 to **1,290**, if structure, gates, overnight, planning and above-8 market coverage gate pass. **This is not yet an accepted canonical update.**
2. `scripts/v143_r303_early_originator.py` tests advancing BHM→MCI flight #1409 from 06:30 earlier, then inserting MCI-originating SGF/OMA/DSM/TUL morning mini-turns **without moving #1346 PNS→MCI**. This avoids the documented >8 passenger PNS connectivity regressions from earlier PNS retimes. Structural and passenger validation required; do not accept speculative blocks.
3. The earlier R345 short CLT side turns passed gates but lacked meaningful O-D/connection demand; meaningful expansion requires reassigning a leg or retiming downstream PHF→GSP. R316/R319 remain congested at PHF/SYR; swapping portions of AH rather than artificially lengthening a hold is required.
4. A completed native-valid R338 PHF→SAV earlier-side turn had unacceptable loss of reasonable Northeast→SAV itineraries; current staging therefore uses the **later** PHF→SAV timing, contingent on hard-stop-count guard.

## Current status

Native and protected one-stop CI: `.github/workflows/v143-rebuild-passenger-gate.yml`. Early R303 alternate: `.github/workflows/v143-r303-early-originator.yml`. Their job completion status must be examined before an acceptance decision. Do not merge PR #46 or update `web/schedules.json` as part of this reconnaissance phase. The original 1,286-leg canonical in `data/schedules/schedule_7_v1_4_3_draft` remains the working acceptance checkpoint.

## Reassembly validation results

GitHub Actions run **39695610829** tested the combined R313 JAX and R338 RDU experimental extension, **1,290 flights / 191 routes** (four additional flights over the preserved 1,286-flight draft), no extra aircraft:
- Native structural PASS, overnight PASS, fixed gates PASS, planning PASS, **zero effective operating errors** after correction of R338 PHF→SAV #1493 departure bank to PHF-M5.
- `scripts/v143_rebuild_guard.mjs` checks **3,519 directional-market/model combinations** (>8 daily O-D; geographically reasonable and unrestricted), **zero losses of one-stop-or-better coverage**.
- Whole-network itinerary audit `scripts/v143_seven_route_rebuild_audit.mjs`, run **39695957909**, records geographically reasonable markets: **3 gained, 0 lost, 22 faster, 14 slower**. Unrestricted model: 6 gained, 0 lost, 30 faster, 17 slower. Representative faster trips: BNA→RDU 317→188min (122.4 O-D/day), BWI→RDU 227→138 (57.8), PVD→RDU 284→173 (42.2), MSY→CLT 256→224 (75.2). Representative slower trips *with stop count preserved*: BDL→SAV 296→341 (22.6), CLT→AVP 173→254 (11.9), HPN→SAV 320→365 (10.4). This is permissible under user's stated floor, not consequence-free.
- This candidate remains **experimental**, not promoted to saved v1.4.3 draft, pending further seven-route holistic improvement and independent release regressions.
- Separate R303 earlier BHM→MCI originator exploration `scripts/v143_r303_early_originator.py`, run **39695402977**, produced no full native-pass candidate across examined SGF/OMA/DSM/TUL mini-turn combinations. R303 PNS inbound afternoon bank remains a protected network constraint.

Further R345 high-demand exploration: the original short CLT–TYS/AVL/GSP rounds yielded negligible connecting gains, but CLT–BWI has ~235.8 combined daily O-D and CLT–PIT ~98.5. `scripts/v143_r345_bwi_coordinated.py` now tests advancing JAX→SYR and SYR→CLT ~18–25 minutes to free a long enough CLT–BWI/CLT–PIT turn **without moving PHF→GSP**; native screening results pending as of report update.

## R345 high-demand CLT opportunity identified

Broadening the demand screen beyond the previous low-demand local CLT loops reveals **CLT↔BWI 235.8 daily two-way O-D passengers**, CLT↔PIT 98.5 and CLT↔JAX 80.9. R345 currently has SYR→CLT arriving 13:07 and CLT→PHF departing 17:10, with no permitted disruption to aircraft line endpoints.

The first CLT–BWI/CLT–PIT technical insertion screen advances JAX→SYR and SYR→CLT by 18–25 minutes, creating room for two new 70-minute legs (based on preliminary block assumption) within CLT before the original PHF departure. **Gates and structural/overnight continuity pass, but SYR hub-bank alignment fails**: moving original #1408's SYR arrival earlier than 10:30 exits the SYR-B3 inbound window beginning at 10:30. Thus these earlier-departure options are **not valid** as tested; no service accepted. Native test `scripts/v143_r345_bwi_coordinated.py`, run 39696225077.

Revised `scripts/v143_r345_bwi_bank_fit.py` preserves SYR-B3 by moving #1408 only 6–8min earlier, #1306 8–10min earlier, and examining 62–66min CLT–BWI flight blocks. **Requires validation both for real block feasibility and fixed airport gates**; user-authorized retiming sacrifices still cannot violate bank/turn limits or >8 passenger one-stop protections. This is a more compelling potential reassembly than low-demand CLT–TYS/GSP/AVL excursions.

## R345 bank-safe high-demand insertion — latest validation

October 21, 2026 continuation. `scripts/v143_r345_bwi_bank_fit.py` run **39696666412** proved a native-valid insertion with revised station clock times and SYR-B3-safe upstream retiming: existing #1408 JAX→SYR **08:02–10:30** (-8m); #1306 SYR→CLT **11:10–12:57** (-10m), creating CLT→BWI **13:37–14:42** and BWI→CLT **15:22–16:27**, followed by unchanged CLT→PHF #1382 at 17:10. A 65-minute block per BWI leg is assumed; no preexisting CLT–BWI flight exists in schedule 7 to confirm empirical block. This is a crucial feasibility assumption and must be reviewed before release.

The changes were inserted into `scripts/v143_seven_route_rebuild_candidate.py` along with the previously tested R313–JAX and R338–RDU additions. GitHub Actions run **39699254347**: candidate **1,292 flights / 191 routes / 17 lines**, structural PASS, overnight PASS, fixed gates PASS, planning PASS, **zero effective operating errors**. New user-specific guard `scripts/v143_rebuild_guard.mjs` checked **3,519 above-8-pax/day directional market/model instances; zero one-stop-or-better coverage losses**. Network audit vs accepted 1,286-flight draft finds **3 gained reasonable connections, zero lost, 36 faster and 28 slower** (longer times are acceptable under current instructions). For the primary R345 local market, CLT→BWI and BWI→CLT become nonstop at 65 minutes; underlying O-D totals **235.8 passengers/day across directions**. Preserve the accepted 1,286-flight canonical as revert point; experimental 1,292-flight builder is separate and not published.

Caveat: this construction demonstrates **cross-route cumulative compatibility** rather than a completed redistribution of already existing flights between all seven routes. R303, R316, R319 and R339 have not been successfully reassembled, despite screening. Further route reassignment must be genuine assignment moves with valid aircraft cycles, not superficial relabeling. Do not imply the whole seven-route overhaul is finished. Verify block time and direction-specific passenger capacity before accepting R345 into v1.4.3 main draft.

## Continued AH actual flight-pair exchange (October 21, 2026)

Following the R345 CLT–BWI addition, the 1,292-flight staged builder passes all native, fixed-gate, overnight and planning checks. New reproducible alternative `scripts/v143_cumulative_ah_exchange.py` then **moves flight pairs, not just retimes**:
- R317 (AH day 7) hands off SYR–RFD #2103 and RFD–SYR #2104 to R319 (AH day 9), retimed as **SYR→RFD 12:00–12:54, RFD→SYR 13:54–16:48**.
- R319 hands off SYR–PHF #1951 and PHF–SYR #1952 to R317, retimed as **SYR→PHF 18:10–19:35, PHF→SYR 20:15–21:40**.
- All route-day originators, terminators, line identities and aircraft connections are retained; existing SYR→PIT on R317 at 22:25 and SYR→BWI on R319 at 18:55 are protected. Native screening `scripts/v143_ah_exchange_r317_r319.py` run 39709253007 confirmed the above times are the legal bank/spacing option.
- Cumulative candidate `schedule_7_v1_4_3_ah_exchange_candidate` is 1,292 flights, **zero effective operating errors**, structural PASS, gates PASS, overnight PASS, planning PASS, and **zero protected >8-pax one-stop losses across 3,519 directional-market checks** (GitHub Actions 39709466131).
- Comparative passenger network audit vs the same 1,292-flight candidate *without the exchange* (GitHub Actions 39709680467): reasonable model **0 gained, 0 lost, 45 faster, 21 slower**, no new flights. Major benefits MDT→RFD 375→254m (46.2 O-D pax/day), RFD→ROA 619→465 (19.6), HPN→MYR 406→325 (17.1); costs PWM→RFD 224→264 (41/day), HPN→RFD 209→214 (35.6), RFD→BTV 217→248 (30.3), HVN→RFD 209→299 (14.6), **RFD→HVN 204→363 (14.3)**.
- Although legal under the user's explicit >8-pax stop-count guard, this swap **does not create any additional flights**, and only reallocates CRJ700 utilization from AH day 7 R317 to AH day 9 R319. The 90–159-minute deterioration for HVN–RFD is too large to assume commercial acceptance without further reciprocal improvements. **Do not promote exchange automatically**. Save it as tested experimental alternative; the more attractive next exchange should free aircraft time for an actual additional flight while preserving demand.
- The upstream 1,292-flight candidate (R313 JAX, R338 RDU, R345 BWI) remains separate and native/coverage-valid. The original accepted 1,286-flight v1.4.3 canonical remains the hard revert point; no changes on main.



## October 22 resumption — workflow suppression and next reassembly screen

The user approved resuming development after excessive GitHub notification traffic. Development PR #46 remains **closed but unmerged** and its head branch remains the primary store of all v1.4.3 files. Audited all **34 v1.4.3 research workflow definitions**: each now uses `workflow_dispatch`, not automatic pull-request/push triggers. Historical release workflows on this branch are manual. Routine `ci.yml` push events have been scoped to `main` only, preventing each research-branch commit from invoking another routine CI run. None of this touches production `main`. Research workflows remain available for deliberately selected checks, with manual workflow configuration and scripts preserved.

Current state protected:
- Published v1.4.2 remains default on `main`.
- Accepted reproducible v1.4.3 draft is **1,286 flights**; never alter it in-place.
- Separate `scripts/v143_seven_route_rebuild_candidate.py` builds **1,292-flight** native- and >8-passenger coverage-valid R313/R338/R345 concept.
- `scripts/v143_cumulative_ah_exchange.py` documents another 1,292-flight *zero-net-flight* R317/R319 pair exchange, operationally valid but commercially mixed. Retain for fallback, do not promote automatically.

**Direct exchange feasibility screen performed on the current 1,286-flight schedule**: enumerated 407 existing, same-day two-leg out-and-back pairings with a ground turn <=180m and segment length <=480m. Compared every pairing to the 16 interior holds >=90m across the seven user-target routes, requiring same starting station and same aircraft line as well as 40-minute turns before/after the transferred pair (80m slack). **No intact pair is feasible in a target hold.** This is only a *necessary-window check* and not an impossibility proof for comprehensive line rebuilds or retimed flight exchanges. It confirms that a productive cross-route transfer requires retiming adjacent legs, replacing another flight pair, and/or changing the placement of the turn across days.

Next targeted reconstruction:
1. **AH**: evaluate R313/R316/R319 together, and adjacent AH days R317/R318 if needed to preserve cyclic aircraft continuity. Aim to free a single long bank-compatible window, rather than shifting the R317 RFD pair to R319 without adding utilization; review HVN↔RFD timing losses in the previous experiment.
2. **AK**: R338/R339 adjacent SAV handoff and the PHF-SAV #1493 16:15 flight's Northeast-bank protection are constraints for any flight replacement.
3. **AA**: protect PNS→MCI #1346 near the existing inbound connections; R303 early-return options produced meaningful PNS penalties. Rebuild with bank coverage replacement, not just advancing it.
4. **AS**: preserve R345 CLT-BWI proposed connection with separately verified 65-minute block before merging it into any accepted candidate.

A move is rejected if either native hard-operating validation fails or any >8-pax directional market loses all 0/1-stop paths; timing-only deterioration can be traded transparently. Manual checks are required when a new candidate is actually ready, not on every code edit.


## Continued AH swap development — October 22

The 34 v1.4.3 research workflow files were verified as manually triggered and routine development-branch pushes were excluded from `.github/workflows/ci.yml`. PR #46 stays closed; accepted and experimental canonical files are unchanged.

A scan of existing 407 physical out-and-back pairs against 16 holds on the seven focus routes showed no **unmodified, same-line** pair would fit directly in another current hold with 40-minute turns on both sides. Therefore further optimization must alter adjacent timings and/or exchange pairs across aircraft-days.

Developed a more promising *reciprocal* flight-pair exchange on neighboring **AH line days 8 and 9**, rather than the prior R317/R319 exchange that severely delayed HVN→RFD:
- R318 (PIT→SRQ, AH day 8) would receive R319's SYR→PHF #1951 and PHF→SYR #1952 in its early Syracuse gap before existing SYR→SRQ 11:20.
- R319 (SRQ→ABE, AH day 9) would receive R318's SYR→BTV #2189 and BTV→SYR #2190 in its SYR midday gap before existing SYR→BWI 18:55.
- Both route endpoints and their day-to-day aircraft handoffs remain *planned* unchanged; flight numbers, market flying and fleet size are conserved, with no proposed new flights in this first reciprocal swap.
- Mechanical screening of exact flight station order and minimum 40-minute aircraft turns found **14 candidate clock combinations**. One example: R318 SYR→PHF 06:20–07:45 and PHF→SYR 08:30–09:55; R319 SYR→BTV 12:30–13:22 and BTV→SYR 14:07–14:59.
- `scripts/v143_ah_btv_phf_swap.py` reproduces the alternatives with full structural, overnight, airport gate and operating checks, and writes a separate candidate **only on a full native pass**. `.github/workflows/v143-ah-btv-phf-swap.yml` is strictly `workflow_dispatch` and additionally invokes the >8-pax market guard if the candidate is produced.
- **This is a queued-for-manual-validation proposal, not a validated swap.** The automatic GitHub runs remain disabled to prevent another flood of email. A successful native check is required before a network effect comparison and before accepting anything into v1.4.3.


## October 22: AH pair-transfer constraint and notification containment

The tested transplant of R319's existing SYR–PHF–SYR #1951/#1952 into R316's SYR hold cannot work as an isolated reassignment: R316 has just **123 minutes** between CLT→SYR arrival at 11:12 and SYR→BNA departure at 13:15; the currently scheduled SYR→PHF→SYR turn spans **215 minutes** from 13:15 to 16:50, including the PHF ground turn. The initial AH transfer test was blocked by an unrelated Python formatting syntax error; that syntax has been repaired in `scripts/v143_ah_pair_exchange_screen.py`. Even with corrected code, the transfer must be coupled to moving or retiming SYR→BNA #1335 and downstream BNA→PHF #1294 / PHF→BNA #1292, and must preserve the overnight endpoints and >8 pax directional-market one-stop coverage. Do not move #1951/#1952 into the accepted canonical on its own.

To contain excessive GitHub notifications, PR #46 is **closed but unmerged**; the branch and all saved candidate data remain. On the research branch, broad push-triggered `v143-utilization-screen`, `v143-native-turn-screen`, `v143-combined`, `v143-save-draft`, and stale `release-v142` were changed to manual dispatch. The targeted `v143-ah-single-run` diagnostic was also converted from temporary path-scoped push to manual. Do not reopen the PR before rationalizing all remaining `pull_request` research workflow triggers. Do not move the production schedule on main.

**Conserved snapshots:** accepted `data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json` (1,286 flights); separate experimental 1,292-flight cumulative builder `scripts/v143_seven_route_rebuild_candidate.py` (R313/R338/R345 additions), with native validation and 3,519 protected passenger-market/model checks already reported passing. Release still v1.4.2.


## October 22 — actual AH line R319/R320 reassignment, staging only

A concrete **cross-day existing-flight reassignment** is now scripted in `scripts/v143_ah_day9_day10_exchange.py`. This addresses the limitations of the earlier exploratory R316 test, whose script had a syntax error before validation. The R319→R320 exchange is staged on top of the independently native-valid **1,292-flight** experimental builder; **neither accepted 1,286-flight draft nor published main has been changed**.

**R319 AH day 9:** Remove the existing SYR–PHF #1951 / PHF–SYR #1952 pair from this aircraft-day. Keep the SRQ→SYR morning flight and SYR→BWI→SYR→ABE evening flights. Use the larger SYR gap for a proposed SYR→BNA **11:30 ET–12:34 CT** and BNA→SYR **13:14 CT–16:18 ET**. This adds a new high-value BNA frequency instead of merely shifting idle time.

**R320 AH day 10:** Accept the same *existing flight IDs* #1951/#1952, preserving both SYR–PHF directional flights and their original markets, not eliminating a one-stop connection. To fit the pair, retime #1302 SRQ→SYR to **09:40–12:36** (42-minute turn after the previous SRQ inbound), #1951 SYR→PHF to **13:16–14:41**, #1952 PHF→SYR to **15:26–16:51**, #1307 SYR→CLT to **17:31–19:18**, and #1102 CLT→BDL to **19:58–21:50**.

Preliminary direct timetable-continuity calculations (not full native operating checks) show route R319 transitions/turns **49 / 40 / 157 / 40 / 40 min**, preserving SRQ originator and ABE terminator, and R320 turns **40 / 42 / 40 / 45 / 40 / 40 min**, preserving ABE originator and BDL terminator. Hence full AH cyclic day boundaries remain geographically intact. Two relocated *existing* flights are not deleted or duplicated. In the staged concept the total becomes **1,294 flights** (+2 new BNA flights relative to the 1,292 experimental builder, and +8 relative to the accepted 1,286 draft).

**Crucial unvalidated matters:** Syracuse and especially Nashville bank assignments; fixed physical gates; flight-block applicability on new SYR–BNA flights; maintenance; the strict >8 pax/day one-stop floor in both itinerary models; and any adverse passenger timing effects of moving SRQ→SYR and CLT→BDL. The script performs the native validators and emits a separate candidate artifact **only if all checks pass**. Then run `node scripts/v143_rebuild_guard.mjs data/schedules/schedule_7_v1_4_3_ah_reassignment_experiment/canonical_schedule.json` plus a commercial itinerary comparison. There is **no automatic workflow attached**, and no claim of full validation yet. A failure should be resolved within the experiment, not silently included in the accepted draft.

Progress interpretation: This is a *real proposed existing-flight/aircraft-day exchange*, unlike the preceding additive-only reconstructions. Do not merge PR #46 or advance `web/schedules.json` until full validation and release authorization.
