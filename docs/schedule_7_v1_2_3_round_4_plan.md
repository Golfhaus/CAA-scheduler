# Schedule 7 v1.2.3: approved 526/509 additions and evening extensions

## Implemented state

On October 7, 2026, the user approved adding the 526 and 509 extensions. They are now implemented in the **unpublished accepted draft, with 1148 flights**:

| Route / line-day | Fleet | Added flying, local time | Existing-flight change |
|---|---|---|---|
| 526 / AJ-7 | CRJ900 | DAL 04:58 → MCI 06:25; MCI 07:15 → DAL 08:42, all CT | Flight 1206 DAL–PHF moves to 09:32 CT → 13:25 ET, +12 minutes |
| 509 / AB-9 | CRJ900 | SAT 05:00 → DAL 06:01; DAL 06:51 → SAT 07:52, all CT | None |

Flight numbers are 2147–2150, unchanged from the reviewed proposal. All previously approved v1.2.3 changes, including 305, remain present. The accepted draft passes structure, operating rules, overnight turns, planning and physical gate/stand allocation with zero operating errors and no hard-stop failures. It retains 182 warning findings and 15 stand claims totaling 3771 minutes.

The current authoritative accepted overlay is `config/optimizations/schedule_7_v1_2_3_accepted_rounds_1_3.json`, pinned to the released v1.2.2 canonical. Applying that combined overlay reproduces the sequentially reviewed flights, including their IDs, flight numbers and clocks. The working canonical is `data/schedules/schedule_7_v1_2_3_draft/canonical_schedule.json`. Earlier round-three proposal files describe their original 1144-flight comparison snapshot; they are historical evidence, not the current accepted state.

**No new evening proposal below has been implemented. Main and the app remain v1.2.2; publication is reserved to the user's decision.**

## Recommendation

**Add the ROA–PHF evening turn on 114 and the FWA–DAY late-bank turn on 169. Preserve the existing approved DAY turns on 340 and 327. Keep 350's late MCI turn as an optional, lower-priority addition.**

| Route / line-day | Current accepted endpoint | Disposition | Proposed flying, local time | Allocated local + connecting opportunity, out / back |
|---|---|---|---|---|
| 114 / AD-4 | ROA 18:49 ET | Recommended; best new hub option | ROA 19:30 → PHF 20:24; PHF 21:45 → ROA 22:39 ET | 0.6 + 33.7 / 0.6 + 86.3 |
| 169 / AF-5 | FWA 18:50 ET | Recommended; efficient short feeder | FWA 20:25 → DAY 21:05; DAY 21:55 → FWA 22:35 ET | 0.0 + 10.1 / 0.025 + 47.4 |
| 350 / AO-1 | ELP 17:41 MT | Optional; strongly directional | ELP 18:27 MT → MCI 21:43 CT; MCI 22:33 CT → ELP 23:49 MT | 3.3 + 0.0 / 3.2 + 148.0 |
| 340 / AL-4 | CLT 23:12 ET | Retain accepted evening DAY turn | Already CLT 19:48 → DAY 21:05; DAY 21:55 → CLT 23:12 ET | Previously reviewed and approved |
| 327 / AK-3 | SDF 22:43 ET | Retain accepted evening DAY turn | Already SDF 20:17 → DAY 21:05; DAY 21:55 → SDF 22:43 ET | Previously reviewed and approved |

These are **seat-uncapped, full-capture relative-choice opportunity scores**, not forecast loads, bookings, or net incremental passengers. All existing flights and competing nonstop/one-stop/two-stop choices are included. The pinned demand model uses 30–240-minute connections, a 2.25 circuity ceiling and no repeated airport. It does not model fares, operating costs, preferred departure times or seat constraints. Adding scores across flights can double-count travelers. The recommendations reflect relative connection usefulness and aircraft time; profitability has not been calculated.

## 114: new ROA–PHF service

The new flights are **2151 and 2152**, CRJ200, Route 114 / AD-4. ROA–PHF goes from **zero to one daily nonstop in each direction**, adding PHF alongside ROA's existing JAX service. Directional local O-D is only 0.6 each way: connections make the case.

The inbound reaches PHF at 20:24, 31 minutes before the 20:55 departure wave. Represented connecting demand includes Florida, Texas, Appalachia, coastal Georgia and a smaller Northeast contribution. Leading outbound markets are ROA–PIE (8.9 opportunity), ROA–DAL (7.7) and ROA–HOU (4.7). The 21:45 PHF departure can receive inbound traffic from multiple earlier waves and late arrivals from MCI/PIE. The return's leading groups are GLC (26.4), FLP (14.2), TEX (13.8) and NEC (7.2); RFD–ROA contributes 19.6 opportunity.

