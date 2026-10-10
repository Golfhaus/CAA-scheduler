# Schedule 7 v1.2.4 — Routes 304, 125 and 157 extension review

Status: **approved and implemented in the unpublished v1.2.4 draft** following the instruction “Add the suggested additions from the last few messages to 1.2.4.” At round-four acceptance the working draft had **1,168 flights**. Round five subsequently added the approved PHF–MCI exchange, bringing it to **1,170**; see `docs/schedule_7_v1_2_4_midnight_swap.md`. Route 304 remains unchanged; main remains v1.2.3.

This review uses the immutable accepted round-three snapshot in `data/schedules/schedule_7_v1_2_4_round_3/canonical_schedule.json`. The original reviewed joint proposal is preserved in `config/proposals/schedule_7_v1_2_4_proposed_125_157.json`. Accepted incremental replay is `config/optimizations/schedule_7_v1_2_4_accepted_round_4.json`; round-four cumulative replay from released v1.2.3 is `config/optimizations/schedule_7_v1_2_4_accepted_rounds_1_4.json`. The full screen and audit are `config/proposals/schedule_7_v1_2_4_extensions_review.json`. Flights 2167–2170 are now in the draft.

## Recommendation

- **157: favor the evening OMA–BHM turn.** It doubles a one-flight pairing, preserves every existing clock, and offers useful late connections. The cost is an after-midnight return, a short OMA aircraft overnight, and a separate crew plan.
- **125: consider the morning SYR–ROC turn, rather than extending the DAY terminator.** The ROC–SYR feeder is useful; the outbound is almost entirely positioning. Three minimum turns and a nine-minute PVD retiming make this the more conditional option.
- **304: retain the current schedule.** The practical MCI extension is commercially weak and worsens established connections. Additional flying solely to fill the hours is not warranted by this screen.

| Route | Fleet / line / day | Current start–finish, local | Current block | Proposed block | Added block |
|---|---|---|---|---|---|
| 304 | CRJ700 / AA / 4 | PNS 04:30–HRL 19:42 CT | 8h48 | 8h48 | — |
| 125 | CRJ200 / AD / 15 | HVN 04:30–DAY 19:43 ET | 6h11 | 7h29 | 1h18 |
| 157 | CRJ200 / AE / 7 | ECP 04:50–OMA 19:44 CT | 10h13 | 14h29 | 4h16 |

## Proposed flights and demand

All clocks are local; +1 means the following calendar day. Opportunities are from the existing pinned O-D and relative-choice connection model. **They are not forecast passengers, seat-capped loads, or net new demand.** Both proposed routes are CRJ200; modeled opportunities exceeding aircraft capacity demonstrate connectivity strength, not an achievable load. The same passenger opportunity can be represented on multiple legs.

| Flight | Route / line / day | Flight | Departure–arrival | Local opportunity | Connecting opportunity | Total opportunity | Pair frequency, each way |
|---|---|---|---|---:|---:|---:|---|
| 2167 | 125 / AD / 15 | SYR–ROC | 06:06–06:45 ET | 0.3 | 0.9 | 1.2 | 3 → 4 |
| 2168 | 125 / AD / 15 | ROC–SYR | 07:25–08:04 ET | 0.3 | 82.9 | 83.1 | 3 → 4 |
| 2169 | 157 / AE / 7 | OMA–BHM | 20:30–22:38 CT | 2.2 | 60.6 | 62.9 | 1 → 2 |
| 2170 | 157 / AE / 7 | BHM–OMA | 23:23–01:31 +1 CT | 2.7 | 162.8 | 165.5 | 1 → 2 |

### Route 157: OMA–BHM

OMA arrival from MCI remains **19:44**. Departing at 20:30 gives a **46-minute OMA turn**. BHM arrival 22:38 supports the 23:15 SFB and VPS departures and 23:20 HOU departure, with 37–42 minutes to connect. These provide Florida Peninsula, Gulf Coast and Texas coverage.

The return leaves BHM at **23:23**, after a **45-minute aircraft turn**. It collects existing arrivals from SFB, SRQ, FLL, VPS, ECP, HOU, AUS, DAL, SAT, HRL and MCI; Florida Peninsula and Texas are the dominant geographic groups. AUS 22:37 and DAL 22:41 arrivals have 46 and 42 minutes to connect, respectively.

OMA arrival **01:31 +1** leaves **4h14** before Route 158's unchanged **05:45 OMA–MCI** departure. OMA remains the terminator; line AE's longest non-MX overnight run remains six nights, and existing MCI maintenance overnights are retained.

No existing flight needs retiming. This turn alone removes no qualifying O-D markets and slows no best itinerary; four markets have faster best itineraries. Its modeled newly connected markets have underlying O-D totaling 66.8, which is distinct from the opportunities allocated to the two added flights.

Important limitations: 14h29 of aircraft block and a day spanning ECP 04:50 CT to OMA 01:31 CT require a separate crew duty/rest and handoff plan. The 4h14 overnight is aircraft ground time, not a crew-rest allocation. Scheduled BHM departure is seven minutes before the existing 23:30 departure cutoff.

