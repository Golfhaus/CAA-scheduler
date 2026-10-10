# Hub exchanges finishing by 00:01 local

This is the original pre-approval review against the immutable 1,168-flight input. The user subsequently approved the repaired 337/345 CRJ700 option for the draft. It is now implemented in the 1,170-flight unpublished draft; see `docs/schedule_7_v1_2_4_midnight_swap.md`. Other alternatives remain unapproved. Main remains v1.2.3.

## Preferred revised option: routes 337 / 345, CRJ700

Replace the previously recommended 337 / 344 PHF–MCI exchange with 337 / 345, using explicit small retimings. This adds a second flight in each direction and avoids the former 02:22 PHF arrival.

| Source route | Added flight | Departure local | Arrival local | Local opportunity | Connecting opportunity | Total opportunity |
|---|---|---|---|---:|---:|---:|
| 337 | PHF–MCI | 20:45 ET | 22:22 CT | 5.7 | 84.4 | 90.1 |
| 345 | MCI–PHF | 20:24 CT | 00:01 ET next day | 5.6 | 23.3 | 28.9 |

These are seat-uncapped, full-capture relative-choice one/two-stop opportunities from the pinned demand model, not forecast passenger loads, incremental passengers or profit. The eastbound opportunity is materially weaker than the westbound opportunity.

The PHF–MCI flight retains a connection to the existing 22:55 MCI–SAT departure, with 33 minutes to connect. The MCI–PHF flight principally brings western/MCI feeders to PHF; it does not feed PHF's first 04:30 departures. A 00:01 arrival leaves a 269-minute wait, exceeding the model's 240-minute connection maximum.

### Required existing-flight changes

| Flight | Direction | Existing times local | Revised times local | Advance |
|---|---|---|---|---:|
| 1404 | ELP–MCI | 11:40 MT–14:56 CT | 11:28 MT–14:44 CT | 12 min |
| 1319 | MCI–CMH | 15:40 CT–18:30 ET | 15:24 CT–18:14 ET | 16 min |
| 1320 | CMH–MCI | 19:10 ET–20:00 CT | 18:54 ET–19:44 CT | 16 min |
| 1784 | XNA–MCI | 14:00–14:57 CT | 13:57–14:54 CT | 3 min |
| 1589 | MFE–MCI | 12:20–14:55 CT | 12:19–14:54 CT | 1 min |

The XNA and MFE adjustments preserve their minimum 30-minute connections to revised flight 1319. Without these repairs XNA–CMH loses all valid connecting itineraries, and MFE–CMH's fastest itinerary becomes 414 minutes slower. The unrepaired scenario is retained in the analysis report as a rejected alternative.

Move two 60-minute MCI banks one minute earlier: 14:45–15:45 becomes 14:44–15:44; 19:45–20:45 becomes 19:44–20:44. Add a PHF 00:00–01:00 arrival bank.

Rebuild the four-line CRJ700 pool AH / AK / AL / AS, preserving its 41 aircraft-days and fleet count. The new lines have 9 / 9 / 12 / 11 days, within the 9–12-day rule. Route numbers will change under reconstruction; 337 / 345 refer to current source routes. The forced handoffs are source 337 to 346 at MCI and 345 to 338 at PHF. PHF overnight time becomes 4h29; MCI overnight time is 8h53.

Structural, operating hard stops, planning, overnight continuity, maintenance cadence and gates/stands pass with zero operating errors. §2.6 Check A passes; Check B has no new findings or worsened departure gaps. Existing advisory operating findings are not all eliminated by this proposal.

The repaired package leaves every previously connected market with a valid itinerary. It improves the fastest itinerary for 25 directional markets, while 31 become 1–16 minutes slower. Newly connected directional markets have 24.8 daily underlying O-D in total; this is distinct from the flight-level opportunity sums. These small wait penalties are a real tradeoff of moving existing services earlier. The 33-minute SAT connection also has little recovery margin. A 00:01 arrival has no timing margin against the requested cutoff.

## SYR and alternatives

Defer the original 159 / 165 MCI–SYR exchange. No unchanged-clock SYR reciprocal exchange was proved under this cutoff. The earliest eligible CRJ200 MCI terminator arrives at 19:54 CT; its 40-minute turn and the MCI–SYR block produce a 00:19 ET arrival. Broad schedule reconstruction beyond the retiming cases tested remains possible, but there is no validated stronger SYR recommendation in this review.

The fixed-clock screen covered 29 eligible hub terminators and 97 reciprocal same-fleet pairs. Thirty-one pairs met the added-arrival cutoff with suitable turns, but none fit both directions entirely into existing banks. Three individual MAX9 pairs and one coordinated CRJ200 package passed complete line and schedule validation. Failure to prove other line covers in the bounded search is not proof of global infeasibility.

| Alternative | Added arrivals local | Opportunity by direction | Frequency after addition | Decision |
|---|---|---|---|---|
| MAX9 703 / 715 DAY–MCI | MCI 22:21 CT; DAY 23:55 ET | DAY–MCI 129.6; MCI–DAY 15.1 | 2 to 3 each way | Defer: weak return, no second-flight benefit |
| MAX9 703 / 722 DAY–PHF | PHF 22:31 ET; DAY 23:28 ET | DAY–PHF 39.2; PHF–DAY 10.7 | 4 to 5 each way | Do not prioritize |
| CRJ200 115 / 136 plus 125 / 135 | DAY 23:58 ET and 00:00 ET; JAX 23:04 ET; MCI 21:08 CT | JAX–DAY 12.7; DAY–JAX 99.1; DAY–MCI 131.1; MCI–DAY 13.6 | DAY–JAX 4 to 5; DAY–MCI 2 to 3 | Defer: two weak legs and four-route commitment |
| Retimed MAX9 712 / 722 PHF–MCI | PHF 00:01 ET; MCI 22:58 CT | MCI–PHF 32.3; PHF–MCI 52.7 | 1 to 2 each way | Inferior to the CRJ700 option for the modeled opportunity |

The retimed MAX9 alternative advances AUS–MCI flight 2001 by two minutes. It passes all schedule checks, keeps previously connected markets connected, improves 13 fastest journeys and slows 11 by two minutes. It is an alternative PHF–MCI exchange, not an additional recommendation to stack on the preferred CRJ700 plan.

## Reproduction and scope

Input: `data/schedules/schedule_7_v1_2_4_round_4/canonical_schedule.json`, byte-identical to the accepted draft, SHA256 `1d6e8fd937524657116664ee8fb0423b90e1b81099513c0c29387c532b393438`.

Scripts: `scripts/analyze_schedule_7_v1_2_4_midnight_swaps.py` and `scripts/analyze_schedule_7_v1_2_4_midnight_retimings.py`.

Machine-readable reviews: `config/proposals/schedule_7_v1_2_4_00_01_swaps_review.json` and `config/proposals/schedule_7_v1_2_4_midnight_retimings_review.json`. Preferred analysis overlay: `config/proposals/schedule_7_v1_2_4_mid_retime_337_345_preserve.json`.

The repaired 337/345 option was subsequently approved and implemented in the unpublished draft. This review retains the original analysis; publication remains reserved to the user.
