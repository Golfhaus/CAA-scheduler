# Schedule 7 v1.4.3 — CRJ700 underutilized route reconstruction screen

**Unpublished working analysis, October 21, 2026.** Preserve all 14 previously accepted-to-draft R177/R178/R359 additions. Working canonical is 1,286 flights, 191 routes, 17 aircraft routing lines and zero effective operating errors. No changes to `main`. Baseline current published `schedule_7_v1_4_2`.

## Exact hold audit
From `scripts/v143_five_crj700_holds.py`, CI run 39685374215. All times local station clocks; holds are actual aircraft idle intervals.

| Route (line/day) | Biggest holds | Current route |
|---|---|---|
| **R339 AK/2** | BHM **182m** (04:43–07:45); PHF **179m** (13:16–16:15); SAV **112m** (09:58–11:50) | SAV–BHM–SAV–PHF–CHS–PHF–CHS |
| **R303 AA/3** | PNS **210m** (12:40–16:10); MCI **139m** (08:16–10:35); MCI 95m (18:15–19:50) | BHM–MCI–PNS–MCI–PNS |
| **R313 AH/2** | CLT **208m** (06:22–09:50); PHF **179m** (10:56–13:55) | BDL–CLT–PHF–MSY–PHF–SAV |
| **R316 AH/5** | BNA **184m** (14:19–17:23); SYR **123m** (11:12–13:15) | PVD–PHF–CLT–SYR–BNA–PHF–BNA |
| **R319 AH/9** | SYR **154m** (10:41–13:15); SYR **125m** (16:50–18:55) | SRQ–SYR–PHF–SYR–BWI–SYR–ABE |

At strict bookend turn assumptions, a new two-leg side excursion needs 40 minutes before first flight, 40 at destination and 40 on return. A demand screen using conservative block-time estimates (`scripts/v143_crj700_demand_hold_screen.py`, run 39685560933) found **no meaningful-demand roundtrip fitting inside the untouched holds**. This is a negative *screen* rather than proof every possible short pairing is impossible: candidate flight times, physical station gates and bank effects must be validated individually.

## Highest-priority holistic rebuild studies

