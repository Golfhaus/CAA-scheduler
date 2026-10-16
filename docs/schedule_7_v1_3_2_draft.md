# Schedule 7 v1.3.2 cumulative draft

Updated October 15, 2026. Unpublished: main and the app default remain v1.3.1.

## Accepted changes

1. [Maintenance validator and AC/AO/AQ rotation repair](schedule_7_v1_3_2_maintenance.md), configured by `config/optimizations/schedule_7_v1_3_2_round_1.json`. Every repeating line reaches an eligible base overnight. AM explicitly uses the standing one-day grace. SYR–MDT is one minute later and DAY–TOL 43 minutes later.
2. [R501 RFD replacement](schedule_7_v1_3_2_r501_review.md), configured by `config/optimizations/schedule_7_v1_3_2_round_2.json`. Retain ABE–MYR; advance MYR–ABE and ABE–SFB by 2h45; replace SFB–CHS–SFB with a second SFB–RFD–SFB turn. The longest R501 sit falls from 5h12 to 2h27 and block increases by 2h54, using the same six flights and aircraft. CHS loses its SFB nonstop pair but retains one-stop JAX service.

3. [R175 PWM–BWI insertion](schedule_7_v1_3_2_r175_review.md), configured by `config/optimizations/schedule_7_v1_3_2_round_3.json`. Add PWM 10:13–BWI 11:43 and BWI 12:23–PWM 13:53 ET; advance ISP–SYR eight minutes and SYR–PWM ten minutes. All existing R175 choices and afternoon/evening clocks remain intact. Block increases by three hours and its longest hold becomes 1h26.

4. [R125 PVD–BWI insertion](schedule_7_v1_3_2_r125_review.md), configured by `config/optimizations/schedule_7_v1_3_2_round_4.json`. Add PVD 08:30–BWI 09:43 / BWI 10:25–PVD 11:38 ET, preserving every existing R125 clock. Delay R346 F1418 PHF–BWI two minutes to 09:17–10:05 to fit BWI gates without a cascade. R125 adds 2h26 block and its longest hold becomes 1h52.

5. [R111 PIE turn and R312 PHF-bank return](schedule_7_v1_3_2_r111_r312_adopted.md), configured by `config/optimizations/schedule_7_v1_3_2_round_5.json`. Advance F1991 OMA–BHM 26 minutes to 10:40–12:48 CT; add BHM 13:28 CT–PIE 15:59 ET / PIE 16:39 ET–BHM 17:10 CT. Replace R312 F1360 DAB–BDL with DAB 17:52–PHF 19:40 / PHF 20:20–BDL 21:40 ET. R111 adds 3h02 block and its longest hold becomes 56 minutes; R312 adds 31 minutes and its longest hold becomes 79 minutes. No other-route clocks change in this round. The user accepted the OMA–PHF one-stop loss and DAB–BDL nonstop downgrade on October 15.

The draft contains **1,221 flights, 184 routes and 17 lines**. Fleet use remains MAX9 24, CRJ900 28, CRJ700 56 and CRJ200 76. Structure, operating, planning, overnight turns and physical inventory pass with zero effective errors/hard stops. Stand use remains 15 claims / 3,061 minutes; AM's standing grace and unavailable runway-data check remain visible.

Against published v1.3.1, the cumulative app audit loses 23 raw itinerary choices (18 geographically reasonable): the two approved CHS nonstops, the DAB–BDL nonstop, and 20 raw / 15 reasonable choices affected by the OMA–BHM advance. OMA–PHF loses its one-stop option but retains two-stop service and an unchanged fastest journey of 5h31. Geographic fastest-journey effects are **50 faster and 100 slower**. All accepted northeast/Florida direct-or-one-stop coverage remains intact, including DAB–BDL with one stop.

R175 contributes 15 faster journeys and 22 ISP-origin journeys that take eight minutes longer; it loses no existing choices. R125 contributes two faster nonstop journeys and makes RDU/MYR/ILM→BWI two minutes longer, with no choices lost. Against the prior round-four draft, R111/R312 together improve 26 reasonable fastest journeys and make 17 slower: 16 OMA-origin journeys by 26 minutes and DAB–BDL by 71 minutes. R312's 19:40 PHF arrival retains the approved evening bank connections, including PVD, BWI, MCI, BNA and DAL. The accepted CHS downgrades and one-/43-minute maintenance impacts remain explicit.

## Build

`python scripts/build_schedule_7_v1_3_2_draft.py` reproduces all five accepted overlays and the native artifacts. `--maintenance-only` recreates the pinned round-one checkpoint; `--r501-only` recreates the round-two checkpoint. `--r175-only` recreates the round-three checkpoint. `--r125-only` recreates the pinned round-four checkpoint. These flags do not overwrite the cumulative draft. `bash scripts/run_latest_regression.sh` validates the currently published baseline, corrected maintenance behavior, cumulative draft and approved network tradeoffs. Publication requires a separate release step.