The higher-scoring OMA–MCI alternative requires advancing MFE–MCI by 60 minutes and MCI–OMA by 30 minutes. Its new OMA–MCI departs 19:54, MCI–OMA 21:23–22:12. Opportunities are 16.7 / 339.8, but the full audit slows 26 best itineraries, and MCI already has four daily flights each way. The current 20:38 OMA–MCI departure prevents a fifth departure from fitting after the unchanged 19:44 OMA arrival: the new departure would violate the spacing floor or the 21:00 destination cutoff. Prefer BHM's second frequency and preserved clocks.

### Route 125: use the SYR morning hold

The current HVN–SYR arrival remains **05:26**. Insert SYR–ROC **06:06–06:45**, ROC–SYR **07:25–08:04**, then move Flight **1811 SYR–PVD from 08:35–09:38 to 08:44–09:47**. Every later clock remains unchanged, including the 19:43 DAY terminator and Route 126's 05:50 DAY–HOU originator.

The ROC–SYR flight arrives before SYR's morning departure wave: FLL, PIE, SFB, SRQ, MCI and northeastern destinations, plus later connections inside the model's four-hour window. Florida Peninsula accounts for about 60.7 of the connecting opportunities. It improves 24 best itineraries in its individual audit. The outbound's 1.2 total opportunity is very weak: the rationale is positioning the aircraft for the useful ROC feeder.

All three added/adjacent turns are exactly **40 minutes**: following HVN arrival, at ROC, and before SYR–PVD. The SYR–PVD departure is also one minute before Bank 2 ends at 08:45. This is valid under current rules but has little operational slack.

The nine-minute retiming loses no existing qualifying connecting choices on Flight 1811 and adds one. Five PVD-bound best itineraries — SRQ, CAK, BUF, BTV and ABE — become nine minutes slower. No market loses all connections. Full-capture relative allocation on Flight 1811 changes from 70.3 to 67.0; this does not imply that 3.3 actual passengers are displaced.

DAY's late terminator could not accommodate a compliant evening round trip with unchanged clocks in the screened network. SDF–DAY advances of 30 and 60 minutes miss DAY banks; a 90-minute advance reaches a bank but still yields no compliant turn. Banks, destination departure cutoffs and pair spacing bind the available window. This bounded review is not a claim that no network-wide rebuild could ever work.

DAY's **10h07** aircraft overnight is preserved, along with its maintenance credit. Line AD's longest non-MX overnight run remains nine nights.

### Route 304: retain

The aircraft currently reaches HRL **19:42**, leaving **10h57** before Route 305's **06:39 HRL–MCI** departure.

An unchanged evening HRL–BHM turn was rejected by full pairing-spacing validation. Its 20:30 departure is only 114 minutes after the existing 18:36 HRL–BHM flight, below the applicable approximately 196-minute target, with no allowable exception.

A fully valid HRL–MCI turn can be created by advancing BLV–MCI **60 minutes** (15:30–16:34 → 14:30–15:34) and MCI–HRL **40 minutes** (17:15–19:42 → 16:35–19:02). New flying would be:

| Flight | Time CT | Total opportunity |
|---|---|---:|
| HRL–MCI | 20:00–22:27 | 1.8 |
| MCI–HRL | 23:07–01:34 +1 | 28.7 |

This adds **4h54** of block to a CRJ700, chiefly to carry a weak inbound and a modest outbound. Retiming removes the last qualifying OKC–HRL itinerary (underlying O-D 3.3) and makes seven best itineraries slower, notably BLV–SAT by 60 minutes and BLV–PHF by 55. A nearby HRL–MFE turn has only 0.9 / 0.4 modeled opportunities and entails the same retiming harm. Neither warrants the change.

## Combined verification and scope

The stored joint proposal passes structural, operating, overnight, planning and fixed gate/stand validation, with **zero blocking findings and zero hard-stop failures**. No new bank, inventory, curfew, turn, runway or maintenance waiver is used. Gate stand use remains 16 claims / 3,717 minutes; no passenger handling is assigned to stands. The applicable existing policy overrides remain in force.

Combined audit: **no markets lose all qualifying connections**, five best itineraries become nine minutes slower due solely to Flight 1811, and 28 improve. Original flight identities are preserved; Flight 1811 is the only clock change. The replay has 1,168 flights, 181 routes and 20 lines. Maintenance longest non-target overnight runs remain AA 7, AD 9, AE 6.

Screens use a bounded 5/15-minute grid, rank wide windows with one-stop marginal opportunities, then fully enumerate one/two-stop demand and validate selected options. Both the weak outbound demand and the effects of retiming are included. This is an aircraft schedule feasibility review, not crew legality, a fleet-capacity forecast, or an exhaustive network optimization.

The accepted v1.2.4 canonical now includes both turns. The prior round-three canonical and draft report remain saved as an immutable comparison snapshot. Exact cumulative replay, all released identities and the two authorized released clock changes (1739 and 1811) were verified. Latest-release regression remains **49 checks passed against v1.2.3**. Main and the live app were not changed.
