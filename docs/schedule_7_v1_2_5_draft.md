# Schedule 7 v1.2.5 working draft

The first accepted round incorporates the CRJ200 line alignment and the recommended IND/CAK destination overnights. **This version is unpublished.** Additional changes will accumulate here before the user decides to publish. Main and the app continue to use released v1.2.4.

## Added flying

All four additions use CRJ200 aircraft. Times below are local Eastern time. Each market grows from two to three flights daily in each direction.

| Flight | Route | Line / day | Flying | Purpose |
|---:|---:|---|---|---|
| 2173 | 125 | AE / 4 | DAY 21:35 → IND 22:18 | Evening DAY connections; aircraft RON in IND |
| 2174 | 126 | AE / 5 | IND 04:30 → DAY 05:13 | New IND originator feeding later DAY B1 departures |
| 2175 | 136 | AF / 4 | DAY 21:35 → CAK 22:25 | Evening DAY connections; aircraft RON in CAK |
| 2176 | 137 | AF / 5 | CAK 04:30 → DAY 05:20 | New CAK originator feeding later DAY B1 departures |

Flight **1503 DAY–HOU** moves from 05:50 ET to **05:53 ET**, arriving 07:31 CT. Flight **1873 DAY–FWA** moves from 05:50 ET to **06:00 ET**, arriving 06:40 ET. Their returns and every later flight keep their existing times. All other 1,168 released flights retain their departure and arrival clocks.

DAY B1 moves one minute later, from 05:00–06:00 to **05:01–06:01**. Both new arrivals serve ATW, HOU, BNA and FWA within B1, plus later banks. Existing 04:30 BHM and 05:09 JAX departures are too early to receive these feeders. The original DAY–BHM bank exception remains in place; no new exception is introduced.

## CRJ200 alignment carried into this version

The seven original CRJ200 lines are recalibrated into six closed lines, retaining all 66 aircraft-days. AR's flying is retained under other line labels. AC and other fleet lines remain outside the alignment. Route numbers in this draft follow the accepted mapping, rather than the original v1.2.4 numbering.

| Line | Routes | Length | Maximum consecutive non-MX nights, excluding 125/136 credit |
|---|---|---:|---:|
| AD | 111–121 | 11 | 9 |
| AE | 122–132 | 11 | 10 |
| AF | 133–143 | 11 | 7 |
| AI | 144–155 | 12 | 8 |
| AM | 156–167 | 12 | 9 |
| AN | 168–176 | 9 | 8 |

AE retains its SYR maintenance night on route 129/day 8. AF retains MCI on 135/day 3 and DAY on 138/day 6. Neither line relies on the former DAY nights on 125/136, and neither needs rolling-RON grace. The full mapping is included in `draft_report.json` and in the [alignment review](schedule_7_crj200_line_alignment.md).

## Validation and decision evidence

The combined draft has **1,174 flights, 181 routes and 19 lines**. Structural, operating hard-stop, overnight-turn, planning, fixed gate/stand and maintenance checks pass, with **zero effective operating errors**. There are 172 inherited advisories; the seven affected line-length warnings are removed. Stand use remains 16 claims / 3,717 minutes. Fleet inventory and aircraft-days are unchanged.

The reviewed demand and connection audit is reproduced from SHA-pinned inputs. There are 21 directional markets with faster best itineraries; no previously connected market loses all valid connections. Neither retimed flight loses any existing connecting-choice tuple. TOL–HOU's fastest modeled itinerary becomes three minutes slower; its pinned O-D value is zero. Demand scores are seat-uncapped relative-choice opportunity units, not passenger forecasts or achievable loads.

Both returning aircraft have exactly the minimum 40-minute turn into their original originator. CAK's ATW passenger connection is exactly the 30-minute floor. These timings offer limited delay margin. Destination overnight feasibility still requires a separate crew duty/rest plan.

The **52 latest-release regression checks pass** against v1.2.4. The draft receives its own full feasibility and exact replay checks. Superseded released schedules are not regression targets.

## Authoritative draft and replay

- Configuration: `config/optimizations/schedule_7_v1_2_5.json`.
- Accepted cumulative overlay: `config/optimizations/schedule_7_v1_2_5_accepted_round_1.json`, applied directly to released v1.2.4.
- Saved canonical and validation/export artifacts: `data/schedules/schedule_7_v1_2_5_draft/`.
- Rebuild and verification: `python scripts/build_schedule_7_v1_2_5_draft.py`.
- Latest-release regression: `bash scripts/run_latest_regression.sh`.

The builder verifies base/source hashes, exact equivalence to the reviewed sequential alignment and IND/CAK proposal, preservation of original flights, approved retimings, route closure/length, independent maintenance, demand scores and connection tradeoffs. It writes the draft artifacts without changing the app manifest or publishing a release. The other reviewed destinations remain alternatives, outside this accepted round.
