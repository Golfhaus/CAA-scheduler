# Schedule 7 v1.4.0 — Syracuse mini-bank strategic proposal

**Planning only; do not integrate into the canonical v1.4.0 draft.** Source is the accepted 1,257-flight `schedule_7_v1_4_0_draft` (R106 and R110 utilization changes already included). `main` remains released v1.3.3. All clocks local Eastern.

## 1. Every qualifying outstation hold before SYR

A reproducible source scan found **22 qualifying holds on 17 routes**. Each is at least 120 minutes between arriving at an outstation and departing that same station for SYR. Detailed flight IDs, scheduled and possible times, hold sizes and downstream flight IDs are in `outputs/schedule_7_v1_4_0_utilization/syr_hold_inventory.json`.

| SYR proposed arrival wave | Candidate returns | Count |
| --- | --- | ---: |
| M09, 08:55–09:55 | R110 HVN, R129 PHF, R162 BDL, R167 ALB | 4 |
| M12, 11:55–12:55 | R105 MHT, R106 HPN, R107 ISP, R108 ORH | 4 |
| M15, 14:45–15:45 | R103 ISP, R104 HVN, R110 MHT, R124 HPN, R160 BTV, R167 CAK | 6 |
| M17, 17:15–18:15 | R105 BGR, R106 HPN, R107 BDL, R108 BTV, R130 PWM, R131 ALB | 6 |
| M20, 20:15–21:15 | R124 HVN, R530 CAK | 2 |

Note: the R129 PHF-origin return can reach M09 only at 09:50 after an 08:25 departure inside PHF's existing B2; forcing a 09:15 SYR arrival violates the PHF bank assignment. No PHF bank addition is needed.

All five simultaneous **arrival-only** wave groups, including R129's corrected clock, pass native structural, overnight, planning, operating, physical gates and stands with zero effective errors. The 22 adjusted holds transfer **1,366 minutes** from outstations to SYR, but **do not by themselves add one minute of inflight utilization** or validate a better passenger network.

## 2. Coupled outbound feasibility

Twenty-one of the 22 returns have a same-route onward SYR departure; 18 can be individually moved forward 40 minutes after arrival inside an associated SYR mini-bank. The three failures are R107's midday ISP–SYR–BDL turn (BDL gate capacity), R110's HVN–SYR–MHT (same-pairing spacing) and R129's PHF–SYR–ROC (arrives too late for a departure in M09). The no-onward case is terminating R530.

Native group tests independently verify the three central waves with **15 paired arrivals/departures**, and all five waves with **18 pairs and four additional inbound-only returns**. Both pass zero-effective-error and fixed-inventory checks, retain 1,257 flights, 188 routes and 17 lines.

**Do not approve blanket retiming.** The passenger audit finds unacceptable tradeoffs:

| Scenario | Reasonable market gains | Losses | Faster | Slower |
| --- | ---: | ---: | ---: | ---: |
| Arrival-only central M12/M15/M17 | 2 | 9 | 12 | 206 |
| Arrival-only five waves | 2 | 11 | 15 | 258 |
| Paired central M12/M15/M17 | 3 | 19 | 190 | 207 |
| Paired all five | 4 | 23 | 207 | 289 |

Large-demand relationships worsened by indiscriminate re-banking include RFD→ROC, RFD→HPN, BDL→PIT and ALB→BNA. Operating feasibility is not commercial acceptability. These are geography-screened directional fastest reasonable itineraries and not flight loads.

## 3. Recommended selective initial two-bank proposal

**Create SYR-M15 and SYR-M17 as mini-banks, not new full banks yet.** Begin with four paired return/outbound retimings whose individual O-D-weighted fastest-path comparison is positive. These have now also passed combined native and commercial screens.

| SYR mini-bank | Route | Inbound / outbound pairing | Arrival / onward departure |
| --- | --- | --- | --- |
| M15 | R110 | MHT→SYR→PIT | 15:00 / 15:40 |
| M17 | R106 | HPN→SYR→BTV | 17:30 / 18:10 |
| M17 | R130 | PWM→SYR→BUF | 17:30 / 18:10 |
| M17 | R131 | ALB→SYR→ORH | 17:30 / 18:10 |

