# R144 holistic rebuild review — proposal only

Reviewed October 15, 2026 against accepted v1.3.2 draft commit `4d72b3eaea5d3659e09e7c8b252ca889f2ac21a9`, canonical SHA256 `4de8042da82c48f67a991551476e620f01b17cade91d75b5189e9a53ecbb48b0`. This investigation does not change any accepted overlay or schedule artifact. The accepted draft remains 1,221 flights / 184 routes / 17 lines. Main and the app remain v1.3.1.

## Finding

A holistic rebuild is feasible while retaining **all four existing sectors**. The best-balanced candidate found adds an early JAN–JAX–JAN turn and an evening MCI–BNA–MCI turn, changes the hub banks of three existing flights, and preserves the existing OKC→MCI clock. It substantially improves aircraft use and loses fewer reasonable direct/one-stop markets than the more aggressive HOU/RFD, BNA/DAL and BWI alternatives tested.

The BNA addition has strong local and connecting support. The early JAX pair is the commercial caveat: its connecting opportunity is real, but modest. Treat this as a reviewable candidate, not a commitment to fly the morning pair merely to increase block hours.

## Current and proposed day

| Metric | Current R144 | Candidate |
| --- | --- | --- |
| Sectors | 4 | 8 |
| First departure from JAN, CT | 08:10 | 04:30 |
| Terminating arrival at SHV, CT | 20:28 | 23:48 |
| Flying | 5h38 | 12h04 |
| Longest hold | 2h22 | 1h40 |
| Existing sectors retained | — | All four |

| Sector | Departure | Arrival | Status |
| --- | --- | --- | --- |
| JAN–JAX | 04:30 CT | 07:08 ET | Added |
| JAX–JAN | 07:48 ET | 08:26 CT | Added |
| JAN–MCI | 09:42 CT | 11:25 CT | Retained; 92 minutes later |
| MCI–OKC | 13:05 CT | 14:16 CT | Retained; 50 minutes later |
| OKC–MCI | 15:25 CT | 16:36 CT | Retained; unchanged |
| MCI–BNA | 17:16 CT | 18:51 CT | Added |
| BNA–MCI | 19:31 CT | 21:06 CT | Added |
| MCI–SHV | 22:15 CT | 23:48 CT | Retained; 200 minutes later |

The first MCI hold falls from 142 to 100 minutes. The old 139-minute second MCI sit is replaced by the BNA turn, with 40 minutes before it and 69 minutes after it. OKC falls from 119 to 69 minutes. The other added turns are JAX 40, JAN 76 and BNA 40 minutes. Average same-day hold falls from 133 to 62 minutes. Total ground time increases by 34 minutes because four additional flights introduce four additional turns; block increases by 6h26. The block share of the operating span rises from 45.8% to 62.5%.

R144 remains AI day 1, starts in JAN and ends in SHV. Its preceding JAN arrival remains 23:11 and the next day's SHV departure remains 06:40. The candidate leaves 5h19 and 6h52 between those operating days. Line size, fleet use and the maintenance cycle are unchanged.

## Demand and bank value

MCI–BNA currently has two daily departures each way. Underlying local demand is **77.9 / 78.2 passengers/day**. The proposed third pair also serves meaningful connections: OKC→BNA falls from 6h39 to 3h26; MKE→BNA from 4h28 to 3h41; BNA→SAT from 6h26 to 5h20; BNA→DSM from 4h01 to 2h55. Competitive opportunity indices are **193.0 outbound / 161.5 inbound**.

JAN–JAX currently has one afternoon flight each way: JAN 15:00 CT→JAX 17:38 ET and JAX 19:25 ET→JAN 20:03 CT. The new morning pair adds a distinct part of the day. Local O-D is only **5.0 / 4.9 per day**; it is not a sufficient case by itself. The 07:08 JAX arrival catches DAY at 07:38, PGD at 08:00, SYR at 08:10, and PIT/other departures at 08:35. The return provides morning JAX feed into JAN. Competitive opportunity indices including connections are **21.8 / 35.7**, substantially weaker than BNA. The weaker outbound leg is an explicit commercial caveat.

Indices split underlying geographically reasonable O-D opportunity across competitive choices within 30 minutes of the fastest itinerary at the same stop count, exclude connecting journeys when a nonstop exists and include at most one stop. They are not flight-load forecasts or a capacity-constrained passenger allocation. The 50-seat CRJ200 is not assumed full on the strength of these indices.

The revised JAN–MCI arrives in MCI-B5, with MCI–OKC in B6 and its unchanged return in B8. The new BNA turn departs in B8 and returns in MCI-M11. The SHV flight departs MCI-M12. Existing banks are reused; no bank extension or operating waiver is added.

## Passenger tradeoffs

The app's raw enumeration loses 82 existing itinerary choices; 52 pass the 2.25× geographic screen. Most affected choices remain available through different flights. No nonstop market disappears and no existing sector is removed.

