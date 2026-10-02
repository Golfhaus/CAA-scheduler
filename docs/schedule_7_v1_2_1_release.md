# Schedule 7 v1.2.1

Released October 2, 2026 on the user's instruction to implement the proposals
on Routes 701, 123, 321, 129, 118, 323, 147, 151, 508 and 131 and publish
them to main. The app defaults to `schedule_7_v1_2_1`.

The release adds ten daily round trips (20 flights), reaching 1,116 flights,
181 routes and 20 lines. Existing aircraft and rotation positions are used;
fleet inventory, cities, hub banks, physical gates/stands, curfews and
connection display rules remain unchanged. The additions total 28h52 of
daily aircraft block time. The earlier approved 13-day MAX9 Line A exception
remains visible.

Times below are local to each airport. RFD/MCI/JAN/SAT/BLV/XNA use Central;
the other listed airports use Eastern. +1 denotes next calendar day.

| Route | Fleet / line-day | New flight outward | New flight return |
|---|---|---|---|
| 701 | MAX9 / A1 | 2099 PHF 09:20 → PGD 11:21 | 2100 PGD 12:40 → PHF 14:41 |
| 123 | CRJ200 / AD13 | 2101 SYR 08:40 → BDL 09:34 | 2102 BDL 10:30 → SYR 11:24 |
| 321 | CRJ700 / AH10 | 2103 SYR 16:50 → RFD 17:44 | 2104 RFD 18:44 → SYR 21:38 |
| 129 | CRJ200 / AD19 | 2105 MCI 14:50 → DAY 17:35 | 2106 DAY 18:15 → MCI 19:00 |
| 118 | CRJ200 / AD8 | 2107 MCI 15:25 → BLV 16:30 | 2108 BLV 17:10 → MCI 18:15 |
| 151 | CRJ200 / AE1 | 2109 MCI 13:45 → XNA 14:42 | 2110 XNA 15:38 → MCI 16:35 |
| 147 | CRJ200 / AD37 | 2111 SYR 11:18 → PIT 12:24 | 2112 PIT 13:04 → SYR 14:10 |
| 323 | CRJ700 / AH12 | 2113 SYR 18:55 → BWI 20:00 | 2114 BWI 20:40 → SYR 21:45 |
| 508 | CRJ900 / AB8 | 2115 SAT 20:19 → MCI 22:15 | 2116 MCI 22:55 → SAT 00:51 +1 |
| 131 | CRJ200 / AD21 | 2117 JAN 19:05 → MCI 20:48 | 2118 MCI 21:28 → JAN 23:11 |

The three previously proposed adjustments to existing flights are retained:
2041 SYR→PIT departs 22:25 instead of 22:14 (+11 minutes);
1607 PIT→SYR departs 09:32 instead of 09:35 (−3 minutes);
2043 SYR→ABE departs 22:25 instead of 22:18 (+7 minutes).
Arrival times shift by the same amounts. All other pre-release flight clocks,
numbers, fleet and route assignments are preserved.

Structural, planning and overnight-turn checks pass. Effective operating
errors and hard-stop failures are zero; passenger handling on stands is zero.
Stand use is 15 claims / 4,277 minutes, down from v1.2.0's 20 / 5,552.
The BHM audit remains 12 directly served target cities and 27 connected
directional cross-group pairs. Existing informational warnings and unavailable
aircraft-performance checks remain visible. Crew legality and economic
profitability require their own inputs.

The evening extensions have asymmetric connection opportunity, as discussed
in `schedule_7_v1_2_1_resolving_pair_audit.md`: the late MCI→SAT return is
stronger than its outward flight; the JAN pair is weaker. Their publication
does not resolve the remaining morning directional gaps. Opportunity values
assume full CAA capture without seat caps and are not predicted loads.
Routes 163, 307, 322 and 122 receive no further changes in this release.

Rebuild the release with:

```bash
python -m caa_scheduler build-optimization-release config/optimizations/schedule_7_v1_2_1.json
```

The pinned input is the published v1.2.0 canonical schedule followed by the
three approved v1.2.1 overlays. Authoritative artifacts are under
`data/schedules/schedule_7_v1_2_1` and are listed in `web/schedules.json`.
Run `bash scripts/run_latest_regression.sh` for release reproduction,
approved-flight/scope preservation, operating/planning/overnight validation,
retained DAY/JAX growth, gate capacity, connection accounting and app checks.
CI tests v1.2.1 only; historical releases remain input/reference data.
