# Schedule 7 v1.4.2 release notes

Published October 21, 2026, after user approval and validation. [PR #44](https://github.com/Golfhaus/CAA-scheduler/pull/44) merged the release into `main`, and the [web schedule manifest](../web/schedules.json) sets v1.4.2 as the application default. The [canonical schedule](../data/schedules/schedule_7_v1_4_2/canonical_schedule.json) is the published Schedule 7 baseline.

Changes relative to published v1.4.1:
- R177 DAY–SRQ–DAY CRJ200 in line AF, extending 11→12-day cycle.
- R178 SYR–RDU–SYR CRJ200 in line AC, extending 10→11-day cycle, with flight 1879 HVN–SYR advanced 50 minutes and bank assignments updated.
- R359 BNA–BHM 20:10–21:25 and BHM–BNA 22:10–23:25 CRJ700 in line AH, extending 9→10-day cycle. Flight #1235 BLV–BNA and #1236 BNA–BLV advanced 35 minutes to protect physical BNA gates; connects BNA↔ECP via BHM within 30–240 minute window.
- Flight #1357 BLV–MCI shifted six minutes later, providing BLV→HOU via MCI.
- Flight #1077 MCI–BNA shifted 11 minutes earlier, providing OMA→BNA via MCI.
- Flight #1080 BNA–MCI advanced to 16:56–18:25, with MCI arrival bank changed from B10 to B9; creates BNA→OMA via MCI with a 30-minute transfer to #1636.
- Schedule 7-specific operatingPolicy.hubCountCeilingEnabled=false. Effective minimum flight count and physical inventory rules remain strictly enforced. The validator's default for all other schedules remains true.

The published package contains **1,272 flights, 191 routes and 17 routing lines**. Extending existing lines used two CRJ200 and one CRJ700 aircraft from the spare pool. The [release report](../data/schedules/schedule_7_v1_4_2/release_report.json) records zero effective operating errors and zero hard-stop failures. The [Pages deployment run](https://github.com/Golfhaus/CAA-scheduler/actions/runs/39633525592) passed the current-release regression gate and deployed the console.

There is no new hub-count ceiling policy for Schedule 8. Revisit in Schedule 8 setup.
