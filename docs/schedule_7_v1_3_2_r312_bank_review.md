# R312: PHF evening-bank follow-up — proposal only

**Adoption update, October 15, 2026:** The user accepted the original R111 PIE option and the refined R312 17:52 DAB–19:40 PHF / 20:20 PHF–21:40 BDL sequence. See the [combined adoption and validation](schedule_7_v1_3_2_r111_r312_adopted.md). The remainder records the historical investigation before adoption.


Reviewed October 15, 2026 against accepted draft commit `0e9a17f48b9de56d50be89a4cc49defd4d2a3bd6`, canonical SHA256 `ecf5306874c274135e8d6b3bbfbd33bfb5ef6e7ed8b2dc2a1bd731bc435e733f`.

This refines the [earlier review](schedule_7_v1_3_2_r111_r312_review.md). No candidate is adopted. Accepted canonical/build overlays remain unchanged.

## Preferred timing of the PHF proposal

| Sector | Departure ET | Arrival ET |
| --- | --- | --- |
| PHF–DAB (unchanged) | 14:45 | 16:33 |
| DAB–PHF (new) | 17:52 | 19:40 |
| PHF–BDL (new) | 20:20 | 21:40 |

DAB hold is 79 minutes; PHF turn is 40 minutes. R312 still adds only 31 block minutes / one net flight versus the current direct DAB–BDL tail, requires no additional aircraft or other-route clock changes, and terminates at BDL 1h57 earlier. The longest hold is 79 minutes.

The earlier proposed 17:13–19:01 DAB–PHF already connected with PHF's last evening departure bank. Waiting 39 more minutes at DAB preserves every one of those one-stop connections and reduces all of their elapsed journey times by 39 minutes. It does not create extra outbound destinations relative to the 19:01 arrival. There are no DAB arrivals in the newly accessible inbound-connection interval, so the additional DAB wait adds no feeder arrivals there.

19:40 is the latest PHF arrival compatible with the 20:20 BDL departure and the 40-minute aircraft turn. It lies in PHF-M6 (18:52–19:52), feeding PHF-B7 (20:05–21:05). The 30-minute passenger connection minimum is also met.

## Useful connections

| Destination | PHF departure ET | Connection minutes | DAB-origin market O-D/day | Fastest current → proposed journey |
| --- | --- | --- | --- | --- |
| BDL | 20:20 (new sector) | 40 | 18.7 | 2h37 nonstop → 3h48 one-stop |
| BWI | 20:30 | 50 | 3.8 | 3h49 → 3h26 |
| MCI | 20:45 | 65 | 4.0 | 5h35 → 5h30 |
| PVD | 20:55 | 75 | 14.8 | 5h33 → 4h26 |
| BNA | 20:55 | 75 | 5.4 | 5h47 → 4h45; gains reasonable one-stop coverage |
| DAL | 20:55 | 75 | 4.0 | 6h41 → 5h56 |
| HOU | 20:55 | 75 | 1.6 | 6h51 → 6h06 |
| ILM | 20:55 | 75 | 1.0 | Gains reasonable one-stop coverage; 4h00 |
| AVP | 20:55 | 75 | 0.7 | 4h56 → 4h11 |
| ROA | 21:45 | 125 | 0.9 | 8h14 → 4h47; gains reasonable one-stop coverage |

ACY and TTN also pass the connection/geographic screen, but both have zero underlying DAB-origin demand in the pinned matrix. Other technically available departures that fail the geographic screen are excluded from the demand case. O-D figures above are total underlying markets, not expected flight loads.

Against the accepted draft:
- Twelve geographically reasonable fastest journeys improve; only DAB–BDL becomes slower.
- Four markets gain geographically reasonable direct/one-stop coverage: DAB–BNA, ILM, ROA and ACY. Raw enumeration also adds DAB–MYR, which fails the geographic screen.
- Only the removed DAB–BDL nonstop itinerary is lost. Every other existing raw and geographically reasonable itinerary choice is retained.
- The DAB–PHF competitive opportunity index rises from 28.3 for the 19:01 arrival to 39.6 for 19:40, compared with 38.9 on the existing afternoon PHF–DAB sector.
- The PHF–BDL index rises from 14.4 to 20.7 because the new evening DAB connection is now within 30 minutes of the fastest alternative.

Indices use the prior review's method, allocate market opportunity across competitive choices, and are not capacity-constrained load forecasts. The case is substantially more useful as an evening bank feeder than a comparison using local PHF demand alone suggests. PVD provides the strongest connecting market.

## Operational screen and remaining tradeoff

19:30 and 19:40 PHF arrivals, both retaining PHF–BDL 20:20, pass structural validation, operating validation (zero effective errors/hard stops), planning reconstruction/validation, overnight-turn validation and physical gate export. Stand use remains 15 claims / 3,061 minutes. The inherited AM standing maintenance grace and unavailable runway-data check are unchanged. A 19:50 arrival with a 20:30 PHF–BDL departure fails physical gates in the tested configuration.

The preferred timing reduces the new evening DAB–BDL journey from 4h27 to 3h48. Losing the current 2h37 nonstop remains the central cost: 71 minutes extra travel for the 18.7/day underlying market. BDL still receives the aircraft earlier at 21:40, and the reverse-direction BDL–DAB nonstop remains.

Recommendation: use 17:52 DAB–19:40 PHF as the preferred timing if the PHF proposal is selected. The connection benefits strengthen the case, but do not erase the BDL nonstop tradeoff. No schedule changes have been applied.

## Reproduction

`python scripts/review_schedule_7_v1_3_2_r111_r312.py 312_bank_arrival_1170 312_bank_arrival_1180 312_bank_arrival_1190` recreates the three additional native screens against the pinned canonical. `node scripts/audit_schedule_7_v1_3_2_r111_r312.mjs` evaluates all locally passing scenarios (or accepts their names). The full script without scenario arguments reproduces the original alternatives too.

[Evidence](schedule_7_v1_3_2_r312_bank_evidence.json) records native findings/overlays, before/after network comparisons, new-flight profiles and source provenance. All candidates remain independent proposals; combining with an R111 candidate requires cumulative validation.

