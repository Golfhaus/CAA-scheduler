# Schedule 7 v1.3.1 draft — northeast service to PGD and DAB

Historical planning snapshot: the accepted changes were published as **v1.3.1 on October 13, 2026**. The [release notes](schedule_7_v1_3_1_release.md) and released canonical are authoritative; draft-status and default-schedule statements below describe the review checkpoint.

Accepted into the **unpublished draft** October 13, 2026. Published v1.3.0 and the app default remain unchanged. This is cumulative round 3, following R724's accepted RFD/JAX/MCI flying.

The totals and comparisons below describe the accepted round-3 checkpoint. Subsequent [DSM round-4 changes](schedule_7_v1_3_1_dsm_review.md) retain this coverage and raise the current draft to 1,214 flights.

## Result

HPN, HVN, ISP, BTV and ORH now have timetable-valid, geographically suitable one-stop service in **both directions** to PGD and DAB through **SYR**. All 20 priority directions pass the existing 30–240-minute connection window and 2.25 distance screen. Their combined pinned directional O-D is **335.4/day**: PGD 278.9 and DAB 56.5. ISP–DAB and ORH–DAB have zero recorded demand, but fit the same bank without additional flying.

The same five cities retain direct/one-stop service to FLL, PIE, SFB and SRQ in both directions. EYW, GNV and MLB still lack one-stop coverage for these cities; new SYR service or new northeast feeders would be required, so they do not meet the user's trivial-modification limit. Some gain two-stop options incidentally.

| Northeast city | To PGD | From PGD | To DAB | From DAB |
|---|---|---|---|---|
| HPN | 4h33; F1854 + F2210 | 4h43; F2201 + F1851 | 4h04; F1855 + F2204 | 4h22; F2207 + F1851 |
| HVN | 7h09; F1879 + F2210 | 6h40; F2201 + F1876 | 4h04; F1880 + F2204 | 6h19; F2207 + F1876 |
| ISP | 4h29; F1893 + F2210 | 4h47; F2201 + F1889 | 4h09; F1894 + F2204 | 4h26; F2207 + F1889 |
| BTV | 7h06; F2190 + F2210 | 7h26; F2201 + F1825 | 4h04; F1829 + F2204 | 7h05; F2207 + F1825 |
| ORH | 4h29; F1884 + F2210 | 4h47; F2201 + F1881 | 6h54; F1884 + F2204 | 4h26; F2207 + F1881 |

These are the fastest **one-stop** durations, not necessarily the fastest itinerary of any stop count. PGD→BTV, for example, gains a 7h26 one-stop option while retaining a faster 6h17 two-stop journey. PGD→HVN's fastest journey instead slows 19 minutes to 6h40 as its one-stop coverage is added. HVN and BTV have long morning waits at SYR; ORH has a long afternoon wait for DAB. No connection-window exception is used. HVN→DAB's 30-minute connection is exactly at the permitted minimum.

## Aircraft rotation and productive flying

Add R355 and R356 on CRJ700 Line AS, Days 3 and 4. They form a closed **PGD–DAB–PGD** segment between existing R343 and R344. Fleet use rises from 54/65 to **56/65**, leaving nine spare CRJ700 aircraft. This is two additional daily aircraft requirements within the cyclic line, not two flights that operate only every twelve days.

All clocks below are Eastern. No new bank or bank-window change is required.

| Route/day | Flight | Departure | Arrival | Purpose |
|---|---|---|---|---|
| R355/AS-3 | F2201 | PGD 04:46 | SYR 07:45 | Florida bank link |
| R355/AS-3 | F2202 | SYR 08:25 | JAX 10:53 | Existing hub network support |
| R355/AS-3 | F2203 | JAX 11:33 | SYR 14:01 | Existing hub network support |
| R355/AS-3 | F2204 | SYR 16:41 | DAB 19:19 | Florida bank link |
| R355/AS-3 | F2205 | DAB 20:03 | JAX 20:45 | Evening JAX bank turn |
| R355/AS-3 | F2206 | JAX 21:25 | DAB 22:07 | Evening JAX bank turn |
| R356/AS-4 | F2207 | DAB 05:07 | SYR 07:45 | Florida bank link |
| R356/AS-4 | F2208 | SYR 08:25 | BDL 09:19 | Restore morning BDL feed |
| R356/AS-4 | F2209 | BDL 10:35 | SYR 11:29 | Restore morning BDL feed |
| R356/AS-4 | F2210 | SYR 13:55 | PGD 16:54 | Florida bank link |
| R356/AS-4 | F2211 | PGD 19:43 | JAX 20:45 | Evening JAX bank turn |
| R356/AS-4 | F2212 | JAX 21:25 | PGD 22:27 | Evening JAX bank turn |

