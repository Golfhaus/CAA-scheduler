# Schedule 7 v1.4.3 — R338 and R345 added to seven-CRJ700 reconstruction

Date: October 21, 2026. Retain the pre-existing 1,286-flight, 191-route, 17-line v1.4.3 draft (including 14 R177/R178/R359 additions) unchanged pending native/commercial validation. Published main remains v1.4.2.

## R338 (AK day 1)

Flight-day: PHF–SYR–PHF–PVD–PHF–SAV–JAX–SAV. Two conspicuous stands: PHF **13:13–16:15 (182 min)** and SAV **17:41–20:00 (139 min)**. Existing late SAV→JAX→SAV 20:00–22:10 is important to its day 2 SAV originator and must be retained absent complete cyclic rebuild.

The PHF→SAV #1493 16:15–17:41 separates those holds. Moving it earlier consolidates more time at SAV; moving later consolidates at PHF. Neither isolated shift increases flying, and any retiming must preserve existing PHF bank connections and the 20:00 SAV→JAX turn. Screen: `scripts/v143_r338_sav_hold_retime.py` and `.github/workflows/v143-r338-hold.yml`.

Physical minimum 40-minute turns imply the SAV hold 139 minutes is too short for a meaningful two-leg side turn using even 40–45-minute blocks. PHF hold 182 minutes has at most 62 minutes total for two legs under conservative bookend turn requirements; an ordinary nearby 40+40 side turn fails. A genuine improvement requires exchanging an existing scheduled segment (e.g. #1493/#2127/#2128) with another valid AK/PHF/SAV route-day while protecting R339's SAV start and R338's SAV terminator.

## R345 (AS day 6)

Flight-day: SDF→JAX→SYR→CLT→PHF→GSP→PHF. CLT ground hold **13:07–17:10 (243 minutes)** is exploitable. The morning SYR→CLT #1306 and evening CLT→PHF #1382 remain completely unchanged in the proposed short-turn approach.

Native isolated candidate screen `scripts/v143_r345_clt_turn_screen.py` (GitHub Actions run 39691750365) recorded passing **structure, overnight, physical gate and zero-effective-error operating validation** for:
- CLT–TYS–CLT 14:00–16:30; 110 extra block minutes; estimated **15.5 combined daily two-way CLT–TYS O-D**.
- CLT–GSO–CLT 14:00–16:10; 90 block minutes; 7.5 combined daily O-D.
- CLT–GSP–CLT 14:00–16:00; 80 block minutes; 7.4 combined daily O-D.
- CLT–AVL–CLT 14:00–16:10; 90 block minutes; 4.9 combined daily O-D.
- CLT–CAE–CLT 14:00–16:10; 90 block minutes; 4.8 combined daily O-D.
- CLT–ROA–CLT and CLT–TRI–CLT also passed preliminary native screening but have thinner local demand.

Route lengths are estimated from existing published market block times where available, otherwise conservative distance-based block assumptions. Screening terminated after these successful options with an inactive FAY airport metadata lookup; passing options listed above remain valid. All proposals need the net passenger-itinerary audit, secondary available seat/capacity assessment and released timetable regression before draft inclusion. **Do not select solely by block minutes**: CLT–TYS is the first local O-D contender but its additional connecting demand is the deciding metric. See `scripts/v143_r345_commercial_screen.mjs` and workflow `v143-r345-commercial.yml`.

## Shared AH reconstruction (R313, R316, R319)

Prior preserved analysis in `docs/schedule_7_v1_4_3_crj700_reconstruction_screen.md`: R313 CLT–JAX–CLT tested zero native errors but its CLT→PHF retime harms CLT→AVP; shifting PHF→AVP later causes even larger SFB/RFD→AVP regressions. R316 BNA→PHF hold relocation does not yield legal PHF excursions before PHF→BNA #1292; R319 earlier SYR→PHF failed physical gate capacity. These candidates remain **experimental and excluded from canonical**, not waived.

R303 PNS→MCI early retimes with extra OMA or DSM flying are gate- and structural-feasible, but cause substantial loss to PNS–PIE and PNS–RDU and slower PNS–RFD/DAL journeys; commercial reconstruction must preserve those feeds before introduction.

## Next gate

Compare marginal network outcomes for the gate-valid R345 options. Select the best meaningful-demand connection gains, then construct a cumulative candidate with exactly two more R345 legs and check all native rules, planning snapshot and benchmark vs v1.4.3's 1,286-flight draft. Continue R338's coupled flight-exchange analysis after checking PHF→SAV retiming screen. Do not publish any change to main.
