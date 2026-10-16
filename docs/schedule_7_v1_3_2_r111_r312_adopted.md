# R111 PIE turn and R312 PHF-bank return — adopted in v1.3.2 draft

Accepted October 15, 2026: “Add the original R111 and this modified R312 extension to the draft.” Publication is not authorized. Main and the app default remain v1.3.1.

## Accepted flights

| Route / flight | Sector | Departure | Arrival | Change |
| --- | --- | --- | --- | --- |
| R111 F1991 | OMA–BHM | 10:40 CT | 12:48 CT | 26 minutes earlier |
| R111 F2223 | BHM–PIE | 13:28 CT | 15:59 ET | Added |
| R111 F2224 | PIE–BHM | 16:39 ET | 17:10 CT | Added |
| R111 F1992 | BHM–OMA | 17:50 CT | 19:58 CT | Unchanged |
| R312 F1922 | PHF–DAB | 14:45 ET | 16:33 ET | Unchanged |
| R312 F2225 | DAB–PHF | 17:52 ET | 19:40 ET | Added |
| R312 F2226 | PHF–BDL | 20:20 ET | 21:40 ET | Added |
| R312 F1360 | DAB–BDL | Formerly 21:00 ET | Formerly 23:37 ET | Removed |

All other preexisting flights retain their clocks in this round. All preceding approvals remain in place. The four new flight numbers are distinct in the combined draft; historical independent R312 scenarios used temporary F2223/F2224 numbers.

R111 gains 182 block minutes and its longest hold becomes 56 minutes. R312 gains 31 block minutes and its longest hold becomes 79 minutes. The two changes add 213 block minutes and three net flights, without additional aircraft or stand use. The cumulative draft has **1,221 flights, 184 routes and 17 lines**.

## Demand and connections

The R111 afternoon PIE pair complements existing morning service. Underlying BHM–PIE O-D demand is 36.7 / 37.4 passengers per direction per day, with useful OMA/PIE and PIE/OKC/TUL connections. These are market totals, not per-flight load forecasts.

R312 arrives in PHF-M6 at 19:40, feeding the PHF-B7 departure bank. The 79-minute DAB hold and 40-minute PHF turn retain the useful connections of the earlier 19:01-arrival proposal while reducing passengers' elapsed journeys by 39 minutes. Confirmed connections include PHF→BDL 20:20, BWI 20:30, MCI 20:45, PVD/BNA/DAL/HOU/ILM/AVP 20:55 and ROA 21:45. PVD has the strongest connecting market, 14.8 O-D/day: fastest DAB–PVD improves from 5h33 to 4h26.

The complete [bank review](schedule_7_v1_3_2_r312_bank_review.md) and [original option comparison](schedule_7_v1_3_2_r111_r312_review.md) retain their historical evidence and assumptions.

## Approved passenger tradeoffs, verified together

Against the pinned round-four draft:

- Twenty-one raw itinerary choices disappear, 16 of them geographically reasonable. These are exactly the removed DAB–BDL nonstop and the 20 raw / 15 reasonable choices affected by the OMA–BHM advance. No additional choices are lost when the changes are combined.
- OMA–PHF loses its one-stop choice: the BHM connection becomes 252 minutes, exceeding the 240-minute maximum. Two-stop service remains, and the fastest available journey stays 5h31.
- DAB–BDL loses its only nonstop. Its new evening one-stop journey is 3h48 versus the former 2h37 nonstop, a 71-minute increase, while arrival at BDL is 1h57 earlier. The BDL–DAB nonstop remains.
- Twenty-six geographically reasonable fastest journeys improve. Seventeen become slower: 16 OMA-origin journeys by 26 minutes and DAB–BDL by 71 minutes.
- Geographic direct/one-stop coverage gains PIE–OKC, PIE–TUL, DAB–BNA, DAB–ILM, DAB–ROA and DAB–ACY, with zero underlying DAB–ACY demand still explicitly excluded from the commercial case. Only OMA–PHF loses direct/one-stop coverage. DAB–BDL retains one-stop coverage.

Across the full draft versus published v1.3.1: 23 raw choices / 18 geographically reasonable choices are lost, **50 reasonable fastest journeys improve and 100 become slower**. All previously protected northeast/Florida direct-or-one-stop coverage remains intact. Existing approved CHS nonstop losses, eight-minute ISP impacts, two-minute BWI impacts and one-/43-minute maintenance impacts remain covered by the regression audit.

## Validation and reproduction

The combined draft passes structural validation, operating validation with zero effective errors/hard stops, planning reconstruction/validation, overnight turns and physical gate export. Fleet use remains MAX9 24/35, CRJ900 28/45, CRJ700 56/65 and CRJ200 76/80. Stand use remains **15 claims / 3,061 minutes**. AM's standing one-day maintenance grace and unavailable runway-data check are inherited and visible.

The accepted overlay is `config/optimizations/schedule_7_v1_3_2_round_5.json`. Its base is commit `6722c0b4c95f17451483906b4632a38cbae2f833` and canonical SHA256 `ecf5306874c274135e8d6b3bbfbd33bfb5ef6e7ed8b2dc2a1bd731bc435e733f`. `python scripts/build_schedule_7_v1_3_2_draft.py` reproduces all five accepted overlays and the ten native/network artifacts. `--r125-only` recreates the pinned round-four canonical without overwriting the cumulative draft, preserving the historical reviewers' base.

Final canonical SHA256: `4de8042da82c48f67a991551476e620f01b17cade91d75b5189e9a53ecbb48b0`.

`bash scripts/run_latest_regression.sh` validates the released baseline, all accepted draft changes, physical inventory, exact allowed itinerary losses, stage-specific passenger impacts and the PHF evening connections. See `data/schedules/schedule_7_v1_3_2_draft/connection_review.json` for the cumulative and round-specific network evidence, and the other native reports beside it for operating evidence.