R355 supplies **11h57** of block flying across six legs; R356 supplies **9h29** across six legs. Their minimum same-day turns are 40 minutes. The evening JAX turns use B15, which has room; late PGD/DAB arrivals are legal RON terminators under the existing policy, rather than new curfew exceptions. PGD's 04:46 departure clears before the existing 04:55 boarding claim, keeping PGD within its two physical gates.

Without rebalancing, AS would grow to 13 days. Transfer existing R352 (RDU–DAY flying) from AS to AK, add **F2213 PHF 06:05–RDU 06:55** before R352 and **F2214 RDU 04:30–PHF 05:20** before existing R326 the following day. AS then closes in **12 days**, AK in **10**, with legal maintenance and overnight turns. The two bridge legs add 1h40; this round adds **23h06 total block**. The low-demand PHF–RDU bridge itself is not presented as the aircraft demand case; it carries the existing productive RDU day into a compliant rotation.

## Why this design

SYR already has all five northeast feeders and the established FLL/PIE/SFB/SRQ banks. JAX, BHM and PHF would require new two-way northeast feeder service for this group. Their Florida flights alone cannot turn the current three-flight chains into one-stop itineraries. SYR therefore offers a shared-bank solution with four new target-market legs, while the JAX and BDL support legs improve aircraft use and restore important connections.

SYR's original B2 and B4 waves already fill 16 gates. Simply adding two arrivals and departures fails physical inventory. The selected changes move a few existing turns to earlier banks, exchange two same-fleet round trips, and stagger the new afternoon Florida departures across B4/B5. JAX's new SYR round trip also restores JAX→HVN one-stop service after the HVN bank change, and strengthens the existing SYR/JAX connection network.

## Existing changes

All 1,192 published flight IDs, markets, aircraft types and pairing identities remain. **1,179 retain their clocks; 13 are retimed.** Existing R307 and all R724 flights are retained. Six existing legs change route ownership: the ROC turn moves from R125 to R159, and the HPN/ALB round trips are exchanged between R106 and R131. Both exchanged aircraft return to SYR at the unchanged 18:54 time, preserving their downstream BTV/ORH departures and line closures.

| Flight | Market | Previous departure–arrival | Draft departure–arrival |
|---|---|---|---|
| F1294 | BNA-PHF | 17:30–20:12 | 17:23–20:05 |
| F1335 | SYR-BNA | 13:55–14:59 | 13:15–14:19 |
| F1751 | SYR-ALB | 14:05–14:49 | 14:10–14:54 |
| F1811 | SYR-PVD | 08:44–09:47 | 06:06–07:09 |
| F1853 | SYR-HPN | 14:10–15:04 | 13:55–14:49 |
| F1854 | HPN-SYR | 12:30–13:24 | 12:21–13:15 |
| F1876 | SYR-HVN | 11:20–12:16 | 10:30–11:26 |
| F1887 | SWF-SYR | 07:05–07:54 | 04:30–05:19 |
| F2037 | SYR-BNA | 16:30–17:40 | 16:14–17:24 |
| F2101 | SYR-BDL | 08:40–09:34 | 05:59–06:53 |
| F2102 | BDL-SYR | 10:30–11:24 | 10:05–10:59 |
| F2167 | SYR-ROC | 06:06–06:45 | 05:56–06:35 |
| F2168 | ROC-SYR | 07:25–08:04 | 07:15–07:54 |

