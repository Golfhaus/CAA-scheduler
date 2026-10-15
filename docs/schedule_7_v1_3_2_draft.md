# Schedule 7 v1.3.2 cumulative draft

Updated October 14, 2026. Unpublished: main and the app default remain v1.3.1.

## Accepted changes

1. [Maintenance validator and AC/AO/AQ rotation repair](schedule_7_v1_3_2_maintenance.md), configured by `config/optimizations/schedule_7_v1_3_2_round_1.json`. Every repeating line reaches an eligible base overnight. AM explicitly uses the standing one-day grace. SYR–MDT is one minute later and DAY–TOL 43 minutes later.
2. [R501 RFD replacement](schedule_7_v1_3_2_r501_review.md), configured by `config/optimizations/schedule_7_v1_3_2_round_2.json`. Retain ABE–MYR; advance MYR–ABE and ABE–SFB by 2h45; replace SFB–CHS–SFB with a second SFB–RFD–SFB turn. The longest R501 sit falls from 5h12 to 2h27 and block increases by 2h54, using the same six flights and aircraft. CHS loses its SFB nonstop pair but retains one-stop JAX service.

The draft retains **1,214 flights, 184 routes and 17 lines**. Fleet use remains MAX9 24, CRJ900 28, CRJ700 56 and CRJ200 76. Structure, operating, planning, overnight turns and physical inventory pass with zero effective errors/hard stops. Stand use remains 15 claims / 3,061 minutes; AM's standing grace and unavailable runway-data check remain visible.

Against published v1.3.1, the app audit loses exactly the two approved CHS direct choices and no direct/one-stop market coverage. Geographic fastest-journey effects are seven faster and 59 slower: the two CHS downgrades plus the previously reviewed 57 one-/43-minute maintenance impacts. All accepted northeast/Florida coverage remains intact.

## Under review

[R175 PWM–BWI proposal](schedule_7_v1_3_2_r175_review.md): add a three-hour CRJ200 round trip using the PWM hold, with eight-/ten-minute advances to its first two flights. All existing choices are preserved; R175's longest hold becomes 1h26. **This is not applied.**

## Build

`python scripts/build_schedule_7_v1_3_2_draft.py` reproduces both accepted overlays and the native artifacts. `--maintenance-only` recreates the pinned round-one checkpoint without overwriting the cumulative draft. `bash scripts/run_latest_regression.sh` validates the currently published baseline, corrected maintenance behavior, cumulative draft and approved network tradeoffs. Publication requires a separate release step.
