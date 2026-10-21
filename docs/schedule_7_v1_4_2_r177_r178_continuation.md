# v1.4.2 continuation: R177 and coordinated R178 validation

## R177 DAY–SRQ–DAY
GitHub Actions run 39581258095 screened the 12-day AF cyclic insertion with explicit bank assignments DAY-B3 (10:00 departure) and DAY-B6 (15:35 arrival). Native structural check passed, fixed gate export passed, and effective operating error count was **0**. The underlying separate baseline has historical non-blocking findings; the candidate produces no new effective errors after the assignments. Reproducible candidate generator: `scripts/build_schedule_7_v1_4_2_r177_candidate.py`, which combines the two approved-to-draft MCI retimings with R177 to form a **1,268-leg / 189-route** unpublished candidate. Treat this as a candidate until the cumulative independent passenger-itinerary analysis and full latest-release checks pass.

## R178 SYR–RDU–SYR
New route R178 can become the 11th day of CRJ200 line AC. Gate export passes for SYR–RDU 10:50–12:20 / RDU–SYR 13:15–14:45 and an HVN–SYR flight #1879 shift of -50 minutes (08:55–09:51). With the existing SYR-M09 arrival assignment, SYR-B3 departure and SYR-M15 return, the screen reports **one remaining effective operating error: tiered_service_minimums RDU**. Need inspect the detailed RDU rule and either increase actual service appropriately or reconstruct existing flying; do not override a hard requirement merely to force the new turn. The earlier -30 minute proposal instead still failed arrival bank alignment.

## R359 BNA–BHM
The additional 10th day of CRJ700 line AH preserves structural and overnight continuity, but the five-to-six-leg flight pattern still exceeds fixed gate inventory at BHM and BNA. Uniform time shifts +/-45 min were insufficient. Need coordinated bank-specific timing or existing-route gate reconstruction.

**Governance**: No aircraft physically committed to the published schedule. The analysis branch and draft PR #43 are not approved for merging; production continues v1.4.1. The planned maximum of two CRJ200 and one CRJ700 spares remains intact.