The larger shifts are deliberate: SWF originates earlier, BDL's original flight moves to B1, and PVD moves to B1 while ROC's turn transfers to the other aircraft. The new B2 BDL flight preserves morning Florida/northeast connections that the early BDL move would otherwise remove. The HPN/ALB exchange avoids an illegal 25-minute turn in the first timing proposal. BNA changes release the late SYR gate and keep BNA within two gates.

## Demand case and tradeoffs

The pinned matrix is already dampened for secondary airports. It is directional market demand, **not forecast passengers on these flights**. The opportunity review excludes connections competing with existing nonstops, screens geography, deduplicates each market per flight and separates competitive options from slow alternatives. Market totals overlap across legs and must not be summed as aircraft loads.

The four SYR/Florida legs have competitive equal-choice indices of approximately **261 PGD→SYR, 347 SYR→PGD, 45 DAB→SYR and 43 SYR→DAB**. PGD is the main demand driver. BDL support is mostly connecting demand rather than its 0.6/day local directional market: its indices are about 153 outbound and 44 returning. SYR/JAX support is about 62 outbound and 14 returning. These are screening indices across eligible alternatives, without a booking-preference or competitor-capture model. Several evening legs have modest opportunities; the overall aircraft case rests on the strong PGD flows, requested DAB coverage and the productive support flying, not a claim that every new flight fills its cabin.

Against round 2, the app gains **66 one-stop directional markets** and 186 faster fastest journeys, while losing seven one-stop markets and slowing 140 fastest journeys. Under the unchanged geographic screen, it gains **72**, loses **four**, improves 126 and slows 112. The audit records 145 raw existing path losses / 102 geographically suitable path losses. This round does **not** claim zero network regression.

The four geographically suitable markets losing one-stop coverage total **6.2/day** in recorded demand:

| Direction | O-D/day | Before | After |
|---|---|---|---|
| CAK→PVD | 5.1 | One stop, 3h07 | Two stops, 6h08 |
| DAY→HPN | 0.9 | One stop, 2h59 | Two stops, 5h23 |
| BTV→PVD | 0.2 | One stop, 2h47 | No geographically suitable option within two stops |
| MDT→HVN | 0.0 | One stop, 2h36 | No geographically suitable option within two stops |

The raw app also loses one-stop BGR→PVD (0.2), ACY→HVN (0.0) and ISP→PVD (0.0); those former options already failed the distance screen. All seven still have raw two-stop choices. The biggest material elapsed-time costs include ROC→BNA (+145 minutes), JAX→HVN (+127), CHS→HVN (+90) and CLT→HPN (+80); these retain one-stop coverage. ROC's existing Florida options slow ten minutes. The exact market-level changes are saved in the review JSON. These are intentional lower-demand tradeoffs within the user's authorized holistic changes, and deserve further optimization before publication.

## Validation and reproduction

The round-3 checkpoint contains **1,212 flights, 184 routes and 19 lines**. Fleet use is MAX9 24/35, CRJ900 28/45, CRJ700 56/65 and CRJ200 76/80. Native structural, operating, planning, maintenance/overnight and gate exports pass with **zero effective errors and zero hard stops**. There are 164 existing/effective advisories; the unavailable runway-data check remains unavailable. Physical inventory, bank counts/windows and the 30–240-minute connection window remain unchanged. Existing useful additional-hub exceptions cover the authorized new SYR service at PGD/DAB; no new timing or physical exception is introduced.

System stand use remains **16 claims / 3,595 minutes**, the same as round 2. All passenger handling takes place at gates.

```bash
python scripts/build_schedule_7_v1_3_1_draft.py
node scripts/audit_schedule_7_v1_3_1_connections.mjs
node scripts/audit_schedule_7_v1_3_1_ne_service.mjs
```

The builder also reproduces the SHA-pinned round-2 input needed for comparison. `--round-1` reproduces the earlier evening-review input without replacing the accepted draft; `--round-2` reproduces the hypothesis baseline. The historical hypothesis script now reads that baseline. No superseded release package or app default is changed.

Sources: `config/optimizations/schedule_7_v1_3_1_round_3.json`, `outputs/schedule_7_v1_3_1_ne_service/service_review.json`, and the regenerated current draft package. PR30 remains a draft; release requires a separate publication instruction.
