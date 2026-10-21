# v1.4.2 continuation: R177 and coordinated R178 validation

## R177 DAY–SRQ–DAY
GitHub Actions run 39581258095 screened the 12-day AF cyclic insertion with explicit bank assignments DAY-B3 (10:00 departure) and DAY-B6 (15:35 arrival). Native structural check passed, fixed gate export passed, and effective operating error count was **0**. The underlying separate baseline has historical non-blocking findings; the candidate produces no new effective errors after the assignments. Reproducible candidate generator: `scripts/build_schedule_7_v1_4_2_r177_candidate.py`, which combines the two approved-to-draft MCI retimings with R177 to form a **1,268-leg / 189-route** unpublished candidate. Treat this as a candidate until the cumulative independent passenger-itinerary analysis and full latest-release checks pass.

## R178 SYR–RDU–SYR
New route R178 can become the 11th day of CRJ200 line AC. Gate export passes for SYR–RDU 10:50–12:20 / RDU–SYR 13:15–14:45 and an HVN–SYR flight #1879 shift of -50 minutes (08:55–09:51). With the existing SYR-M09 arrival assignment, SYR-B3 departure and SYR-M15 return, the screen reports **one remaining effective operating error: tiered_service_minimums RDU**. Need inspect the detailed RDU rule and either increase actual service appropriately or reconstruct existing flying; do not override a hard requirement merely to force the new turn. The earlier -30 minute proposal instead still failed arrival bank alignment.

## R359 BNA–BHM
The additional 10th day of CRJ700 line AH preserves structural and overnight continuity, but the five-to-six-leg flight pattern still exceeds fixed gate inventory at BHM and BNA. Uniform time shifts +/-45 min were insufficient. Need coordinated bank-specific timing or existing-route gate reconstruction.

**Governance**: No aircraft physically committed to the published schedule. The analysis branch and draft PR #43 are not approved for merging; production continues v1.4.1. The planned maximum of two CRJ200 and one CRJ700 spares remains intact.


## Exact RDU blocker from subsequent native evidence

GitHub Actions run 39581901703 exposed the RDU `tiered_service_minimums` finding: RDU is at the 90th percentile, has 28 flights and 22 hub/focus flights after the proposed SYR addition, but **five connected hubs (DAY, JAX, MCI, PHF, SYR)** against a **four-hub cap**. Thus the candidate is **not** blocked by too few departures; it would violate the permitted count of distinct hubs. Adding flights or a bank will not resolve this. Do **not** issue a policy override. The options are to replace existing RDU service to one of DAY/JAX/MCI/PHF with SYR, change the proposed one-stop connection to use an already connected permitted hub, or find a policy-compliant network reconstruction. Any removed hub pairing must be audited for lost reasonable coverage and high-demand connections.

The -50-minute HVN-SYR 08:55–09:51, SYR-RDU 10:50–12:20, RDU-SYR 13:15–14:45 screen passes structural and physical gates and resolves the original SYR bank alignment when HVN arrival is reassigned to SYR-M09, new outbound to SYR-B3, and new return to SYR-M15. It is still **not a valid release candidate** because of RDU's four-hub cap.


## Actual combined tactical + R177 passenger-network audit

GitHub Actions run 39582235653 passed and rebuilt `data/schedules/schedule_7_v1_4_2_r177_candidate/` in CI (not published to main). The candidate contains **1,268 flights / 189 routes**, retaining all prior v1.4.1 services plus the two MCI tactical retimings and R177. Full native structural/overnight/planning/gate/operating validation passed; **zero effective operating errors**.

Independent comparison with published v1.4.1 on geographically reasonable directional coverage: **18 new reasonable markets, zero lost, 46 faster fastest reasonable journeys, zero slower**. GRR→SRQ improves from two stops / 468 min to one stop / 370 min; SRQ→GRR improves from two stops / 408 min to one stop / 243 min. Additional high-demand market gains include SRQ→IND (67.5/day O-D), BNA→SRQ (45.7), and both directions of SBN↔SRQ (~22/day each). These numbers are relative to v1.4.1, and are *not* summed with earlier individual audit results.

**Disposition:** R177 should now be treated as a validated unpublished v1.4.2 candidate, not merely a conceptual turn. One CRJ200 spare is implied by extending line AF 11→12 days, but the user-approved spare pool should not be decremented on the released schedule until the eventual release decision.
