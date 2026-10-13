# Schedule 7 v1.3.1 draft — DSM operating day

Accepted into the unpublished draft October 13, 2026. Publication remains separate; the app default is v1.3.0. This round follows the accepted RFD and northeast/Florida work.

## Selected changes

Use R154's existing MCI hold for an additional CRJ200 DSM turn. Keep the morning MCI flights, whose connections are valuable. Move the existing R516 RFD–DSM round trip 75 minutes later, using its existing RFD hold. No spare aircraft is required and no downstream flight is retimed.

All times below are Central.

| Flight | Market | Before | Draft |
|---|---|---|---|
| F1210, R516 | RFD–DSM | 06:00–07:00 | 07:15–08:15 |
| F1209, R516 | DSM–RFD | 07:40–08:40 | 08:55–09:55 |
| F2215, R154 | MCI–DSM | New | 14:00–14:50 |
| F2216, R154 | DSM–MCI | New | 15:35–16:25 |

DSM departures become **07:25 MCI, 08:55 RFD, 09:05 MCI, 10:45 MCI, 15:35 MCI**. Arrivals become **08:15 RFD, 09:45 MCI, 14:50 MCI, 20:45 MCI, 22:26 MCI**. The long interval between the 10:45 departure and 20:45 arrival is interrupted by useful afternoon activity. The remaining longest interval between passenger operations is 5h10, from 15:35 to 20:45; this effort does not claim a fully balanced all-day schedule.

R154 turns are 43 minutes at MCI before the new departure, 45 at DSM and 49 at MCI before its unchanged 17:14 SGF departure. This uses existing MCI B6/B8. The prior 3h57 MCI hold becomes productive flying; daily block rises by 1h40. R516 reaches RFD at 09:55 with exactly 40 minutes before the unchanged 10:35 SYR departure. Its idle time moves before the DSM turn; total flying and existing SYR connections are unchanged.

## Demand and passenger benefit

The existing RFD market records 40.8 daily DSM→RFD and 41.4 RFD→DSM O-D passengers. The later time is a modest distribution improvement within the existing aircraft's available slack, not a modeled increase in bookings.

The new MCI turn is supported chiefly by connections: local demand is only 0.8/day MCI→DSM and 0.9/day DSM→MCI. Eligible local/one-stop market totals are 175.1 and 79.5/day. After accounting for existing itinerary alternatives and screening slow options, competitive equal-choice indices are about 60.4 inbound and 33.6 outbound. These are screening indices, **not forecast aircraft loads**. Market totals overlap and must not be summed as unique passengers. Nonstop competitors within the CAA timetable are excluded from connecting-market claims; geography uses the existing 2.25 distance screen.

The changes add nine one-stop directional markets: RDU→DSM, DSM→RDU, JAX→DSM, PHF→DSM, DSM→PHF, SYR→DSM, DSM→SHV, DSM→SGF and DSM→COU. Their recorded O-D totals 46.6/day; the zero-demand COU option is incidental and is not used to justify flying.

Nineteen geographically suitable fastest journeys improve; 20 improve in the raw timetable. No existing itinerary choice, one-stop coverage or fastest journey is lost or slowed relative to round 3.

| Direction | Before fastest | Draft fastest |
|---|---|---|
| RDU→DSM | 5h25, two connections | 3h55, one connection |
| JAX→DSM | 6h00, two connections | 4h00, one connection |
| DSM→PHF | 5h31, two connections | 4h22, one connection |
| DSM→SAT | 5h11, one connection | 3h36, one connection |
| CLT→DSM | 4h42, one connection | 3h50, one connection |
| SFB→DSM | 4h21, one connection | 4h05, one connection |

Some new one-stop choices, including DSM→RDU, reduce the connection count without beating the retained fastest two-stop journey. Existing northeast coverage to PGD/DAB/FLL/PIE/SFB/SRQ remains intact.

## R150 and rejected alternatives

R150 remains unchanged. Its 09:05 DSM originator feeds MCI's 10:35 departures. The 105-minute JAX and 63-minute BHM holds cannot fit a round trip with three mandatory 40-minute turns, even before flight time. Advancing DSM–MCI alone merely moves idle time to MCI and introduces physical gate conflicts at the tested earlier bank times.

A physically valid earlier R150 option replaces DSM–MCI with DSM 05:27–DAY 08:04, DAY 09:10–MCI 09:55, preserving all subsequent R150 clocks. It increases flying by 2h32 but has a DSM–DAY competitive opportunity index of just 9.4. It slows DSM→SFB by 100 minutes, and the combined DAY/afternoon option slows 12 geographic fastest journeys. This does not meet the user's demand-first priority and is not adopted.

Relocating the existing midmorning DSM turn to noon or afternoon is also rejected: it removes 11 or 13 geographically suitable one-stop markets, respectively, including useful BNA and FLL service. The additional afternoon turn provides the benefit without those losses. A later RFD turn would require changing its SYR flying or transferring it to another aircraft; 75 minutes is the maximum simple shift preserving the next 40-minute turn.

## Validation and reproduction

The cumulative draft has **1,214 flights, 184 routes and 19 lines**. Fleet use remains MAX9 24/35, CRJ900 28/45, CRJ700 56/65 and CRJ200 76/80. Structural, operating, planning, maintenance/overnight and physical gate checks pass with zero effective operating errors and zero hard stops. The existing runway-data check remains unavailable. No bank windows, physical inventories, operating policies, destinations or pinned demand data are changed.

System stand use is 15 claims / 3,061 minutes, compared with 16 / 3,595 in round 3. All passenger operations remain at gates. The existing round-3 network tradeoffs remain documented separately; the zero-loss statement applies to this DSM round only.

```bash
python scripts/build_schedule_7_v1_3_1_draft.py
node scripts/audit_schedule_7_v1_3_1_connections.mjs
node scripts/audit_schedule_7_v1_3_1_dsm.mjs --accepted
```

The builder reproduces round 3 from its original configuration, verifies its SHA before applying round 4, and saves the immutable comparison input. The accepted network report records source, baseline and demand fingerprints. Optional screening uses `review_schedule_7_v1_3_1_dsm.py` and the DSM audit script without `--accepted`; rejected alternatives remain local review inputs rather than release artifacts.
