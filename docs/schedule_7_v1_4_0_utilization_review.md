# Schedule 7 v1.4.0 utilization review

Status: unpublished; released app default remains v1.3.3.

## Accepted draft

The published v1.3.3 schedule plus accepted R106 and R110 overlays builds `data/schedules/schedule_7_v1_4_0_draft` using `scripts/build_schedule_7_v1_4_0_draft.py`.

- R106: BTV-SYR-BTV late turn and minor retimings; 5h48m to 7h32m daily flying.
- R110: DAY-SYR-DAY late turn and six-minute PIT-DAY retiming; 6h34m to 9h40m. Logical DAY-M0 bank 00:00-00:45, with bank count 10 (no physical gate increase).
- Draft: 1,257 flights, 188 routes, 17 lines; zero effective operating errors; structural, overnight, planning and physical inventories pass.

## Unaccepted P2P / A-B-C candidates

R160: BTV-PHF-SYR instead of BTV-SYR, coordinating earlier ACY-SYR and SYR-BTV flights and the 15:25 PHF-SYR departure. Adds 2h13m of daily flying (7h57m total), native validated.

R107: SYR-BWI-BDL-SYR instead of SYR-BDL-SYR; keeps BDL-SYR direct, shifts another morning SYR-BDL flight by six minutes, adds 1h21m (7h08m total), native validated.

Together, these would yield 1,259 flights and retain 188 routes and 17 lines, with zero effective operating errors. They remain output-only candidates, NOT part of the accepted draft.

A commercial screen versus the accepted draft found 8 newly covered reasonable directional markets, 4 lost, 45 faster fastest journeys, and 56 slower. Gains include BDL-BWI (32.9 underlying directional O-D per day), BTV-RDU (18), BTV-CHS (8), BTV-DAL (7.8), BTV-MSY (5.3), BTV-SAV (3.8), BTV-VPS (0.9), and BTV-MLB (0.5). Losses: BTV-DAB (0.9), MDT-BDL (0.8), ACY-FWA (0), BTV-ACY (0). O-D is NOT forecast loads.

References: `outputs/schedule_7_v1_4_0_utilization/r160_r107_bwi_combined_native.json`, `bwi_bdl_network_comparisons.json`, and `individual_network_comparisons.json`.

Other technically feasible but lower-value options were BTV-PWM-SYR, BTV-ROC-SYR, BDL-BUF-SYR, BDL-ROC-SYR and BDL-PVD-SYR. The last three damage important BDL-PIT and BDL-CAK connecting options.

Next: review the 56 slower journeys and SYR-BDL directional connectivity before deciding whether to accept the R160/R107 alternatives; keep main unchanged until explicitly authorized.
