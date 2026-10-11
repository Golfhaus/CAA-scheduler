# Schedule 7 v1.2.5 accepted working draft

All three accepted rounds are included and authorized for publication October 11, 2026. The [v1.2.5 release notes](schedule_7_v1_2_5_release.md) describe the published schedule. Its authoritative canonical is `data/schedules/schedule_7_v1_2_5/canonical_schedule.json`; the working draft is a reproducible checkpoint of the same flying.

The cumulative accepted overlay includes the CRJ200 alignment, DAY IND/CAK overnights, MCI SDF/SBN/GRR/SGF overnights and B1 shift, and the ALB/SWF PHF turns and SYR BTV/HPN feeders. There are 1,190 flights, 181 routes, 19 lines, 20 additions and 16 retimed original flights. All physical and timing validations pass with zero effective operating errors. Stand use is 14 claims / 3,253 minutes.

## Reproduction

- Configuration: `config/optimizations/schedule_7_v1_2_5.json`.
- Cumulative overlay: `config/optimizations/schedule_7_v1_2_5_accepted_rounds_1_3.json`.
- Draft replay: `python scripts/build_schedule_7_v1_2_5_draft.py`.
- Release replay: `python -m caa_scheduler build-optimization-release config/optimizations/schedule_7_v1_2_5_release.json`.
- Latest regression: `bash scripts/run_latest_regression.sh`.

The builder verifies source hashes, exact sequential/cumulative equality, preservation of original flights and approved clock changes, fleet/physical inventory, independent maintenance, full joint demand and itinerary tradeoffs. Its draft replay does not publish the app; the release configuration and app manifest define publication.

Round-one and round-two canonicals and reports are preserved in `data/schedules/schedule_7_v1_2_5_round_1/` and `data/schedules/schedule_7_v1_2_5_round_2/`. The [MCI review](schedule_7_v1_2_5_mci_b1_review.md) uses round one; the [long-hold review](schedule_7_v1_2_5_long_holds_review.md) uses round two. Their alternative proposals remain outside the release.
