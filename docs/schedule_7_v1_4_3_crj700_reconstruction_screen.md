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
