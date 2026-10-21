# Schedule 7 v1.4.2 release notes

Date: October 21, 2026. Approved by user for validation and publication. **Release remains a candidate until the PR is merged and the default points to v1.4.2.**

Changes relative to published v1.4.1:
- R177 DAY–SRQ–DAY CRJ200 in line AF, extending 11→12-day cycle.
- R178 SYR–RDU–SYR CRJ200 in line AC, extending 10→11-day cycle, with flight 1879 HVN–SYR advanced 50 minutes and bank assignments updated.
- R359 BNA–BHM 20:10–21:25 and BHM–BNA 22:10–23:25 CRJ700 in line AH, extending 9→10-day cycle. Flight #1235 BLV–BNA and #1236 BNA–BLV advanced 35 minutes to protect physical BNA gates; connects BNA↔ECP via BHM within 30–240 minute window.
- Flight #1357 BLV–MCI shifted six minutes later, providing BLV→HOU via MCI.
- Flight #1077 MCI–BNA shifted 11 minutes earlier, providing OMA→BNA via MCI.
- Flight #1080 BNA–MCI advanced to 16:56–18:25, with MCI arrival bank changed from B10 to B9; creates BNA→OMA via MCI with a 30-minute transfer to #1636.
- Schedule 7-specific operatingPolicy.hubCountCeilingEnabled=false. Effective minimum flight count and physical inventory rules remain strictly enforced. The validator's default for all other schedules remains true.

Provisional candidate: 1,272 flights, 191 routes, 17 aircraft lines; two CRJ200 and one CRJ700 aircraft released from spare pool through extension of existing lines. Initial full native structural, overnight, operating, physical gate, and planning validation found zero effective operating errors. Full latest-only regression is the release gate and must pass before publication.

There is no new hub-count ceiling policy for Schedule 8. Revisit in Schedule 8 setup.