There are **41 minutes at ROA before the new departure and 81 minutes at PHF**. This is a tight 41-minute aircraft turn followed by a tight 31-minute connection into PHF's principal outbound wave; the model's minima are 40 and 30. That sensitivity is real: delaying the new departure by four minutes would miss much of the 20:55 wave. Preserve the selected clock and allow for appropriate ground handling. Existing Flight 1560 JAX–ROA remains 17:15–18:49.

Extra aircraft block is **1h48**, increasing Route 114 from 8h29 to 10h17. The aircraft day becomes 05:55–22:39; the unchanged next-day ROA 05:15 originator has **6h36 RON**.

The overlay explicitly records a ROA second-hub service-envelope exception under the user's standing authorization to add useful hubs. No gate, turn, curfew, bank or service-minimum rule is waived.

Alternatives tested:

- An unchanged-clock JAX turn produces roughly 12.8/36.3 opportunity, less useful than PHF, with 3h08 of added block. A nominal buffered return after 21:45 fails the existing JAX late-bank alignment; that bank is not silently extended.
- MCI is about 9.7/55.0 but returns ROA after midnight and adds 4h38 block. DAY is about 1.4/66.6 but is almost entirely return-driven. SYR is about 4.4/35.9. PHF offers the best balance of opportunity, time and new coverage.
- Advancing the last AVL/JAX flights by four minutes improves the ROA turn to 45 minutes but makes **17 best modeled itineraries slower**, including AVL onward journeys. Advancing them 30 minutes loses PNS–ROA availability and makes **21 best itineraries slower** with the PHF addition, for little improvement on the added legs. Neither retiming is selected.
- High-ranked BHM timings fail physical gate/passenger-touch allocation; those constraints are retained.

## 169: short feeder into DAY-B9

The new flights are **2153 and 2154**, CRJ200, Route 169 / AF-5. FWA–DAY goes from **three to four daily nonstops each way**. This is a fourth frequency because the requested aircraft already serves the pairing repeatedly; its value is a new time window and access to the approved 21:05–22:05 mini-bank. Local O-D is 0.0 FWA→DAY and 0.1 DAY→FWA.

FWA reaches DAY at 21:05, alongside CLT and SDF, with BWI arriving 21:14. The 21:55 return accepts those inbound feeders with 50/41-minute connections. Outbound FWA travelers primarily gain CLT, BWI and SDF options. Inbound FWA demand is broader: CGI (12.2), FLP (13.5), TEX (6.7), GLC (4.8) and smaller groups; CLT, FLL and PGD are leading individual origins. Northeast opportunity in this specific DAY bank is negligible. This is a useful late feeder, not complete all-group coverage.

There are **50 minutes in DAY**, and no original flight needs retiming. Only **1h20 of aircraft block** is added, taking Route 169 from 6h01 to 7h21. It ends FWA at 22:35 and preserves the cyclic Route 165 FWA 04:30 originator with **5h55 RON**. No new bank or hub-count exception is required.

Alternatives tested:

- A late PHF turn (FWA 19:50 → PHF 21:32; PHF 22:12 → FWA 23:54) passes with the standing extra-hub exception, about 7.8/37.9 opportunity and 3h24 block. DAY is more productive per added aircraft hour.
- Earlier BHM/MCI timings overfill physical gates. Moving FWA–BHM to the latest normal spoke departure makes a valid alternative: FWA 21:00 ET → BHM 21:39 CT; BHM 22:29 CT → FWA 01:08 ET next day. It scores 25.5/44.5, adds 3h18 block and leaves only **3h22** before the 04:30 originator. DAY provides nearly the same return opportunity in much less time and with a longer overnight window.
- A broader six-flight rebuild advances SBN–DAY 11 minutes and moves the intermediate flights into earlier banks, aiming to finish FWA at 16:05. Its screened extensions fail physical SYR gate allocation: the earlier SYR turn would require a 17th gate. It is not selected. This is a bounded rebuild screen, not proof that no global reconstruction could work.

## 350: optional late MCI turn

Flights **2155/2156** in the optional combined package use CRJ700, Route 350 / AO-1. ELP–MCI already has **three** daily flights each way across the schedule, including another line's 11:40 ELP departure. The addition makes four each way. Directional local O-D is 13.2/12.7; the model distributes that over four nonstops, yielding about 3.3/3.2 on the added legs.

The ELP 18:27 departure arrives MCI at 21:43, in MCI-M11, with almost no useful onward connections. Its 22:33 return, in MCI-M12, collects late inbound connections and scores about 151.1, chiefly connecting demand. Leading groups are TEX, GLC, FLP, APP and GCP. Some gained markets involve indirect journeys, such as HOU–MCI–ELP near the model's circuity ceiling; real-world willingness to use those journeys is not established by the O-D allocation.

