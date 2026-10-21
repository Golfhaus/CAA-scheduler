# Schedule 7 v1.4.3 — seven-route reassembly authorization and regression gate

2026-10-21. **Exploratory only; DO NOT publish.** User authorizes broad reconstruction of routes **303, 313, 316, 319, 338, 339, 345**, including unassigning and reassembling flights and substantial retimings. The previous **1,286-leg, 191-route, 17-line v1.4.3 draft is a hard revert point** and must not be modified in place until construction and commercial validation succeed. Current released `main` remains v1.4.2.

## Highest-priority protected invariant

**No directional market with >8 underlying passengers/day may deteriorate from one-stop (or nonstop) service to needing 2+ stops or no service.** This is checked in both the geographically reasonable and all technically reachable itinerary models, on a direction-by-direction basis. `scripts/v143_rebuild_guard.mjs` now turns such a loss into a failing exit status; any above-threshold loss blocks release, regardless of other benefits. For markets **≤8 passengers/day**, losses can be considered but must still be reported. Longer minimum journey time without stop-count deterioration is acceptable when justified by offsetting demand/service improvements. No physical gate/stand, curfew, aircraft-turn, or cyclic-line violations may be waived.

## Line structure and scope

- R303 is AA day 3 (BHM→PNS).
- R313, R316, R319 are AH days 2, 5 and 9 (BDL→SAV; PVD→BNA; SRQ→ABE).
- R338, R339 are AK days 1 and 2 (PHF→SAV; SAV→CHS), cyclically adjacent at SAV.
- R345 is AS day 6 (SDF→PHF).

All seven may be reorganized jointly, but aircraft-day endpoints must remain connected with preceding/succeeding line days; line AH/AK/AS/AA identities cannot be silently interchanged, and new aircraft cannot be assumed. Rebuilding can move a flight across routes only if all other routes and full line turns remain valid.

## Initial construction experiments

1. Reproducible `scripts/v143_seven_route_rebuild_candidate.py` stages two previously native-feasible physical changes together:
   - R313 CLT→JAX 07:02–08:13, JAX→CLT 08:53–10:04, followed by existing #1379 CLT→PHF retimed to 10:50–11:56. Existing PHF→AVP #1745 **not** retimed, because its later departure materially damages SFB/RFD→AVP; this is a *commercial timing tradeoff* if the hard guard passes.
   - R338 PHF→RDU 13:53–14:43, RDU→PHF 15:23–16:13, followed by existing #1493 PHF→SAV retimed to 17:00–18:26. Preserves evening SAV→JAX and all other station visits, at cost of slower BDL/HPN/ALB/SYR→SAV trips if their stop count is preserved.
   - Combined candidate would add 4 legs, from 1,286 to **1,290**, if structure, gates, overnight, planning and above-8 market coverage gate pass. **This is not yet an accepted canonical update.**
2. `scripts/v143_r303_early_originator.py` tests advancing BHM→MCI flight #1409 from 06:30 earlier, then inserting MCI-originating SGF/OMA/DSM/TUL morning mini-turns **without moving #1346 PNS→MCI**. This avoids the documented >8 passenger PNS connectivity regressions from earlier PNS retimes. Structural and passenger validation required; do not accept speculative blocks.
3. The earlier R345 short CLT side turns passed gates but lacked meaningful O-D/connection demand; meaningful expansion requires reassigning a leg or retiming downstream PHF→GSP. R316/R319 remain congested at PHF/SYR; swapping portions of AH rather than artificially lengthening a hold is required.
4. A completed native-valid R338 PHF→SAV earlier-side turn had unacceptable loss of reasonable Northeast→SAV itineraries; current staging therefore uses the **later** PHF→SAV timing, contingent on hard-stop-count guard.

## Current status

Native and protected one-stop CI: `.github/workflows/v143-rebuild-passenger-gate.yml`. Early R303 alternate: `.github/workflows/v143-r303-early-originator.yml`. Their job completion status must be examined before an acceptance decision. Do not merge PR #46 or update `web/schedules.json` as part of this reconnaissance phase. The original 1,286-leg canonical in `data/schedules/schedule_7_v1_4_3_draft` remains the working acceptance checkpoint.
