# R307 PIT–BHM–PIT review

Historical review from October 12, 2026 against the seven-retiming draft. These direct BHM proposals were not accepted: the user subsequently selected the buffered PIT–DAY–PIT extension for released v1.3.0. No direct BHM leg or R307 retiming from this review is included. Reproduce these trials at commit `c3f51b03aa326cc5933c0754be764030566cac21`; see the [release notes](schedule_7_v1_3_0_release.md) for current flying.

## Fit in the existing hold

R307 reaches PIT on F1917 at 11:24 ET and leaves for PHF on F1918 at 16:46 ET: 322 minutes, or 5h22. The repository's CRJ700 block model uses 519.9 nautical miles and rounds each direction to 106 minutes (1h46). Two flights plus three required 40-minute turns require 332 minutes (5h32). The shortfall is exactly ten minutes; timezone differences do not change elapsed flying time.

## Smallest tested modification with existing PHF banks

| Flight | Proposed local times | Change |
|---|---|---|
| New PIT–BHM, provisional F2193 | 12:04 ET–12:50 CT | Add 1h46 flying |
| New BHM–PIT, provisional F2194 | 13:30 CT–16:16 ET | Add 1h46 flying |
| F1918 PIT–PHF | 16:56–18:05 ET | Delay 10 minutes |
| F1401 PHF–CHS | 18:52–20:07 ET | Delay 17 minutes; use existing PHF-M6 |

Ground times are 40 minutes in PIT before the new outbound, 40 in BHM, 40 in PIT before F1918, and 47 in PHF before F1401. F1917 and all earlier flying stay unchanged. Keeping F1401 at 18:35 would leave only 30 minutes in PHF. A ten-minute delay would depart at 18:45, outside PHF-B6's exclusive end; the next existing bank starts at 18:52. No bank-window change or override is needed for the tested 17-minute delay.

This adds 212 block minutes to the existing aircraft-day, with no added fleet use. It passes structure, operating, overnight, planning and fixed physical gate/stand allocation, with zero effective operating errors, 165 advisories and unchanged 14 stand claims / 3,253 minutes.

However, the app audit loses 19 itinerary choices and slows ten markets' fastest journeys. No market loses all service or its last direct/one-stop option. The largest penalty is PIT→DAL: 4h32 becomes 6h52 (+2h20), after the later PHF arrival misses its earlier connection. Seven other CHS-bound markets slow 17 minutes, GRR→CHS slows 12, and PIT→CHS slows 7. It adds 121 itinerary choices and five direct/one-stop market coverages: PIT→BHM, PIT→HRL, PIT→ATW, PIT→ICT and PIT→FSD. Some new PIT→ATW coverage comes from the existing retimed PHF path rather than the added BHM flight.

Pinned direct O-D is 12.8 PIT→BHM and 12.9 BHM→PIT passengers/day. The new outbound can connect to JAX, HRL, SFB, FLL, ICT and FSD in BHM within 30–240 minutes and the 2.25× distance limit; the inbound can receive DAB and PIE. Those existing markets total 483.5 and 113.1 underlying O-D/day respectively, before allocation among alternatives. They are market sizes, not predicted flight loads.

## Buffered alternative

The second tested proposal departs PIT at 12:09 ET, reaches BHM at 12:55 CT, returns at 13:40 CT and reaches PIT at 16:26 ET. It delays F1918 by 20 minutes to 17:06–18:15 ET and F1401 by 25 to 19:00–20:15 ET, retaining 45/45/40/45-minute turns. It also passes full validation. Its connection outcome is worse: 26 choices lost, PIT→MSY loses one-stop service, and 15 fastest journeys slow. It is not recommended as the simple repair.

## Recommendation and reproduction

Keep R307 pending. The minimum construction is feasible, but losing PIT→DAL's fast connection is a significant cost. If pursuing BHM service, first investigate preserving or replacing that PHF connection, or a broader morning rotation change that gets R307 into PIT earlier. The unchanged PHF arrival-to-PIT departure turn is already 40 minutes, so advancing F1917 alone cannot recover the ten minutes legally.

- `python scripts/build_schedule_7_v1_3_0_draft.py`
- `python scripts/review_schedule_7_v1_3_0_r307.py`
- `node scripts/audit_schedule_7_v1_3_0_connections.mjs --r307`

Proposal overlays are `config/proposals/schedule_7_v1_3_0_r307_minimum.json` and `config/proposals/schedule_7_v1_3_0_r307_buffered.json`, pinned to the current accepted canonical SHA256. Validation and exact clocks are in `outputs/schedule_7_v1_3_0_r307/review.json`; detailed app and geographic tradeoffs are in `connection_review.json`. Trial canonicals regenerate locally from the overlays. The review checks that it has not changed the accepted draft.
