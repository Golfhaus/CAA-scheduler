# Schedule 7 v1.2.5 working draft

The accepted draft incorporates the CRJ200 line alignment, IND/CAK destination overnights and the approved MCI FOUR_BUFFERED package. **This version is unpublished.** Additional changes will accumulate here before the user decides to publish. Main and the app continue to use released v1.2.4.

The [MCI B1 review](schedule_7_v1_2_5_mci_b1_review.md) records the SDF/SBN/GRR/SGF destination overnights and six-minute bank shift, now accepted into this draft. The four-long-hold review is a separate analysis; its proposals are not yet accepted.

## Added flying

The first four additions use CRJ200 aircraft. Times below are local Eastern time. Each market grows from two to three flights daily in each direction.

| Flight | Route | Line / day | Flying | Purpose |
|---:|---:|---|---|---|
| 2173 | 125 | AE / 4 | DAY 21:35 → IND 22:18 | Evening DAY connections; aircraft RON in IND |
| 2174 | 126 | AE / 5 | IND 04:30 → DAY 05:13 | New IND originator feeding later DAY B1 departures |
| 2175 | 136 | AF / 4 | DAY 21:35 → CAK 22:25 | Evening DAY connections; aircraft RON in CAK |
| 2176 | 137 | AF / 5 | CAK 04:30 → DAY 05:20 | New CAK originator feeding later DAY B1 departures |

Flight **1503 DAY–HOU** moves from 05:50 ET to **05:53 ET**, arriving 07:31 CT. Flight **1873 DAY–FWA** moves from 05:50 ET to **06:00 ET**, arriving 06:40 ET. Their returns and every later flight keep their existing times. Together with the MCI package below, twelve released flights are retimed; the other 1,158 retain their clocks.

DAY B1 moves one minute later, from 05:00–06:00 to **05:01–06:01**. Both new arrivals serve ATW, HOU, BNA and FWA within B1, plus later banks. Existing 04:30 BHM and 05:09 JAX departures are too early to receive these feeders. The original DAY–BHM bank exception remains in place; no new exception is introduced.

## Approved MCI package — accepted round 2

Times are local; MCI/SGF are Central, SDF/SBN/GRR are Eastern. No fleet or line reassignment is required.

| Flight | Route | Line / day | Fleet | Flying |
|---:|---:|---|---|---|
| 2177 | 112 | AD / 2 | CRJ200 | MCI 21:10 → SDF 23:45 |
| 2178 | 113 | AD / 3 | CRJ200 | SDF 04:30 → MCI 05:05 |
| 2179 | 135 | AF / 3 | CRJ200 | MCI 21:25 → SBN 23:58 |
| 2180 | 136 | AF / 4 | CRJ200 | SBN 04:30 → MCI 05:03 |
| 2181 | 715 | B / 2 | MAX9 | MCI 21:23 → GRR 23:58 |
| 2182 | 716 | B / 3 | MAX9 | GRR 04:30 → MCI 05:05 |
| 2183 | 323 | AK / 3 | CRJ700 | MCI 23:10 → SGF 00:00 |
| 2184 | 324 | AK / 4 | CRJ700 | SGF 04:30 → MCI 05:20 |

SDF grows from two to three flights in each direction, SBN and SGF from one to two, and GRR gets its first MCI nonstop. MCI B1 moves from 04:45–05:45 to **04:51–05:51**. The SFB, RDU, ELP, SHV, OMA, ICT, FSD and CID departures move from 05:35 to **05:50**; AUS moves 04:45→04:51 and its return 07:15→07:18. PGD 05:25 and JAX 05:35 remain unchanged. All later flights retain their clocks.

Modeled connecting opportunity on MCI B1 departures rises from 157.0 to 302.8 units. These are seat-uncapped relative-choice opportunity units, not passengers or loads. AUS remains too early for these feeders; RDU gains geographically valid SGF feed. Return aircraft turns are 45 minutes from SDF/GRR, 47 from SBN, and 115 from SGF; SGF's passenger connections into the 05:50 wave have exactly 30 minutes.

