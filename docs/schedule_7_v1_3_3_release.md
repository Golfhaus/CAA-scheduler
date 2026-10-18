# Schedule 7 v1.3.3 release — October 18, 2026

**Approved by user for publication to main.** Release supersedes Schedule 7 v1.3.2 as default.

## Scope
- v1.3.2 base: 1,229 flights, 184 routes, 17 routing lines.
- Retains the previously reviewed R514 PIE–MCI round trip modification.
- Adds four BHM north/south mini-bank routes (24 flights total):
  - CRJ900 R529: ALB–BHM–SRQ, with CMH–ALB–CMH positioning; integrated into AG day 11.
  - CRJ900 R530: CAK–BHM–MYR, with SYR–CAK–SYR positioning; integrated into AG day 9.
  - CRJ700 R357: ISP–BHM–PGD, with RDU–ISP–RDU positioning; integrated into AK day 10.
  - CRJ700 R358: HVN–BHM–CHS, with CHS–HVN–CHS positioning; integrated into AA day 8.
- AG is 11 route-days, AK 13 and AA 12. R519 shifts to AG day 10, and the affected AK/AA trailing route-days shift by one.
- No airport gate/stand inventory or aircraft fleet size increased; no bank, curfew or maintenance exceptions added.

## Native validation and commercial considerations
- Combined four-route candidate: **1,253 legs, 188 routes, 17 routing lines**, zero effective operating errors, structural/overnight/planning/gates pass.
- CRJ900 used 30/45; CRJ700 used 58/65.
- Individual and joint R357/R358 screens: `outputs/schedule_7_v1_3_3_bhm_line_insertion/remaining_two_alternatives.json`, `remaining_two_combined.json`.
- Previous network audit for the four original BHM route shapes found 60 new geographically reasonable directional markets, no lost markets and 117 faster fastest journeys versus the R514-only baseline. **This audit predates the final positioning-leg replacements**; it must not be misrepresented as an exact final release-level itinerary delta. The release connection audit is BHM-focused.
- The R514 PIE–MCI adjustment has previously documented FWA→PIE service loss and PIE→HVN/GRR→PIE follow-ups; these remain commercial items for later consideration.

## Reproduction and publication
- `python scripts/build_schedule_7_v1_3_3_draft.py` constructs the four-route-integrated draft from the pinned v1.3.2 base and v1.3.3 overlays.
- `python scripts/prepare_schedule_7_v1_3_3_release.py` packages released assets and adds the v1.3.3 web manifest default.
- `bash scripts/run_latest_regression.sh` verifies latest schedule and web-facing logic.
- Pre-BHM revert checkpoint remains `checkpoint/schedule-7-v1.3.3-pre-bhm-minibanks` at `6965d28175b4089c269f543a1d6b24b423fbdcb3`, unchanged.
