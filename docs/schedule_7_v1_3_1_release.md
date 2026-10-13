# Schedule 7 v1.3.1

Published October 13, 2026 following the user's instruction to publish the complete accepted draft. The app defaults to **v1.3.1: 1,214 flights, 184 routes and 19 routing lines**. The released flight list matches accepted draft commit `7a86b782bc415fd2574a19ab317a37b72f1c27e8` exactly. Relative to v1.3.0, it adds 22 flights and changes 15 existing clocks while retaining every original flight ID, market, pairing and aircraft type.

## RFD connections and MAX9 utilization

R724 on MAX9 line A provides the following daily flying. Times are local.

| Flight | Market | Departure | Arrival |
|---|---|---|---|
| F2195 | RFD–JAX | 05:40 CT | 08:56 ET |
| F2196 | JAX–RFD | 09:40 ET | 10:56 CT |
| F2197 | RFD–JAX | 12:14 CT | 15:30 ET |
| F2198 | JAX–RFD | 16:10 ET | 17:26 CT |
| F2199 | RFD–MCI | 19:26 CT | 20:40 CT |
| F2200 | MCI–RFD | 21:20 CT | 22:34 CT |

The day supplies 11h32 of block flying and uses one additional MAX9 aircraft-day. MYR, EYW, ECP, ILM, ROA and TLH gain timetable-valid one-stop service with RFD in both directions. ROA via JAX remains a 2.36× distance detour; the other five priority pairs pass the existing 2.25 screen. The evening MCI turn preserves the next-day 04:35 departure. The existing R703/R704 closed SFB–DAY–SFB segment moves administratively to line B, keeping both MAX9 lines at 12 days without changing its flight times.

## Northeast PGD/DAB service

HPN, HVN, ISP, BTV and ORH gain geographically suitable one-stop service in **both directions** to PGD and DAB through existing SYR banks. All 20 priority directions meet the unchanged 30–240-minute transfer window and distance screen. Existing FLL/PIE/SFB/SRQ coverage for these five cities remains intact. EYW, GNV and MLB required more than trivial changes and were not expanded.

The main Florida bank links are F2201 PGD 04:46–SYR 07:45, F2207 DAB 05:07–SYR 07:45, F2210 SYR 13:55–PGD 16:54 and F2204 SYR 16:41–DAB 19:19, all ET. R355/R356 add two CRJ700 aircraft-days with 11h57 and 9h29 block days, including productive SYR/JAX, SYR/BDL and evening JAX support flying. R352's existing RDU day moves to AK with two PHF/RDU bridge legs, keeping AS at 12 days and AK at 10.

SYR's fixed 16-gate waves require the 13 previously reviewed retimings, a ROC turn transfer and an HPN/ALB same-fleet exchange. Those changes and their demand case are listed in the [northeast review](schedule_7_v1_3_1_ne_service.md).

## DSM operating day

R154's existing MCI hold accommodates an afternoon CRJ200 turn, adding 1h40 block without another aircraft. R516's RFD turn moves 75 minutes later without changing its subsequent SYR flight. All times are CT.

| Flight | Market | Released times |
|---|---|---|
| F1210 | RFD–DSM | 07:15–08:15 |
| F1209 | DSM–RFD | 08:55–09:55 |
| F2215 | MCI–DSM | 14:00–14:50 |
| F2216 | DSM–MCI | 15:35–16:25 |

Against the preceding draft, these changes add nine one-stop directional markets and improve 19 geographically suitable fastest journeys, with no lost itinerary choices, coverage or slower fastest journeys. R150 remains unchanged: the physically feasible earlier DAY option had weak incremental demand and worsened useful DSM trips. The [DSM review](schedule_7_v1_3_1_dsm_review.md) records timing margins, connecting-demand evidence and rejected alternatives.

## Fleet, validation and network tradeoffs

| Fleet | Aircraft-days used / inventory | Spare |
|---|---|---|
| MAX9 | 24 / 35 | 11 |
| CRJ900 | 28 / 45 | 17 |
| CRJ700 | 56 / 65 | 9 |
| CRJ200 | 76 / 80 | 4 |

Structural, operating, physical gate/stand, maintenance/overnight and planning checks pass with **zero effective operating errors and zero hard-stop failures**. The existing runway-data check remains unavailable. Destinations, fleet inventory, physical capacities, bank windows, connection limits and pinned demand v7 are unchanged. System stand use is **15 claims / 3,061 minutes**, versus 14 / 3,253 in v1.3.0; all passenger handling remains at gates.

Compared with released v1.3.0, raw timetable coverage gains 108 directional markets with at most one connection and loses seven. It adds 1,989 itinerary choices on net, improves 241 fastest journeys and slows 140. Under the unchanged geography screen, 108 markets gain coverage and four lose it; 173 fastest journeys improve and 112 slow. There are 145 raw existing itinerary losses / 102 geographically suitable losses; this release does not claim a regression-free network.

The four geographically suitable one-stop losses total 6.2/day in recorded O-D: **CAK→PVD, DAY→HPN, BTV→PVD and MDT→HVN**. The three additional raw losses previously failed the distance screen. Material journey-time costs from the SYR changes, including ROC→BNA, JAX→HVN, CHS→HVN and CLT→HPN, remain documented. The user approved publication of these reviewed tradeoffs. Some new one-stop options are slower than retained two-stop choices.

All demand totals and opportunity indices describe eligible markets, **not forecasts of aircraft loads**. Existing alternatives, geographic suitability and already served nonstop markets are considered in the connecting-demand screening.

## Reproduction and regression

```bash
python -m caa_scheduler build-optimization-release config/optimizations/schedule_7_v1_3_1_release.json
bash scripts/run_latest_regression.sh
python -m caa_scheduler build-web --output dist
```

The release configuration pins the v1.3.0 input and the cumulative accepted overlay. It records the publication instruction, accepted draft fingerprint, full-network comparison and expected native results. Latest-only regression rebuilds every published package artifact, confirms the release matches accepted flying, checks the priority connections and geography, and tests the web console and statistics. Superseded release packages are not rebuilt as regression targets. Historical draft artifacts remain review evidence; the released canonical is authoritative.