**Geographically reasonable direct/one-stop coverage:** 26 gains, three losses:

| Market losing one-stop coverage | O-D/day | Remaining reasonable option |
| --- | --- | --- |
| ATW–OKC | 1.7 | Two stops, 6h27; formerly fastest 5h54 |
| DSM–SHV | 0.8 | None under the connection/circuity screens |
| ATW–SHV | 0.2 | Two stops, 10h33; formerly fastest 3h50 |

These coverage losses sum to 2.7 underlying passengers/day, not a count of passengers who would necessarily lose service. Gains include ELP–BNA (19.0/day), SFB–SHV (9.8), BNA–SHV (8.1), CRP–BNA (6.1), JAN–FLL (5.7) and PIT–JAN (4.4), plus smaller markets. The zero-demand MCN–JAN gain is not counted as commercial support.

**Fastest reasonable journeys:** 48 improve, 31 become slower. The 31 increases are fully retained in the evidence:

- Twenty-two origins to OKC take 50 minutes longer because MCI–OKC moves 50 minutes later: BNA, BLV, RDU, CAK, PGD, BUF, OMA, SYR, DSM, HRL, PWM, ROC, MHT, CID, FSD, LIT, BTV, BGR, COU, ISP, ORH and HVN. HVN has zero demand in the matrix.
- JAN–RDU and JAN–PHF become 100 minutes longer; JAN–MAF becomes 45 minutes longer.
- RFD–SHV becomes 59 minutes longer, PIE–SHV 90 minutes, BLV–SHV and FSD–SHV 200 minutes.
- ATW–OKC becomes 33 minutes longer with an additional stop; ATW–SHV becomes 403 minutes longer with an additional stop.

Raw coverage also loses MAF–SHV, OKC–SHV, XNA–SHV and HRL–SHV; their former paths fail the geographic screen. Raw totals are 39 direct/one-stop coverage gains / seven losses, 74 fastest journeys improved / 43 slower. The evidence includes both raw and geographic results, so the geographic filter does not hide losses.

## Alternatives tested

| Candidate | Result |
| --- | --- |
| Retain four sectors, early MCI arrival, HOU + DAL/RFD/AUS | Physical gate failure in MCI's early bank |
| Retain four, early JAN–MCI + HOU/RFD | Passes physical/native checks; 20 reasonable coverage gains / 11 losses, including the loss of several JAN connections; early JAN–MCI competitive index falls to 1.8 |
| Retain four, early JAN–MCI + BNA/DAL | Passes; 14 gains / 13 losses, including OKC–BNA and OKC–BWI |
| HOU + DSM or LIT | Passes but added small-market sectors have weak opportunity indices (DSM 15.6/8.1; LIT 24.4/7.5); not recommended merely to occupy time |
| Six-flight HOU rebuild | Passes; adds 4h block and reduces maximum hold to 78 minutes, but loses 17 reasonable direct/one-stop markets, including BNA–OKC |
| Six-flight BWI rebuild | Passes, with strong new-sector demand, but loses 20 reasonable direct/one-stop markets, including OKC–RFD (57.5/day) |
| Replace JAN–MCI with JAN–JAX–MCI + HOU | Tested versions fail physical gates |
| Replace JAN–MCI with JAN–DAY–MCI + HOU | Physically fits but requires a new JAN hub-count exception; not introduced into the draft |
| JAN–JAX turn starting 04:50 or 05:00 | Both pass, but yield weaker overall connection results than 04:30; no reduction in the route's maximum hold |

The early JAN–MCI alternatives are especially instructive: more block hours can be fitted, but their first leg loses useful connections and the same-market 06:30 JAN departure competes strongly with them. Preserving the original OKC–MCI time and adding the BNA turn protects important OKC connections better than those alternatives.

## Verification and reproduction

The preferred candidate passes structural, operating (zero effective errors/hard stops), planning reconstruction/validation, overnight-turn and physical gate-export checks. Fleet use stays MAX9 24/35, CRJ900 28/45, CRJ700 56/65 and CRJ200 76/80. Stand use stays 15 claims / 3,061 minutes. AM's existing standing maintenance grace and unavailable runway-data check remain inherited.

The [proposal overlay](../config/proposals/schedule_7_v1_3_2_r144_jax_bna.json) is **not applied**. [Native and network evidence](schedule_7_v1_3_2_r144_evidence.json) includes every tested candidate's screening summary and the preferred candidate's complete itinerary losses, fastest-journey changes, market coverage and flight profiles.

Run `python scripts/review_schedule_7_v1_3_2_r144.py jan_jax_bna_preserve_okc_return` against the pinned accepted canonical, then `node scripts/audit_schedule_7_v1_3_2_r144.mjs jan_jax_bna_preserve_okc_return`. Omitting scenario names repeats the broader native screen / all passing network cases. The scripts never change the accepted schedule.
