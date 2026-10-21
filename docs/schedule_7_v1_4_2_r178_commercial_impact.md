# v1.4.2 — R178 SYR–RDU commercial impact screen

Unpublished network-screen only. GitHub Actions run **39583740237** executed `scripts/v142_r178_network_impact.mjs` against **published v1.4.1**. Scenario: R178 SYR–RDU **10:50–12:20**, RDU–SYR **13:15–14:45** with existing HVN–SYR flight 1879 advanced from 09:45–10:41 to **08:55–09:51**. The comparison **excludes R177 and both tactical MCI retimings**; these must be evaluated cumulatively before release.

## Geographically reasonable route comparison

8 new one-stop/reasonable directional markets, 1 lost, 12 faster fastest journeys, 19 slower. The lost reasonable directional connection is **HVN→FWA, 0 O-D daily**. Significant improved and new markets (minutes):

| Market | Directional O-D/day | Before | After | Saved |
|---|---:|---:|---:|---:|
| HVN→RDU | 49.0 | 439 | 205 | 234 |
| RDU→HVN | 47.6 | 416 | 271 | 145 |
| BTV→RDU | 18.0 | 436 | 320 | 116 |
| RDU→BTV | 18.0 | 421 | 184 | 237 |
| SYR→RDU | 22.1 | 174 | 90 | 84 |
| RDU→SYR | 22.0 | 230 | 90 | 140 |
| RDU→PWM | 19.6 | 258 | 213 | 45 |
| BDL→RDU | 47.6 | 259 | 244 | 15 |
| RDU→BGR | 4.7 | 400 | 330 | 70 |
| RDU→ABE | 2.4 | 347 | 267 | 80 |

Additional geographic coverage includes BGR↔RDU (4.8/4.7 O-D, BGR→RDU fastest unchanged), ORH↔RDU (0.4/0.4 O-D). RDU↔BTV and HVN↔RDU improve from two-stop to one-stop.

## Adverse effects of the HVN feeder retime

19 slower fastest geographically reasonable directional markets, most at **zero demand**. Material nonzero-demand examples:
- **HVN→PIE:** 33.6 O-D/day, 268→318 minutes (+50).
- **HVN→BNA:** 23.1 O-D/day, 334→382 minutes (+48).
- **HVN→VPS:** 2.6 O-D/day, 574→624 (+50).

The 50-minute earlier #1879 is the likely cause of this deterioration. As a qualitative weighted trade-off, two-way HVN↔RDU benefits alone are much larger than the measurable material losses above. Nonetheless a less-disruptive feeder solution should be explored before freezing the retime.

## Native operating condition

Physical gate assignment and cyclic R178 placement can work with the coordinated retiming and SYR bank assignments. **RDU's 90th percentile hub-count rule remains violated**: five served hubs (DAY/JAX/MCI/PHF/SYR) versus four permitted. This screen does not authorize changing policy or publishing R178. All services need a cumulative operating and network audit with R177 and the MCI retimings; separate direct RDU↔SYR O-D is approximately 44.1 passengers/day, not guaranteed capture.
