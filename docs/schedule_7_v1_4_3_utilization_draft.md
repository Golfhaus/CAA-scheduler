# Schedule 7 v1.4.3 — spare aircraft-day utilization working draft

Date: 2026-10-21. Based **exclusively** on published `schedule_7_v1_4_2`. **Not published and not approved for merge.** User requested research into better utilization for the newly added R177, R178 and R359. The draft does not consume additional spare aircraft, add airport gates/stands, alter existing flights, or relax operating requirements.

## Recommended draft route-day extensions

**R177 CRJ200 / AF day 7 (six legs total):**
- DAY–CMH 07:30–08:05; CMH–DAY 08:45–09:20 (40-minute feeder into unchanged 10:00 DAY–SRQ departure)
- Existing DAY–SRQ 10:00–12:25; SRQ–DAY 13:10–15:35 untouched
- DAY–SFB 16:15–18:20; SFB–DAY 19:05–21:10

**R178 CRJ200 / AC day 9 (six legs total):**
- SYR–CHS 05:10–07:10; CHS–SYR 07:50–09:50 (60-minute feeder into unchanged 10:50 SYR–RDU departure)
- Existing SYR–RDU 10:50–12:20; RDU–SYR 13:15–14:45 untouched
- SYR–BDL 15:30–16:20; BDL–SYR 17:05–17:55 (45-minute inbound connection from RDU)

**R359 CRJ700 / AH day 6 (six legs total):**
- BNA–FLL 06:00 CT–09:05 ET; FLL–BNA 09:50 ET–10:55 CT
- BNA–DAL 13:00–14:45 CT; DAL–BNA 15:30–17:15 CT
- Existing BNA–BHM 20:10–21:25 CT; BHM–BNA 22:10–23:25 CT untouched

Flight numbers in deterministic draft: R177 extensions 2283–2286; R178 2287–2290; R359 2291–2294.

## Native feasibility and utilization

Cumulative 12-added-flight screen (GitHub Actions run 39653043675) and follow-up full audit: 1,284 flights, 191 routes, 17 routing lines; **structural PASS, overnight PASS, gate export PASS, planning PASS, zero effective operating errors**. Complete published-route minimum 40-minute turns retained. All 12 added legs fit the same three existing aircraft days; no new aircraft required.

| Route | Total flying before → after | Critical 06–22 flying before → after | Critical utilization before → after |
|---|---|---|---|
| R177 | 290 → 610 min | 290 → 610 min | 30.2% → 63.5% |
| R178 | 180 → 520 min | 180 → 470 min | 18.8% → 49.0% |
| R359 | 150 → 610 min | 75 → 535 min | 7.8% → 55.7% |

Independent `web/opportunity-analysis.mjs` passenger model (geographically reasonable directionals), cumulative vs published v1.4.2: **19 new reasonable connections, 36 fastest reasonable journeys improved, zero lost, zero slower**.

Key improvements:
- BNA→DAL 411→105 min; DAL→BNA 214→105; city pair 330 daily directional-summed O-D.
- BNA→FLL 263→125 min; FLL→BNA 262→125; city pair ~446 daily directional-summed O-D.
- RDU→BDL 427→185 min, 49 daily O-D. 
- CMH→SRQ now one stop via DAY, 220 min; 43.8 daily O-D and previously no geographically reasonable short itinerary.
- TYS→SFB 310→235 min; 51.7 daily O-D.
- CHS→HPN 294→264 min; 24.2 daily O-D.

These are source O-D market volumes, **not** forecast ticket sales. New routes to BNA (FLL/DAL) would have very high market demand relative to 70-seat-class CRJ700 capacity. Verify actual flight block times, commercially appropriate aircraft seating, connection flows, and market economics before a v1.4.3 release; candidate block times are engineering estimates based on flight length and existing network precedent.

## Further options reviewed but not selected

- R177 evening DAY–PIE and DAY–PGD passed independently, but DAY–SFB delivers a stronger combined set of connection opportunities and serves additional larger demand markets. DAY–BNA failed hard airport inventory and bank checks.
- R178 evening SYR–CMH failed CMH fixed gate capacity. The initial morning SYR–CHS return at 09:55 missed SYR-M09 bank alignment; returning five minutes earlier at 09:50 with a valid 40-minute CHS ground turn **passed** in the combined draft.
- R359 morning BNA–DAL/FLL/PIE/AUS all passed individually. The chosen BNA–FLL morning and BNA–DAL afternoon **also pass cumulatively**, without disturbing late BHM service.
- Further morning/evening optimization is possible, but avoid adding weak flying simply to reach a utilization target.

## Reproduce

- `scripts/build_schedule_7_v1_4_3_candidate.py`: native-valid cumulative draft builder.
- `scripts/v143_cumulative_passenger_audit.mjs`: whole network before/after demand-weighted audit.
- `scripts/v143_utilization_delta.mjs`: operating- and critical-period flying audit.
- `scripts/v143_utilization_screen.mjs`: discovery screen.
- `scripts/v143_native_turn_screen.py`: individual hard gate/turn screen.
- `web/schedules.json` must remain pinned to v1.4.2 until user authorizes publication and full latest-only regression passes.