The turn has **46 minutes in ELP and 50 minutes in MCI**. All four original 350 flights retain their clocks. It adds **4h32 aircraft block**, moving the aircraft day from 04:55–17:41 to **04:55–23:49**, with 13h36 total block. The single-day line returns to its own unchanged 04:55 originator after **5h06**. Curfews and overnight validation pass, but crew coverage and overnight maintenance opportunity need operational review.

The unbuffered 18:21 ELP / 22:17 MCI variant scores about 3.3/168.2 with two exact 40-minute turns. The saved option accepts slightly lower return opportunity for recovery margin. It remains lower priority than 114 and 169: one strong direction is purchased with a very weak outbound leg and a long aircraft day. Without fares/costs or a capacity-aware forecast, this analysis does not establish that the round trip is economically justified.

An ELP–BHM turn passes with an extra-hub exception but gives only about 30.5/41.7 opportunity, 5h52 block and an ELP 01:17 finish. An earlier MCI rebuild was also tested: advance the second existing turn, add a 14:05–14:45 MCI mini-bank, and operate ELP 16:43 → MCI 19:59 / MCI 20:39 → ELP 21:55. That version overfills MCI gates and is rejected. No new bank is included in either saved package.

## 340 and 327: already extended in this draft

The released v1.2.2 timetable ends 340 at CLT 17:21 and 327 at SDF 18:59. Those endpoints have already been resolved by the preceding approved v1.2.3 evening DAY feeder package:

- **340:** CLT 19:48–DAY 21:05 / DAY 21:55–CLT 23:12; current block 9h55. Route 341's CLT 05:10 originator retains 5h58 RON.
- **327:** SDF 20:17–DAY 21:05 / DAY 21:55–SDF 22:43; current block 9h39. Route 328's SDF 05:05 originator retains 6h22 RON. Its approved PGD–JAX morning turn is also retained.

Neither can launch another ordinary evening turn after its new return: the departure would be beyond the 21:00 spoke cutoff. There is also no room for a complete extra turn between the old endpoint and the approved DAY departure once 40-minute aircraft turns at each junction are honored (147/78 minutes available). Additional late-bank or overnight restructuring would be a different project; the existing useful DAY turns are the recommendation here.

## Joint validation and saved artifacts

| Package | Flight count | Added block | Lost modeled markets | Slower best itineraries | Faster best itineraries | Newly reachable underlying O-D |
|---|---:|---:|---:|---:|---:|---:|
| Accepted current draft, including 526/509 | 1148 | Already implemented | See prior approved reports | See prior approved reports | See prior approved reports | See prior approved reports |
| Proposed 114 PHF + 169 DAY | 1152 | 3h08 | 0 | 0 | 21 | 91.8 |
| Same plus optional 350 MCI | 1154 | 7h40 | 0 | 0 | 27 | 160.0 |

Both proposed packages pass structure, operating rules, overnight turns, planning and physical gate/stand checks jointly, with zero effective operating errors and no hard-stop failures. They retain the accepted draft's 182 warnings, 15 stand claims and 3771 stand minutes. Newly reachable underlying O-D identifies markets gaining modeled service; it is not incremental bookings. Aircraft-day utilization is not a crew-duty plan, and demand opportunity is not a load forecast.

The latest-release regression suite passed **49 checks (13 Python, 36 JavaScript)**, targeting only the app's latest published v1.2.2. No older release regression was performed.

Saved evidence and reviewable overlays:

- `config/proposals/schedule_7_v1_2_3_round_4_screen.json`: five-route inventory, timed screens, individual demand and itinerary audits.
- `config/proposals/schedule_7_v1_2_3_round_4_joint.json`: extra-hub sensitivities, buffered alternatives and broader rebuilding attempts.
- `config/proposals/schedule_7_v1_2_3_round_4_package.json`: marginal-demand details, connection groups/flight lists, retiming audits and full joint validation.
- `config/proposals/schedule_7_v1_2_3_round_4.json`: recommended four-flight proposal.
- `config/proposals/schedule_7_v1_2_3_round_4_optional_mci.json`: recommended proposal plus optional 350 MCI, six flights total.

Reproduction on this accepted state:

```bash
python scripts/analyze_schedule_7_v1_2_3_round_4.py
python scripts/analyze_schedule_7_v1_2_3_round_4_finish.py
python scripts/analyze_schedule_7_v1_2_3_round_4_package.py
bash scripts/run_latest_regression.sh
```

Screens use cached checkpoints pinned to the accepted draft SHA; `--fresh` reruns the relevant screen. Wide windows rank a 15-minute grid with one-stop marginal scores, retain selected timings, then evaluate full one/two-stop demand and physical constraints. The compared alternatives are bounded screens, not a global optimum. Earlier round scripts describe older accepted states and should not be used to rebuild this current draft.
