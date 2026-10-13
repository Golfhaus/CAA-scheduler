# Schedule 7 v1.3.0

Published October 12, 2026 following explicit approval of the buffered R307 PIT–DAY–PIT round trip and release of the complete accepted draft. The app defaults to **v1.3.0: 1,192 flights, 181 routes and 19 routing lines**. Compared with v1.2.5, two flights are added and seven existing flights are retimed. Fleet inventory, aircraft-days, roster, demand v7, bank windows, policies and physical gates/stands are unchanged.

## R307 aircraft utilization

| Flight | Route; line/day | New flying, all ET |
|---|---|---|
| 2193 | 307; AA/7; CRJ700 | PIT 12:38 → DAY 13:35 |
| 2194 | 307; AA/7; CRJ700 | DAY 14:20 → PIT 15:17 |

These fit inside the former 11:24–16:46 PIT hold, with 74 minutes before the outbound, a 45-minute DAY turn and 89 minutes before the original PIT–PHF departure. They add 114 block minutes without another aircraft-day. Both DAY touches use existing B5. Original R307 flying, including PIT–PHF at 16:46 and PHF–CHS at 18:35, retains its clocks. The direct PIT–BHM trial and the three alternative DAY timings are not included.

PIT→BHM now connects through DAY to F1981 at 16:13 ET, arriving BHM at 16:44 CT: a 2h38 transfer and 5h06 total trip. The new pair also improves PIT→DAL from 4h32 to 3h51, PIT→MCI from 5h00 to 3h17, HOU→PIT from 5h25 to 4h27 and AUS→PIT from 4h59 to 4h27. It creates MCI→PIT one-stop service in 3h37 and PIT→GRR one-stop service in 4h35. Comparison is with the seven-retiming draft's app options. The [saved review](schedule_7_v1_3_0_r307_day_review.md) records all alternatives and geography checks.

## Timing repairs

| Flight | Local departure/arrival after change | Shift | New one-stop benefit |
|---|---|---|---|
| 1437 JAX–SFB | 16:13–16:58 ET | −2 min | BLV/GPT→SFB |
| 1036 MCI–SFB | 10:34 CT–14:07 ET | −1 min | MKE→SFB |
| 2017 MCI–CAK | 15:35 CT–18:40 ET | −2 min | PGD/DSM/FSD→CAK |
| 2019 MCI–PNS | 15:31–17:41 CT | −4 min | DAL→PNS |
| 1727 VPS–JAX | 05:58 CT–08:05 ET | +8 min | VPS→BWI |
| 1723 MCI–SGF | 17:14–18:04 CT | −1 min | RDU→SGF |
| 1589 MFE–MCI | 12:16–14:51 CT | −3 min | Supporting change: preserves a legal 40-minute MCI turn before F2019; MFE turn remains 46 minutes |

All other 1,183 original flight clocks and identities are preserved. Only R307 sequence numbers shift to accommodate its two insertions. Each change is applied once from the SHA-pinned v1.2.5 canonical.

## Validation and network comparison

Structure, operating, curfews, aircraft turns, overnight transitions, planning reconstruction and full fixed gate/stand assignment pass with **zero effective operating errors** and no hard-stop failures. Advisories decrease from 166 to 165 because R307's long hold is removed. Existing policy overrides are retained; none is added. Stand use remains **14 claims / 3,253 minutes**.

Against v1.2.5, the complete app audit adds **190 itinerary choices and 12 one-stop directional markets**, with zero lost direct/one/two-stop choices, zero lost coverage and zero lost one-stop markets. Fastest travel improves in 134 markets. The new markets are BLV→SFB, GPT→SFB, MKE→SFB, PGD→CAK, DSM→CAK, FSD→CAK, DAL→PNS, VPS→BWI, RDU→SGF, PIT→BHM, MCI→PIT and PIT→GRR.

The required F1589 advance causes the documented small tradeoff: 17 MFE-origin fastest journeys become 1–3 minutes longer because the first flight leaves earlier while the onward arrival is fixed. No itinerary disappears. Under the 2.25× distance screen, 102 fastest journeys improve, nine slow by 1–3 minutes, and 15 markets gain direct/one-stop coverage (three additional short markets previously had excessive-detour app options). Full market evidence is embedded in the release configuration and report and saved in the accepted draft's connection review.

The new MKE→SFB and PGD→CAK one-stop options take 7h57 and 8h50 respectively; their retained two-stop options of 5h10 and 5h45 remain faster. Fewer connections do not always mean less elapsed travel.

## Reproduction and checks

```bash
python -m caa_scheduler build-optimization-release config/optimizations/schedule_7_v1_3_0_release.json
bash scripts/run_latest_regression.sh
python -m caa_scheduler build-web --output dist
```

The release builder enforces the base canonical and accepted overlay fingerprints, complete structural/operating/planning/gate validation and expected counts. Latest-only regression rebuilds and compares every public package artifact, verifies exactly the approved insertions and retimings, checks the nine primary one-stop connections and tests the app's statistics, previews, routing geometry and fixed gate displays. Superseded schedules are not reconstructed for regression. The build's input v1.2.5 canonical is retained as a pinned source, not a second regression target.

The authoritative release configuration is `config/optimizations/schedule_7_v1_3_0_release.json`; accepted flying is in `schedule_7_v1_3_0_round_3.json`. Earlier drafts and proposal evidence remain historical. Pinned O-D is market size and opportunity, not forecast flight loads.
