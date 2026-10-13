# Northeast–Florida coverage hypothesis — v1.3.1

Validated October 13, 2026, after adding the approved MCI turn to R724. **Hypothesis confirmed; no new northeast/Florida flying or bank changes have been designed or accepted in this step.** Published v1.3.0 and the current MCI-inclusive draft have identical coverage for all 90 directions audited here.

## Scope and conclusion

Audit HPN, HVN, ISP, BTV and ORH against every active city in the canonical roster's FLP group: DAB, EYW, FLL, GNV, MLB, PGD, PIE, SFB and SRQ. ECP and TLH belong to GCP and are outside this particular FLP audit.

Of **45 city pairs / 90 directions**, **25 pairs lack nonstop or one-stop service in both directions**. That is 50 directional gaps (55.6%): 35 have only two-connection itineraries and 15 have no itinerary within the app's maximum of two connections. The remaining 40 directions comprise two nonstop directions and 38 with one connection.

The affected Florida cities are exactly **PGD, DAB, EYW, GNV and MLB** for every northeast city. FLL, PIE, SFB and SRQ already have service with no more than one connection in both directions from all five. HPN–SFB is nonstop.

These are **structural common-hub gaps**: all 25 affected pairs have no shared hub/focus city with direct service to both endpoints in the needed direction. Existing northeast gateway flying is over SYR, which does not directly serve these five Florida cities. Minute-level adjustments alone cannot create a missing two-leg path. Additional gateway service or a broader route restructuring is necessary. This finding supports investigating the user's proposed JAX/BHM/PHF approach but does not establish gate room or a flight plan at any of those airports yet.

## Complete coverage matrix

Each cell is **northeast→Florida / Florida→northeast** minimum connections. `0` is nonstop; `1` is one connection; `2` is two connections; `—` means no app itinerary with up to two connections. Minimum connections and fastest elapsed journey are separate measures.

| Florida city | HPN | HVN | ISP | BTV | ORH |
|---|---|---|---|---|---|
| DAB | — / 2 | — / 2 | — / 2 | — / 2 | — / — |
| EYW | — / 2 | — / 2 | — / 2 | — / 2 | — / — |
| FLL | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| GNV | 2 / 2 | 2 / 2 | 2 / 2 | 2 / 2 | 2 / — |
| MLB | 2 / 2 | 2 / 2 | 2 / 2 | 2 / 2 | 2 / — |
| PGD | — / 2 | 2 / 2 | 2 / 2 | 2 / 2 | 2 / 2 |
| PIE | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| SFB | 0 / 0 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| SRQ | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |

Every northeast city has five of nine FLP destinations missing direct/one-stop coverage in each direction; no pair here has a gap in just one direction.

## PGD detail and demand priority

| Northeast city | Northeast→PGD | PGD→northeast | O-D/day NE→PGD / PGD→NE | Combined/day |
|---|---|---|---|---|
| HPN | No itinerary up to two connections | 2 connections; 6h19 | 47.4 / 48.8 | 96.2 |
| ISP | 2 connections; 10h45 | 2 connections; 6h28 | 35.8 / 36.1 | 71.9 |
| HVN | 2 connections; 6h51 | 2 connections; 6h21 | 33.7 / 33.0 | 66.7 |
| BTV | 2 connections; 10h40 | 2 connections; 6h17 | 11.2 / 11.4 | 22.6 |
| ORH | 2 connections; 6h51 | 2 connections; 7h53 | 10.6 / 10.9 | 21.5 |

PGD is the clear demand center of this particular problem: **278.9/day** in underlying bidirectional O-D across the five northeast cities, or **77.1%** of the affected markets' **361.6/day** total.

| Affected Florida city | Combined O-D/day to/from the five northeast cities |
|---|---|
| PGD | 278.9 |
| DAB | 56.5 |
| EYW | 20.0 |
| GNV | 3.9 |
| MLB | 2.3 |

These are directional market totals summed once, not forecast passengers on a proposed flight. Several smaller pairs have zero recorded demand in the pinned data. Gap count alone should not drive new aircraft use; later feeder/rotation planning should combine this demand with other credible system demand and existing service alternatives. This finding preserves the user's requirement that spare-fleet deployment deliver useful full aircraft utilization.

## Method and reproducibility

Use the same `buildItineraries` and service-analysis helpers as the current app, the canonical hub/focus roster, and the unchanged 30–240 minute passenger connection window. Count every available nonstop/one/two-connection option before determining minimum connections. The report separately retains the unchanged 2.25× geographic screen; the headline findings above describe timetable coverage.

```bash
python scripts/build_schedule_7_v1_3_1_draft.py
node scripts/audit_schedule_7_v1_3_1_connections.mjs
node scripts/audit_schedule_7_v1_3_1_ne_flp.mjs
```

The northeast/FLP audit validates the active northeast airports, derives the FLP roster from the current canonical, checks all 90 directional counts against published v1.3.0 and saves exact itineraries, demand, shared-hub evidence and source/demand SHA-256 values in `outputs/schedule_7_v1_3_1_ne_flp/coverage_review.json`. It does not modify a schedule or bank. No itinerary within two connections does not prove no physical chain with three or more connections exists.

The accepted MCI flying is F2199 RFD 19:26 → MCI 20:40 CT and F2200 MCI 21:20 → RFD 22:34 CT. It adds 2h28 to the already deployed draft aircraft-day, keeps all prior clocks unchanged, and does not affect these northeast/FLP counts. The draft now has 1,198 flights / 182 routes / 19 lines with zero effective operating errors. Published v1.3.0 remains the app default.
