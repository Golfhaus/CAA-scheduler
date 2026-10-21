# v1.4.2 — physically valid BNA/BHM ECP connection

GitHub Actions run 39607692691 / job 119248064094 on October 21, 2026 verified a narrowed R359 two-leg pattern within the cumulative candidate (tactical MCI retimings + R177 + R178 with Schedule 7-only hub-count cap removed). The new BNA–BHM routing uses CRJ700 line AH extra day, two flights:
- BNA–BHM 20:10–21:25
- BHM–BNA 22:10–23:25

Re-time both flights in existing R512:
- flight 1235 BLV–BNA 17:25–18:25 (35 minutes earlier)
- flight 1236 BNA–BLV 19:05–20:05 (35 minutes earlier)

These create legal BNA→BHM→ECP 31-minute transfer to BHM–ECP #1797 departing 21:56, and ECP→BHM→BNA 61-minute transfer from #1798 arriving 21:09. **Native cumulative structural PASS, overnight PASS, fixed gate export PASS, effective operating errors ZERO**. No airport gate/stand capacity change. This pattern solves BNA↔ECP in principle and retains R359's AH line continuity.

**IMPORTANT:** BNA→OMA is NOT solved by these new flights; the earlier four/six-leg concept covering both markets failed physical gate constraints. Examine separate BNA→OMA path via retiming/fleet reconfiguration (MCI, BHM, or RFD) without disrupting existing bank/aircraft turns. Passenger full-network audit, planning snapshot and package regression remain outstanding for the current two-leg revision. Neither dev branch nor release main is published; main remains v1.4.1.

Reproducibility: scripts/v142_bna_targeted_search.py (gate search, legal-transfer constrained); scripts/v142_r359_fixed_gate_validation.py; .github/workflows/v142-r359-fixed-gate-validation.yml. Exactly three proposed spare aircraft-days remained maximum; no release allocation final yet.
