# v1.3.2 continuation — October 16, 2026

## Approved R144

The user approved integrating the previously reviewed R144 eight-sector solution. It retains JAN–MCI, MCI–OKC, OKC–MCI, MCI–SHV; inserts JAN–JAX–JAN (04:30 CT departure) and MCI–BNA–MCI in the evening. Existing review: [R144 review](schedule_7_v1_3_2_r144_review.md).

A reproducible validation/materialization script is now available at `scripts/stage_schedule_7_v1_3_2_r144.py`. Its output is isolated in `outputs/schedule_7_v1_3_2_r144_accepted/` to avoid falsely treating artifacts as regenerated until the script has been executed. The published schedule and app default remain v1.3.1.

**Important:** This commit stages the integration script only. It is not evidence that the script ran or that the cumulative canonical has been updated. Merge of generated outputs into the cumulative v1.3.2 build must follow a successful run and updated regression/network audits.

## Six-route fleet-level optimization request

Review R160, R176, R146, R158, R107 and R125 *as a group*, using the R144-augmented draft. The first-pass census from the current five-round canonical is:

| Route | Line/day | Fleet | Flights | Total block (min) | 06:00–22:00 block (min) | Ends |
| --- | --- | --- | ---: | ---: | ---: | --- |
| R160 | AM/4 | CRJ200 | 6 | 344 | 304 | ACY → PWM |
| R176 | AN/9 | CRJ200 | 6 | 371 | 316 | AVP → AGS |
| R146 | AI/3 | CRJ200 | 5 | 327 | 317 | MCI → FSD |
| R158 | AM/2 | CRJ200 | 7 | 375 | 331 | GRR → ALB |
| R107 | AC/7 | CRJ200 | 6 | 347 | 347 | BTV → CAK |
| R125 | AE/4 | CRJ200 | 9 | 560 | 486 | HVN → IND |

The critical-period block above clips flights against 06:00–22:00 on the schedule's local-minute representation; verify with canonical time/zone model before using for official rankings. R125 includes the newly accepted PVD–BWI return.

These are **six operating days on five different repeating aircraft lines**, not necessarily six individually removable aircraft. R160 and R158 belong to AM on different days, and R146 shares AI with the approved R144 rebuild. Test consolidation at the line-cycle level; evaluate whether one entire physical line can be removed or whether consolidation merely changes days without reducing fleet use.

Recommended strategy: establish continuity and RON graph for all five lines; find cross-line splice opportunities at SYR, PHF, DAY and MCI; test morning/late hub-bank retimings and geographically reasonable direct/one-stop coverage; preserve end-of-day stations and MX-base cycle. Compare 6→5 and 3→2 physical-cycle outcomes as distinct from flight-count efficiency. Reject any reduction that breaks night-to-next-morning continuity, fleet/line capacity, gates/stands, curfews, or maintenance rotation. Quantify block, critical period block, connections, demand opportunity, nonstop/one-stop losses, and total fleet actually freed.

No six-route optimized overlay has yet been validated or adopted. Do not publish without user authorization.