AD retains maintenance on route 113 at MCI; AF retains route 138 at DAY. Both now reach, but do not exceed, ten consecutive non-MX nights. AK and B peak at four. AI's MCI overnights on 145/154 remain protected.

The MCI round makes 79 directional best itineraries faster. It loses no market's complete connecting coverage and no existing connecting-choice tuple on the ten retimed flights. Seven IND-origin markets have slower fastest itineraries: IND–SFB by ten minutes and IND–OMA/ELP/ICT/FSD/SHV/CID by fifteen. These reviewed tradeoffs are included in the acceptance.

## CRJ200 alignment carried into this version

The seven original CRJ200 lines are recalibrated into six closed lines, retaining all 66 aircraft-days. AR's flying is retained under other line labels. AC and other fleet lines remain outside the alignment. Route numbers in this draft follow the accepted mapping, rather than the original v1.2.4 numbering.

| Line | Routes | Length | Maximum consecutive non-MX nights, excluding 125/136 credit |
|---|---|---:|---:|
| AD | 111–121 | 11 | 10 |
| AE | 122–132 | 11 | 10 |
| AF | 133–143 | 11 | 10 |
| AI | 144–155 | 12 | 8 |
| AM | 156–167 | 12 | 9 |
| AN | 168–176 | 9 | 8 |

AE retains its SYR maintenance night on route 129/day 8. AF retains DAY on 138/day 6; its former MCI night on 135/day 3 is now SBN. Neither line relies on the former DAY nights on 125/136, and neither needs rolling-RON grace. The full mapping is included in `draft_report.json` and in the [alignment review](schedule_7_crj200_line_alignment.md).

## Validation and decision evidence

The combined draft has **1,182 flights, 181 routes and 19 lines**. Structural, operating hard-stop, overnight-turn, planning, fixed gate/stand and maintenance checks pass, with **zero effective operating errors**. There are 170 inherited advisories; the seven affected line-length warnings are removed. Stand use remains 16 claims / 3,717 minutes. Fleet inventory and aircraft-days are unchanged.

The reviewed demand and connection audit is reproduced from SHA-pinned inputs. Across both accepted rounds there are 100 directional markets with faster best itineraries; no previously connected market loses all valid connections. None of the twelve retimed flights loses any existing connecting-choice tuple within its reviewed round. TOL–HOU's fastest modeled itinerary becomes three minutes slower; its pinned O-D value is zero. Demand scores are seat-uncapped relative-choice opportunity units, not passenger forecasts or achievable loads.

Both returning aircraft have exactly the minimum 40-minute turn into their original originator. CAK's ATW passenger connection is exactly the 30-minute floor. These timings offer limited delay margin. Destination overnight feasibility still requires a separate crew duty/rest plan.

The **52 latest-release regression checks pass** against v1.2.4. The draft receives its own full feasibility and exact replay checks. Superseded released schedules are not regression targets.

## Authoritative draft and replay

- Configuration: `config/optimizations/schedule_7_v1_2_5.json`.
- Accepted cumulative overlay: `config/optimizations/schedule_7_v1_2_5_accepted_rounds_1_2.json`, applied directly to released v1.2.4.
- Saved canonical and validation/export artifacts: `data/schedules/schedule_7_v1_2_5_draft/`.
- Rebuild and verification: `python scripts/build_schedule_7_v1_2_5_draft.py`.
- Latest-release regression: `bash scripts/run_latest_regression.sh`.

The builder verifies base/source hashes, exact equivalence to the reviewed sequential alignment, IND/CAK and MCI proposals, preservation of original flights, approved retimings, route closure/length, independent maintenance, demand scores and connection tradeoffs. It writes the draft artifacts without changing the app manifest or publishing a release. The other reviewed destinations remain alternatives, outside this accepted round.

The round-one canonical and report are preserved in `data/schedules/schedule_7_v1_2_5_round_1/`, so the MCI review remains reproducible after acceptance. All source proposals are SHA-pinned; the cumulative overlay reproduces the sequential result.

The [four-long-hold review](schedule_7_v1_2_5_long_holds_review.md) proposes PHF turns for ALB/SWF and directional BTV/HPN feeders from SYR. Those eight flights and their small timing changes are not included in the accepted draft.
