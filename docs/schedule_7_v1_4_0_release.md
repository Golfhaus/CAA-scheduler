# Schedule 7 v1.4.0 release — October 19, 2026

The user authorized publication to `main` after review of the accepted 1,259-flight v1.4.0 draft. The application defaults to v1.4.0 upon merge.

## Summary

| Item | v1.3.3 | v1.4.0 |
| --- | ---: | ---: |
| Flights | 1,253 | **1,259** |
| Routes | 188 | **188** |
| Aircraft routing lines | 17 | **17** |
| Effective operating errors | 0 | **0** |

Fleet size and fixed gates/stands do not change. Native structural, overnight, planning, operating and physical inventory validation all pass.

## Accepted changes

- R106 (AC day 6): Retimes HPN-SYR and SYR-BTV, then adds BTV-SYR-BTV evening service. Flying increases from 5h48m to 7h32m.
- R110 (AM day 12): PIT-DAY moves six minutes earlier and DAY-SYR-DAY is added. Flying rises from 6h34m to 9h40m. Creates logical DAY-M0 00:00-00:45, adding one bank but no physical gates.
- SYR mini-banks M15 (14:45-15:45) and M17 (17:15-18:15): R110 MHT-SYR-PIT pairs through M15, R106 HPN-SYR-BTV, R130 PWM-SYR-BUF and R131 ALB-SYR-ORH through M17. SYR logical bank count becomes nine.
- R160 (AM day 4): BTV-SYR at 14:08-15:00, SYR-PWM at 15:40-16:48; adds PWM-PHF 17:28-19:09 and PHF-PWM 19:49-21:30. Flying rises from 5h44m to 9h06m while preserving ACY originator and PWM terminator.

R107 was reviewed extensively but remains unchanged; other blanket SYR mini-bank options were rejected because of unfavorable connection impacts.

## Passenger connectivity review

Against the intermediate 1,257-flight v1.4.0 draft containing only R106 and R110, the approved M15/M17 and R160 extension produced a previously reviewed directional comparison of one geographically reasonable market gain (FWA-PWM, 0.6 underlying daily directional O-D) and one loss (MCI-PWM, 7.2); 74 faster and 53 slower fastest reasonable itineraries. The one-stop MCI-PWM itinerary lost is documented and has not been automatically restored. User approved publication with this tradeoff visible.

Audit: `outputs/schedule_7_v1_4_0_utilization/syr_selective_network.json`, scenario `positive_four_plus_R160`. Demand sizes are directional underlying market averages, not forecast airline boardings.

## Deterministic reproduction and regression

1. `python scripts/build_schedule_7_v1_4_0_draft.py` builds the exact accepted cumulative draft from the released v1.3.3 canonical and three accepted overlays.
2. `python scripts/prepare_schedule_7_v1_4_0_release.py` prepares validated release assets and changes the web manifest default to `schedule_7_v1_4_0`.
3. `bash scripts/run_latest_regression.sh` checks the released current default.
4. `python -m caa_scheduler build-web --output dist` packages the app default and artifacts.

This procedure must succeed on the candidate branch before merge. The previous version stays archived for reference; regressions are latest-only.
