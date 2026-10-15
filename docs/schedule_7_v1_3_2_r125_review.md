# R125 PVD hold investigation

Reviewed October 14, 2026 against cumulative v1.3.2 draft commit `64c4ab402a22a6813ce230d1c5e9a8bb30300d07`, including accepted R501/R175 changes. **This recommendation is not applied.** The canonical draft remains at 1,216 flights and publication remains unauthorized.

## Recommendation

Insert a CRJ200 PVD–BWI round trip during R125's **5h11 PVD hold**, 07:09–12:20. Keep all seven existing R125 flights at their current clocks. Delay F1418, R346 PHF–BWI, by two minutes to fit BWI's fixed two-gate inventory; no subsequent R346 flight moves.

| Flight / sector | Proposed times, ET | Change |
|---|---|---|
| R125 F1878 HVN–SYR | 04:30–05:26 | Unchanged |
| R125 F1811 SYR–PVD | 06:06–07:09 | Unchanged |
| New R125 PVD–BWI | **08:30–09:43** | New flight |
| New R125 BWI–PVD | **10:25–11:38** | New flight |
| R125 F1812 PVD–SYR | 12:20–13:23 | Unchanged |
| R125 F1658 SYR–DAY | 14:05–15:38 | Unchanged |
| R125 F1849 DAY–SDF | 16:20–17:08 | Unchanged |
| R125 F1850 SDF–DAY | 18:55–19:43 | Unchanged |
| R125 F2173 DAY–IND | 21:35–22:18 | Unchanged |
| R346 F1418 PHF–BWI | **09:17–10:05** | Two minutes later, from 09:15–10:03 |

R125 grows from **seven to nine flights**, with **6h54→9h20 block**, an increase of **2h26**. No additional aircraft is needed, no endpoint or overnight rotation changes, and the existing IND terminator remains intact. The PVD sit becomes **81 minutes before BWI and 42 afterward**, with 42 at BWI. R125's longest same-day hold becomes **1h52**, at DAY before the IND flight; its other longer hold is 1h47 at SDF. Both are too short for an independent out-and-back with 40-minute turns.

## Demand and passenger impact

The pinned matrix has **40.3 daily PVD→BWI and 41.3 BWI→PVD O-D passengers**, with no existing nonstop. Those are underlying market totals, not a forecast of flight loads. BWI has the largest local demand among the physically suitable simple PVD out-and-back options tested: PIT is 15.6 / 15.9, and PHF is 28.4 / 28.3 plus connecting value but already has six daily flights each direction.

Both PVD–BWI directions improve from **2h53 connecting to 1h13 nonstop**, saving **1h40**. The same app enumeration and geographic screen preserve **every existing itinerary choice**, with no lost direct/one-stop coverage and no nonstop downgrade. The change provides nonstop service in two existing one-stop markets; it does not claim to open previously unserved one-stop coverage.

F1418's two-minute shift slows exactly three geographic fastest journeys, all to BWI:

| Market | Underlying O-D/day | Before → after |
|---|---:|---|
| RDU→BWI | 58.1 | 5h33 → **5h35** |
| MYR→BWI | 41.7 | 4h53 → **4h55** |
| ILM→BWI | 13.2 | 4h48 → **4h50** |

No connection disappears. These are the explicit costs of the otherwise unchanged-clock PVD insertion.

## Why the two-minute adjustment is necessary

At BWI, the existing MAX9 R715 claim runs 08:54–09:35, R347 runs 09:15–10:05, and R346 normally arrives at 10:03 and holds until 12:25. The new 09:43–10:25 turn would briefly require a third gate at 10:03–10:05. Delaying R346's arrival to **10:05** lets it use the gate vacated by R347 while the new PVD aircraft uses the other gate. The accepted R175 11:43–12:23 BWI turn remains feasible as well.

PHF departure 09:17 stays in existing PHF B2. R346's previous arrival from DAY at 08:20 now leaves a 57-minute PHF turn; its BWI hold shrinks from 142 to 140 minutes before the unchanged 12:25 PHF return. There is no cascade, physical-inventory increase or new policy exception.

## Alternatives and limits

Eleven timetable variants were screened. Four pass structural, operating, planning, overnight-turn and physical inventory checks: the recommended BWI repair and three timings of a PIT turn. The BWI repair has **zero effective errors/hard stops**, unchanged fleet allocation, and unchanged stand use of **15 claims / 3,061 minutes**. Existing AM maintenance grace remains reported; the inherited runway-data check remains unavailable.

- **BWI without another-route timing change:** four departures from 07:49 through 08:30 were tested; all fail BWI's fixed two-gate inventory. The small R346 correction solves the collision without changing R125's existing clocks.
- **PIT:** a 07:49–09:21 flight returning 10:01–11:33 fits with no retimings and no lost choices. It also gives two faster nonstop journeys, but its 15.6 / 15.9 underlying daily O-D is substantially weaker than BWI's 40.3 / 41.3.
- **PHF:** three tested turn timings fit the aircraft and physical gates, but adding them creates a seventh daily flight each direction and fails the six-flight ceiling. The existing six PHF pairs already provide substantial service; no ceiling waiver is proposed merely to fill this hold.
- **SYR:** the earliest new PVD departure, 07:49, would arrive SYR at 08:52, after B2 ends at 08:45. Waiting for B3 arrival at 10:30 and departing at 11:10 would return PVD at 12:13, leaving only seven minutes before the existing 12:20 flight. A 40-minute turn would push the later SYR–DAY departure beyond its existing bank. No new bank or turn waiver was assumed.
- **Larger local markets:** SFB/FLL/PGD/PIE/RFD are too long for the unchanged hold. RDU is the closest stronger local candidate at 42.2 / 42.7 daily O-D, but its 105-minute blocks require 330 minutes including three 40-minute turns, against only 311 available. Extending the hold by 19 minutes would force SYR–DAY to 14:22, after its bank's 14:15 end.

The first HVN departure is already at the 04:30 operating floor, and the following SYR turn is exactly 40 minutes. Starting R125 earlier is therefore not a source of extra time.

## Reproduction and status

```bash
python scripts/build_schedule_7_v1_3_2_draft.py
python scripts/review_schedule_7_v1_3_2_r125.py
node scripts/audit_schedule_7_v1_3_2_r125.mjs
```

The proposed overlay is `config/proposals/schedule_7_v1_3_2_r125_bwi.json`; the build does not apply it. Evidence is recorded in `data/analyses/schedule_7_v1_3_2_r125_review.json`. The source canonical SHA is pinned in the native screen. Nothing in R125, R346 or the published app has been changed by this investigation.
