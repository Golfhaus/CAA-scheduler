# Schedule 7 v1.4.1 — CRJ200 critical utilization review

**Status:** provisional working draft, NOT approved for publication. Published main/default is Schedule 7 v1.4.0.

## Objective and starting point

Review routes **105, 106, 107, 108, 167 and 162** jointly for productive flying, emphasizing the SYR M15, M17, B5 and B6 waves and additional morning mini-bank opportunities. Maintain fixed airport inventories, curfews, repeating maintenance, overnight routing continuity, and passenger-network value. R106 was improved in v1.4.0; do not force a low-value change.

Initial published 1.4.0 fleet: 1,259 flights, 188 routes, 17 lines.

| Route | Baseline total flying | Provisional draft | Status |
| --- | ---: | ---: | --- |
| R105, AC day 5 | 6h46m | **9h26m** | Provisional BGR service addition |
| R106, AC day 6 | 7h32m | 7h32m | Retain previous v1.4.0 improvements |
| R107, AC day 7 | 5h47m | 5h47m | Pending holistic connection-preserving rebuild |
| R108, AC day 8 | 6h09m | 6h09m | Candidate triangles rejected commercially |
| R167, AC day 9 | 6h54m | 6h54m | No compelling demand-backed growth yet |
| R162, AM day 6 | 6h53m | **9h33m** | Provisional SYR M09/BGR morning turn |

## Provisional draft changes

Deterministic overlay: `config/optimizations/schedule_7_v1_4_1_r105_r162_provisional.json`.
Rebuild: `python scripts/build_schedule_7_v1_4_1_draft.py`.
Provisional canonical and native reports: `data/schedules/schedule_7_v1_4_1_draft/`.

### R162 — productive morning BGR turn

- Retimes BDL–SYR flight 2102 from 10:05–10:59 to **08:16–09:10**, reducing the long BDL sit after arriving 06:53.
- Adds logical SYR mini-bank M09 **08:55–09:55** and SYR–BGR flight **2269 09:50–11:10**.
- Adds BGR–SYR flight **2270 11:55–13:15**, reaching SYR B4.
- Preserves all original flights, PHF–MDT service and the ILM terminator, with sufficient turns and existing physical gates.
- Adds 160 inflight minutes to R162, moving total from 6h53m to 9h33m. Critical-period flying increases by 160 minutes.

### R105 — evening BGR–SYR–BGR extension

- Retimes MHT–SYR to **11:45–12:45**, arriving SYR M12 **11:55–12:55**.
- Advances SYR–BGR to 13:25–14:45, BGR–SYR to 15:25–16:45 (SYR B5), and SYR–BGR to 17:25–18:45 (SYR M17).
- Adds BGR–SYR flight **2271 20:10–21:30**, then SYR–BGR flight **2272 22:10–23:30**, aligned to SYR B7. Retains the BGR terminator and next-day BGR originator.
- Adds 160 total inflight minutes to R105, moving total from 6h46m to 9h26m; 80 of those minutes fall within the 06:00–22:00 critical period.

SYR now has 11 logical banks, including new M09 and M12; **no extra physical gates or stands** are allocated.

## Combined validation and commercial screen

R105 and R162 were native-screened individually and combined before building the provisional draft. Combined result:

- **1,263 flights, 188 routes, 17 routing lines**, +4 flights from v1.4.0.
- Structural, planning, overnight and physical gate/stand validation all pass; **zero effective operating errors**.
- Commercial comparison against published v1.4.0: **12 new geographically reasonable directional markets, zero lost, 70 faster and 39 slower fastest reasonable itineraries**, with a modest +454 O-D-weighted passenger-minute planning score. This is not forecast passenger boardings.
- Potentially material tradeoffs remain: BDL→PIE (underlying O-D 105/day) experiences an 81-minute slower fastest itinerary in the screened comparison. PIE→BGR also becomes slower under R105's late shuttle. These require review before release.
- Sources: `outputs/schedule_7_v1_4_1_utilization/combined_screen.json` and the run evidence for `scripts/audit_schedule_7_v1_4_1_combined_network.mjs`.

**This is a provisional, reproducible draft—not a final release decision.**

## Remaining four routes and next moves

### R107

A native-validated **ISP–PHF–SYR** midday A–B–C path would raise flying from 5h47m to 7h44m and use existing PHF banks plus SYR M15. It creates eight geographically reasonable market gains but loses three, notably ISP→BNA. More importantly, the fastest RFD→BDL journey becomes 80 minutes slower; RFD→BDL's underlying daily directional O-D is about 105.4. Do not adopt until this and other BDL connections are protected. Other ISP–ROC–SYR and ISP–PIT–SYR triangles are operationally feasible but lose ISP connections and rank lower.

Prioritize a holistic R107 rebuild preserving the 14:05 SYR→BDL bank-dependent connectivity, or add a compensating appropriately timed BDL frequency from another CRJ200 route rather than stretching its late CAK terminator. Existing M17 and B6 have usable opportunities, but preserving strong hub flows matters more than filling unused minutes.

### R108

BTV–ROC–SYR, BTV–BUF–SYR and BTV–PWM–SYR triangles all pass native checks and each add one leg, but all make **BTV→RFD** (about 30.1 directional O-D/day) 76 minutes slower and lose BTV→MDT geographic coverage. They are not recommended in their screened forms. Consider a SYR bank-bound afternoon rebuild that preserves BTV→RFD, rather than merely diverting the current BTV→SYR return.

### R167

A compact **ALB–BTV–ALB** pair can fit between the existing SYR→ALB and ALB→SYR flights. It passes native constraints, adds 80 minutes and two flights, with no detected itinerary losses, but underlying ALB–BTV O-D is only around 0.6 passengers/day **per direction** and no other journey-time gains were detected. Do not use an aircraft for such low-demand flying solely to improve utilization. Study stronger outstation-demand opportunities or modest timing changes.

### R106

Existing v1.4.0 R106 already flies 7h32m. A screened HPN–BWI–SYR morning triangle violates BWI physical gate inventory and would disrupt the morning. Retain the route for now; do not force it back below its previous useful connection performance.

## Governance

No v1.4.1 release package, app manifest/default change, pull request to main, or publication is authorized. The provisional R105/R162 draft should remain available for further review and modifications. User review is needed before considering it accepted for release.