Native grouped check: **pass**, zero operating errors, no new gates, stands, aircraft or flights, current termination stations preserved. Passenger network versus accepted 1,257-flight v1.4.0 draft: **zero directional market gains or losses, 55 faster and 36 slower fastest reasonable itineraries**. O-D-weighted journey-time score is **+5,239 modeled passenger-minutes** (relative proxy only, not measured ridership or actual daily flight loads).

This wave has only one M15 routing initially, so M15 should remain provisional until two or more other useful routes join; M17 has a viable three-route cluster immediately. A fifth CAK-origin R167 pairing at M15 still preserves all directional market coverage, but worsens the O-D-weighted journey-time score to +3,266; it is not presently the first choice.

## 4. R160 and R107 within the bank strategy

**R160:** A fully validated alternative brings BTV→SYR forward into M15, advances SYR→PWM to 15:40 and adds **PWM 17:28–PHF 19:09; PHF 19:49–PWM 21:30**. This preserves PWM as the route terminator, creates two flights, and raises R160's inflight flying from 5h44m to **9h06m**. Paired with the four selected bank movements, the proposal has **1,259 flights, zero operating errors, one reasonable coverage gain (FWA→PWM) and one loss (MCI→PWM, underlying directional O-D 7.2/day), 74 faster and 53 slower reasonable itineraries**, with a +8,667 weighted relative score. Do not accept the loss without first testing MCI→PWM replacement connections.

**R107:** A simple earlier ISP→SYR return can feed M12, but moving its SYR→BDL outbound earlier causes BDL gate conflicts. Separately, moving BDL→SYR earlier into M17 and advancing SYR→CAK passes native checks, yet removes the reasonable BDL→PIT option (20.2/day directional O-D) and causes a strongly negative demand-weighted journey-time change. Therefore **do not integrate either R107 mini-bank adjustment in this first phase**. Investigate connecting protection, alternative BDL timings, and the previously validated SYR–BWI–BDL–SYR A–B proposal instead.

## 5. Bank promotion and future additions

Add core mini-banks first and audit network changes, including one-stop origin/destination pairs and existing fastest-path impacts. A mini-bank should be promoted to a full bank only if there are enough simultaneous inbound/outbound flights (ideally at least four each), directional demand/connectivity warrant it, and combined physical/overnight/maintenance and passenger audits pass. SYR's fixed gate inventory must never increase by implication.

Potential phase-two waves: M12 has four theoretical inbound candidates but causes high-demand RFD→HPN loss if paired wholesale; redesign the offending outbound before promotion. M09 has four theoretically feasible arrivals but only two individually feasible paired departures and poor modeled network results. M20 has only two returns and low priority. None should be promoted or added merely because the infrastructure screening passed.

## 6. Reproducibility, approval gate, and links

All evidence is in `outputs/schedule_7_v1_4_0_utilization/`:

- `syr_hold_inventory.json` — all 22 holds.
- `syr_single_return_feasibility.json` — individual early-return validation.
- `syr_group_feasibility.json` — grouped 22-return gate/operation validation.
- `syr_outbound_continuations.json` — individually tested onward departures.
- `syr_paired_banks_native.json`, `syr_paired_bank_network.json` — broad paired variants and negative network impacts.
- `syr_single_paired_network.json` — individually ranked pairs with demand-weighted implications.
- `syr_selective_native.json`, `syr_selective_network.json` — selective four-route, six-route, and R160-extension scenarios.
- `syr_bank_continuations.json` — R160 growth scenario and failed R107 growth alternative.

**No changes from this initiative have been integrated into the accepted 1,257-flight v1.4.0 draft or published to main.** The next approval should concern whether to start drafting the selective core four, R160 only after preserving MCI→PWM, or a revised bank structure.
