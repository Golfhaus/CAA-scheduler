# Schedule 7 v1.3.2 maintenance repair draft

Prepared October 14, 2026 from published v1.3.1 commit `d0b728cab36c0d1f3e04d5140d755c8760b3809b`. The user authorized repairing the maintenance validator and AC/AO/AQ rotations. Publication has not been authorized; main and the app default remain v1.3.1.

## Validation defect

The old rolling RON check treated a cycle without any eligible overnight as a finite absence equal to its length. A one-day cycle was thus allowed to repeat ELP or TYS forever, while AC's ten-day cycle also passed without a base RON. The corrected check reports an unbounded absence whenever a repeating cycle has zero eligible RONs. Its evidence records cycle length, zero target RON count and an explicit unbounded flag rather than a misleading one-day/ten-day maximum.

The existing finite-run policy and standing one-day grace are retained: the metric counts consecutive non-target overnight days, with a normal limit of ten and grace of one. The pass message now describes that metric accurately. No airport is newly designated an MX base, no policy waiver is added, and no overnight turn is treated as maintenance merely because the aircraft visits a hub during the day.

Corrected validation of the published v1.3.1 input reports exactly three maintenance errors: AC, AO and AQ. Its stored zero-error report is historical evidence of the old check, not proof of current compliance. Released v1.3.1 artifacts are not rewritten.

## CRJ700 rotation repair

Absorb R350 (former AO) and R351 (former AQ) into AL. Every CRJ700 flight keeps its original clock, market, flight ID, pairing and aircraft type.

- F2156 MCI–ELP moves from R350 to the end of R336. R336's MCI arrival at 21:35 leaves 58 minutes before its 22:33 ELP departure. R336 then terminates ELP at 23:49; R350 starts there at 04:55 and now terminates **MCI at 21:43**, before R337's next-day MCI originator.
- Exchange the 19:25 JAX terminal flights: F1352 JAX–TYS moves to R331, and F1454 JAX–GSO moves to R351. R331 now ends TYS, R351 begins TYS and ends GSO, and R332 starts GSO. R351's original JAX/SFB flights, including F1437 at 16:13, are unchanged.
- Move R338–R341's PHF→SAV→CHS→CLT→MSY segment to AK, exchange AK's R321 PHF→MSY day into AL, and transfer the closed R327 PHF day from AK to AL. This balances both lines at **12 days**, with legitimate maintenance overnights.

AL becomes `[330, 331, 351, 332, 333, 334, 335, 336, 350, 337, 327, 321]`; AK becomes `[338, 339, 340, 341, 322, 323, 324, 325, 352, 326, 328, 329]`. AO and AQ disappear as separate line labels; their flying still operates daily. These are cyclic tail assignments, not flights that operate once every twelve days.

## CRJ200 rotation repair

Reassign R166's closed evening SYR–ROC–SYR turn, F2039/F2040, to R108. R108 returns from BTV to SYR at 18:52, flies that unchanged turn and now terminates **SYR at 21:34**. R166 reaches SYR from CAK at 18:56 and instead takes F1817 SYR–MDT, with a one-minute delay for the required 40-minute turn.

Reassign F1904 DAY–TOL to the end of R156. Its 20:28 DAY arrival requires a 40-minute turn, so F1904 moves 43 minutes later. R110 now terminates **DAY at 19:42**. Re-close AC and AM around those handoffs:

- AC: `[101, 102, 103, 104, 105, 106, 107, 108, 167, 156]` — ten days, with the new SYR RON.
- AM: `[157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 109, 110]` — twelve days, with the new DAY RON.

AM explicitly uses the existing standing grace: **eleven consecutive non-target overnights between its DAY visits**. The validator flags this as a warning; it is not silently recorded as ordinary ten-day compliance. All other lines avoid the grace warning.

| Flight | Old times, ET | Draft times, ET | Reason |
|---|---|---|---|
| F1817 SYR–MDT | 19:35–20:31 | **19:36–20:32** | 40-minute turn after F1671 |
| F1904 DAY–TOL | 20:25–21:09 | **21:08–21:52** | 40-minute turn after F2072; existing DAY-B9 |

Those are the only clock changes. No flight is added or removed, and no additional aircraft is required. MDT and TOL retain their terminating arrivals and next-day originators.

## Passenger and physical impact

The combined repair preserves every raw and geographically suitable existing itinerary choice, loses no direct/one-stop market and retains all accepted northeast PGD/DAB/FLL/PIE/SFB/SRQ coverage. It introduces an incidental zero-demand BHM→TOL one-stop option, which is not used as a demand justification for the repair.

There are **57 slower geographically suitable fastest journeys**: 23 increase by one minute to MDT, and 34 increase by 43 minutes to TOL. Seven geographic fastest journeys improve. Raw timetable counts are 64 slower and ten faster. These are documented elapsed-time tradeoffs; the repair does not claim zero passenger impact.

An earlier RFD round trip was tested to keep F1904 at 20:25. It would move DAY–RFD to 16:24 and RFD–DAY to 17:26, but it fails DAY's fixed 16-gate inventory by leaving a passenger touch on a stand. No physical or bank exception was introduced to force that alternative through.

The draft contains **1,214 flights, 184 routes and 17 lines**. Every line is now within the 9–12 route guideline. Fleet use remains MAX9 24/35, CRJ900 28/45, CRJ700 56/65 and CRJ200 76/80. Structural, operating, planning, physical gates/stands and next-day turns pass with **zero effective errors and zero hard stops**. Stand use stays at **15 claims / 3,061 minutes**. The existing runway-data check remains unavailable. Roster, pinned demand, bank windows, physical inventory and operating policy are unchanged.

## Reproduction and regression

```bash
python scripts/build_schedule_7_v1_3_2_draft.py
python tests/test_v1_3_2_maintenance_draft.py
node scripts/audit_schedule_7_v1_3_2_maintenance.mjs --accepted
bash scripts/run_latest_regression.sh
```

The builder verifies the released input SHA, confirms the old three defects, checks exact flight preservation and the two retimings, and runs the corrected native checks. Regression now requires the corrected validator to reject v1.3.1 as a fresh valid release, rather than reproducing its former false pass; all other checks stay active. The same CI command validates the repaired draft and its connection audit. Full release reproduction will resume against the corrected package at v1.3.2 publication.

The authoritative proposal is `config/optimizations/schedule_7_v1_3_2_round_1.json`; the draft artifacts are in `data/schedules/schedule_7_v1_3_2_draft/`. Demand-based fleet conversions are not included.