**A. R313: rebuild around CLT and PHF; highest prospective time recovery.** The 208-minute CLT stand and 179-minute PHF stand are adjacent on one route (separated by CLT–PHF). Evaluate moving flight 1379 CLT–PHF earlier and reallocating the released CLT/PHF period to a useful bank-fed turn. Preserve origin BDL and terminator SAV. If pursuing replacement of PHF–MSY–PHF pair (#1270/#1278), ensure MSY service is reassigned to another operationally valid aircraft-day with gate/stand capacity and no lost premium connections. Do not simply discard 2 flights.

**B. R303: reshape the PNS and MCI mini-banks.** This route makes two MCI–PNS traversals and ends PNS. Reconstruct the 210-minute midday PNS hold by shifting #1343 MCI–PNS / #1346 PNS–MCI, or exchange a PNS departure/arrival with another PNS-serving aircraft-day. Earlier evening MCI return may enable an additional MCI bank service. Preserve BHM originator, PNS terminator and bidirectional MCI/PNS frequency where demand requires.

**C. R316: coordinate BNA–PHF and SYR bank timing with other AH line days.** The 184-minute BNA midafternoon hold looks attractive but the airport has a tight two-gate inventory and was difficult to optimize in v1.4.2. Try swapping BNA–PHF and PHF–BNA flying (#1294/#1292) with other existing services rather than force a new BNA turn into the existing hold. Preserve PVD originator, BNA terminator, fixed gates and routing-line cycle.

**D. R339: split morning BHM and afternoon PHF stands.** There are two ~3-hour waits at separate banks. Retiming the BHM–SAV departure (#2068) and SAV–PHF #1496 may align to stronger BHM/PHF bank windows; use a flight pair borrowed from another nearby SAV/BHM/PHF line only after accounting for the donor line's continuity and demand. The evening CHS–PHF–CHS sequence has back-to-back 40-minute turns and no room for insertion.

**E. R319: focus on SYR–PHF–SYR and late BWI bank.** The two short SYR stands alone cannot fit a 40/40/40 short round trip of meaningful demand. Consider moving the SYR–PHF–SYR pair (#1951/#1952) to another SYR-based day and using the enlarged block for an alternate high-value destination; preserve SRQ originator and ABE terminator, SYR bank feed, and the 40-minute BWI and final SYR turns.

## Critical constraints and follow-up

- R313, R316, R319 all occupy distinct days of **line AH**. Flight redistribution between days may break overnight handoffs even though each source station is attractive; reconstruct the full AH cycle, not just route-internal turns.
- R303 is AA and R339 AK, so a proposed swap across these lines requires a valid interline cyclic reorganization, never arbitrary transfers.
- Compare every rebuilt route against published v1.4.2 and the preserved v1.4.3 candidate for demand-weighted coverage, realistic flight block times, bank alignment, gate and stand capacity, curfews, RON, and each line's length.
- Do not remove any existing route or alter its station endpoints unless reconstituting cyclic continuity with all lines.
- Full canonical reconstruction, gate assignment and native validation for swaps are **not yet done**. This document is a shortlist and identified hold anatomy, not a claim that specific rebuilds have passed.

Next screening priority: R313 and R303, followed by R316, R339, R319; measure cost of transferring a specific leg/pair as well as the resulting freed minutes, rather than ranking idle time alone.


## Native hold relocation screen — first results

Run 39685967057, `scripts/v143_crj700_holistic_retime_screen.py`, on the full 1,286-flight v1.4.3 draft.

- **R303** advancing #1346 PNS→MCI from 16:10 to 13:20, 13:30, 14:00, 14:30 or 15:00 **passes physical gates, route structure and overnight continuity** but fails only arrival bank alignment. #1346 currently assigned MCI-B9 (18:05–19:05). At 14:30 departure it would arrive MCI 16:35, inside MCI-B8 (16:25–17:25). Reassign that arrival to B8, run network impact, then examine resulting 16:35–19:50 MCI hold (195m) for productive replacement flying. It does NOT by itself add utilization.
- **R316** advancing #1294 BNA→PHF from 17:23 to 15:00–16:30 **passes physical gates, structure and overnight**; fails only PHF arrival bank alignment. Original PHF-B7 is 20:05–21:05. At 15:30 departure, expected PHF arrival is 18:12 in PHF-B6 (17:45–18:45), generating a 163m PHF wait ahead of #1292 PHF→BNA at 20:55. Reassign to B6 and audit connection losses before any swap; moving a stand alone does not create new flying.
- **R339** moving #2068 BHM→SAV from 07:45 to **05:50 or 06:15** passes all native checks without a bank change, but shifts the idle period to SAV. That city has relatively few candidate aircraft exchanges, so defer any retiming until productive follow-on legs are proven. Moves to 06:40/07:00 cause BHM gate inventory violations.
- **R313** moving CLT→PHF #1379 earlier than 08:30 causes PHF gate congestion and CLT–PHF spacing errors. At 08:30 gates pass but pairing spacing and bank alignment still fail. No accepted change.
- **R319** moving SYR→PHF #1951 earlier to 11:30–12:15 causes PHF fixed-gate/stand errors and network bank misalignments. No accepted change.

**Conclusion:** The highest-value next step is *coupled* flight reassignment/rebuild of R303 and R313, not standalone retiming. Do not incorporate the isolated R303/R316/R339 timing shifts into the canonical yet: they merely transfer idle time and could disrupt existing high-demand connections. Any paired change must produce net additional scheduled flying and pass whole-network coverage and bank regressions.


## Detailed R303/R313 construction findings (continued)

**R303: concrete additional round trips are physically possible, but commercial losses matter.** Moving PNS→MCI flight #1346 from 16:10 to **13:20–15:25**, reassigning its MCI arrival from B9 to B7, allows the following zero-error, structural/overnight/gate-valid extensions before the preserved MCI→PNS 19:50 terminator:
- MCI–OMA–MCI 16:25–18:45 (100 additional flying minutes) or 16:35–18:55;
- MCI–DSM–MCI 16:25–18:55 (110 additional flying minutes).
Source: `scripts/v143_r303_mci_turn_screen.py` GitHub Actions run 39689048972.

Independent geographic reasonable itinerary audit: the OMA alternative yields six new reasonable markets, 27 faster and **six slower**; specifically PNS→RFD (59.7 O-D/day) +5min, PNS→DAL (43.3/day) +6min, and smaller PNS markets slower. More inclusive audit also loses PNS→PIE direct eligibility (23.2 O-D/day; revised shortest +90min) and worsens PNS→RDU (18.1/day) substantially. DSM alternative yields five new reasonable markets, 17 faster and **six slower**, also harming PNS→RFD and PNS→DAL and PNS→PIE nongeographic service. **Decision: do not yet incorporate R303 into the accepted v1.4.3 canonical**. Need a coordinated replacement PNS feeder or a return departure closer to the original that preserves high-demand PNS connections. See `scripts/v143_r303_commercial_audit.mjs`, workflow `v143-r303-commercial.yml`.

**R313: legal early CLT–JAX turn found.** Replace long early CLT stand with CLT→JAX **07:02–08:13**, JAX→CLT **08:53–10:04**, and move the existing CLT→PHF #1379 from 09:50 to **10:50–11:56** (PHF-M12-V141 arrival bank). Preserves BDL originator, all MSY/PHF flying, and SAV terminator. All native structural, overnight, fixed gate, and operating checks **pass with zero effective errors** (GitHub Actions run 39689486666), two added CRJ700 legs. Candidate should be judged by commercial tradeoffs, not physical feasibility alone.

The R313 JAX-only passenger audit finds 2 geographic reasonable coverage gains, 11 faster and **two slower** with no lost reasonable markets. The nontrivial adverse market is CLT→AVP (11.9 O-D/day) 173→254m (+81), because PHF→AVP #1745 departs 11:35 before rebuilt #1379 reaches PHF at 11:56. Major improved markets include MSY→CLT 256→224m (75.2/day), EYW→CLT 316→279m (17.8/day), VPS→CLT 241→186m (15.8/day), ECP→CLT 301→254m (13.1/day). Source: `scripts/v143_r313_jax_commercial.mjs`, GitHub Actions run 39689688204.

**Attempt to repair CLT→AVP by moving #1745 PHF→AVP 55min later**: its new 12:30→13:38 timing, with PHF-M12 arrival/departure assignments and a 47min AVP turn, passes structural, gates, overnight and operating validation with **zero effective errors** after correcting pair IDs (run 39690219314). But the whole-network audit then finds **10 slower directional markets**, including SFB→AVP 218→273m (29.5 O-D/day) and RFD→AVP 218→273m (16.2/day), outweighing the narrow CLT→AVP recovery. **Reject this coupled AVP retiming** (run 39690285454). The unmodified JAX-only concept is the better tradeoff but still merits explicit loss review.

**Governance and next:** preserve the accepted 1,286-flight v1.4.3 canonical unchanged. R303 OMA/DSM and R313 JAX candidates are reproducible **experimental analyses**, not accepted additions. Further reconstruct specific PNS hub feeds or find a second aircraft for CLT→AVP restoration without delaying the widely connected PHF→AVP flight. Study R316 next, with its movable BNA hold and AH line relationship to R313. No main publication authorized.


## Follow-up: R316 PHF turn and lower-disruption R303 screens

**R316:** run 39690870335 tested earlier BNA→PHF #1294 departures at 15:30, 16:00 and 16:30 with a proposed PHF–BWI/RDU/SAV/CLT out-and-back ahead of fixed PHF→BNA #1292 at 20:55. **No turn satisfied the complete bookend-turn and block-time window**, even before airport validation. Shifting #1294 earlier may relocate the stand but does not create physical space for a productive round trip while preserving #1292. No changes accepted. Next strategy: replace a segment or use a two-route swap that enlarges the PHF window.

**R303:** run 39690980953 screened flight #1346 PNS→MCI departures 13:20, 13:50, 14:20 and 15:00 against retained v1.4.3 (without new round-trip additions). Every timing introduces **six slower geographically reasonable directional journeys** and persistent PNS→RFD (59.7 O-D/day; +5m) and PNS→DAL (43.3/day; +6m). Under all-available itinerary audit, advancing to 13:20 also worsens PNS→PIE (23.2/day; +90m) and PNS→RDU (18.1/day; +170m); 15:00 still degrades those markets and PNS→BNA. Therefore even more conservative retiming **does not eliminate the commercial loss**. The earlier MCI–OMA/DSM possibilities are physically feasible but not suitable for immediate acceptance without PNS feeder reconstruction.

**Disposition:** remain at the verified 1,286-flight v1.4.3 draft, with no new CRJ700 edits adopted. Prioritize swaps that explicitly preserve PNS connection banks and existing PHF/AVP traffic, not simply transferring a stand. R313 CLT–JAX remains a native-pass experimental candidate, but delaying #1745 PHF→AVP is rejected because it harms SFB→AVP and RFD→AVP. Publish nothing until user authorization and full regression checks.
