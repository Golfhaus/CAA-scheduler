# Schedule 7 v1.3.3 — BHM four-aircraft mini-bank draft

**Unpublished.** This work was developed separately from the user-approved R514 PIE–MCI change. No edits were made to released `main` or to the immutable pre-BHM checkpoint.

## Revert point and branches

- **Exact revert commit:** `6965d28175b4089c269f543a1d6b24b423fbdcb3`.
- **Preserved branch:** `checkpoint/schedule-7-v1.3.3-pre-bhm-minibanks`.
- **Development branch:** `schedule-7-v1.3.3-bhm-mini-banks`.
- **Checkpoint warning:** `checkpoint/v1.3.3-before-bhm-four-aircraft-20261017` is misleadingly named: it currently contains the post-BHM 1,253-flight schedule and **must not** be used to revert the BHM additions. Use only `checkpoint/schedule-7-v1.3.3-pre-bhm-minibanks` at the pinned SHA above.
- The checkpoint retains the 1,229-flight v1.3.3 working draft including the previously accepted R514 PIE–MCI round trip. To discard the BHM additions, restart from the checkpoint rather than rewriting released `main`. Do not move the checkpoint branch forward.

## Approved aircraft allocation and airports

Use **two additional CRJ900** and **two additional CRJ700** aircraft-days from existing inventories. Fleet use becomes CRJ900 **30/45** (15 spares), CRJ700 **58/65** (7 spares), with CRJ200 76/80 and MAX9 24/35 unchanged. Fleet inventory totals do not change.

**Northern spokes:** ISP, HVN, ALB, CAK. **Southern spokes:** MYR, SRQ, CHS, and **PGD** as the additional FLP city.

**Why PGD?** Compared with EYW/MLB/DAB it has strong recorded north-south underlying O-D. CAK–PGD had *no* geographically reasonable one-stop option on the baseline schedule and has 103.6/day CAK→PGD O-D. SFB and FLL have even higher local demand but already possess multiple reasonable one-stop paths for all four northern origins. PGD also has fewer existing options. This is a demand/opportunity rationale, not a flight-load forecast.

## Validated operating pattern

Four new one-day closed rotations remain at DAY/SYR maintenance bases overnight; **no additional BHM overnight aircraft**. They provide northern morning arrivals into BHM and departures south after 40+ minutes, then southern afternoon arrivals and departures north in two gate-separated waves.

| Route | Fleet | Morning feed | Southern pair | Afternoon / evening north and maintenance return | Block |
| --- | --- | --- | --- | --- | --- |
| 529 | CRJ900 | DAY 06:00–ALB 07:40; ALB 08:40–BHM 10:04 | BHM 10:51–SRQ 13:21; SRQ 14:08–BHM 14:38 | BHM 15:18–ALB 18:42; ALB 19:25–DAY 21:05 | 11h08 |
| 530 | CRJ900 | SYR 06:08–CAK 07:17; CAK 09:25–BHM 10:06 | BHM 10:53–MYR 13:18; MYR 14:15–BHM 14:40 | BHM 15:20–CAK 18:01; CAK 20:21–SYR 21:30 | 8h30 |
| 357 | CRJ700 | SYR 06:08–ISP 07:06; ISP 08:45–BHM 10:10 | BHM 10:55–PGD 13:34; PGD 15:21–BHM 16:00 | BHM 16:40–ISP 20:05; ISP 20:45–SYR 21:43 | 10h04 |
| 358 | CRJ700 | DAY 06:00–HVN 07:47; HVN 08:52–BHM 10:20 | BHM 11:05–CHS 13:25; CHS 15:09–BHM 15:29 | BHM 16:09–HVN 19:37; HVN 20:17–DAY 22:04 | 11h10 |

**All listed departure/arrival times are local** (DAY, SYR, ALB, CAK, ISP, HVN and southern destinations Eastern; BHM Central). The pairs operate in reverse directions in the afternoon without requiring additional aircraft or gate inventory.

BHM morning northern arrivals are 10:04–10:20 CT, southern departures 10:51–11:05 CT. In the afternoon SRQ/MYR arrivals 14:38–14:40 feed ALB/CAK departures 15:18–15:20. CHS arrives BHM 15:29 and feeds HVN departure 16:09; PGD arrives 16:00 and feeds ISP departure 16:40. These are staggered because **BHM's four free gates are not continuously available throughout the afternoon**.

## Native checks

The selected `day_day` feasibility candidate passed native structural, overnight, planning, operating and **gate/stand physical-inventory** checks, with **zero effective operating errors and no added stands/gates**. All flight turns and spacing conform; PGD is placed later specifically to preserve spacing from the existing PGD–BHM departure.

**Review-visible qualifications:** Four new one-day repeating lines BA, BB, BC and BD trigger the standing *9–12 route-days per line* warning guideline, not an error. Each line is nevertheless a physically closed, productive, maintenance-base overnight cycle. Six explicitly user-authorized, **service-tier hub-count** exception entries for ISP, HVN, ALB, CAK, CHS and MYR are scoped to the new useful BHM focus-city connections. No gate, bank, spacing, turn, curfew or maintenance rule was waived.

## Passenger-network audit (vs. R514-only v1.3.3 baseline)

| Measure | Result |
| --- | ---: |
| New scheduled legs | **24** |
| Total flights in new v1.3.3 draft | **1,253** |
| Routes | **188** |
| Routing lines | **21** |
| Geographically reasonable directional coverage gains | **60** |
| Geographic directional coverage losses | **0** |
| Faster fastest reasonable itineraries | **117** |
| Slower fastest reasonable itineraries | **0** |
| New BHM one-stops, north → south | **15 of 16** |
| New BHM one-stops, south → north | **13 of 16** |

Under the fixed 2.25× geography screen, **ISP–MYR is not a qualifying BHM connection in either direction** (2.30×, even if the timing works). **CHS→ALB and CHS→CAK** miss the early afternoon outbound departures; those markets retain their previous one-stop alternatives where applicable. PGD→ISP can be reached by new BHM service; **CAK→PGD gains reasonable one-stop service**.

The 60 gains and 117 fastest-journey improvements are incremental to the preceding **unpublished R514-only v1.3.3 draft**, not comparisons with published v1.3.2. The existing R514 FWA→PIE one-stop loss and PIE→HVN / GRR→PIE follow-ups remain unchanged. All O-D values are underlying directional market demand, not loads.

## Reproducibility and release controls

- `config/optimizations/schedule_7_v1_3_3_bhm_minibanks.json` is the selected four-aircraft overlay.
- `scripts/build_schedule_7_v1_3_3_draft.py` reproduces R514 **plus** the BHM addition, pinning and asserting the native-validated flight/assignment set.
- Validation source: `outputs/schedule_7_v1_3_3_bhm_minibanks_mx5/physical_screen.json` and `day_day_canonical.json`.
- Network evidence: `outputs/schedule_7_v1_3_3_bhm_minibanks_mx5/network_screen.json`.
- The app's default and released `main` remain `schedule_7_v1_3_2`. **No v1.3.3 publication approval has been given.**
