# Schedule 7 v1.3.2 cumulative draft

Updated October 14, 2026. Unpublished: main and the app default remain v1.3.1.

## Accepted changes

1. [Maintenance validator and AC/AO/AQ rotation repair](schedule_7_v1_3_2_maintenance.md), configured by `config/optimizations/schedule_7_v1_3_2_round_1.json`. Every repeating line reaches an eligible base overnight. AM explicitly uses the standing one-day grace. SYR–MDT is one minute later and DAY–TOL 43 minutes later.
2. [R501 RFD replacement](schedule_7_v1_3_2_r501_review.md), configured by `config/optimizations/schedule_7_v1_3_2_round_2.json`. Retain ABE–MYR; advance MYR–ABE and ABE–SFB by 2h45; replace SFB–CHS–SFB with a second SFB–RFD–SFB turn. The longest R501 sit falls from 5h12 to 2h27 and block increases by 2h54, using the same six flights and aircraft. CHS loses its SFB nonstop pair but retains one-stop JAX service.

3. [R175 PWM–BWI insertion](schedule_7_v1_3_2_r175_review.md), configured by `config/optimizations/schedule_7_v1_3_2_round_3.json`. Add PWM 10:13–BWI 11:43 and BWI 12:23–PWM 13:53 ET; advance ISP–SYR eight minutes and SYR–PWM ten minutes. All existing R175 choices and afternoon/evening clocks remain intact. Block increases by three hours and its longest hold becomes 1h26.

4. [R125 PVD–BWI insertion](schedule_7_v1_3_2_r125_review.md), configured by `config/optimizations/schedule_7_v1_3_2_round_4.json`. Add PVD 08:30–BWI 09:43 / BWI 10:25–PVD 11:38 ET, preserving every existing R125 clock. Delay R346 F1418 PHF–BWI two minutes to 09:17–10:05 to fit BWI gates without a cascade. R125 adds 2h26 block and its longest hold becomes 1h52.

The draft contains **1,218 flights, 184 routes and 17 lines**. Fleet use remains MAX9 24, CRJ900 28, CRJ700 56 and CRJ200 76. Structure, operating, planning, overnight turns and physical inventory pass with zero effective errors/hard stops. Stand use remains 15 claims / 3,061 minutes; AM's standing grace and unavailable runway-data check remain visible.

Against published v1.3.1, the app audit loses exactly the two approved CHS direct choices and no direct/one-stop market coverage. Geographic fastest-journey effects are 24 faster and 84 slower. R175 contributes 15 faster journeys and 22 ISP-origin journeys that take eight minutes longer due to added connection waiting; it loses no existing choices. R125 contributes two faster nonstop journeys and makes RDU/MYR/ILM→BWI two minutes longer, with no existing choices lost. The accepted CHS downgrades and one-/43-minute maintenance impacts remain explicit. All accepted northeast/Florida coverage remains intact.

## Build

`python scripts/build_schedule_7_v1_3_2_draft.py` reproduces all four accepted overlays and the native artifacts. `--maintenance-only` recreates the pinned round-one checkpoint; `--r501-only` recreates the round-two checkpoint. `--r175-only` recreates the round-three checkpoint. These flags do not overwrite the cumulative draft. `bash scripts/run_latest_regression.sh` validates the currently published baseline, corrected maintenance behavior, cumulative draft and approved network tradeoffs. Publication requires a separate release step.
