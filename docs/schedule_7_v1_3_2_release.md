# Schedule 7 v1.3.2 release — October 16, 2026

Schedule 7 v1.3.2 supersedes v1.3.1 with **1,229 flights, 184 routes and 17 routing lines**. This release was authorized by the user on October 16, 2026, conditional on completion of operating and network audits. The release artifact is generated from the accepted v1.3.2 cumulative 1,229-flight draft, with an exact leg-for-leg assertion and fingerprinted source canonical.

## Approved aircraft and route improvements

- Maintenance: correct cyclic maintenance/RON validation, repair the AC/AO/AQ rotations, retain line AM's existing one-day grace.
- R501: replace a SFB–CHS–SFB turn with a second SFB–RFD–SFB round trip, while retaining ABE–MYR. CHS nonstop tradeoff explicitly accepted and documented.
- R175: add the PWM–BWI–PWM turn; R125: add PVD–BWI–PVD; R111: add BHM–PIE–BHM.
- R312: return via DAB–PHF–BDL instead of DAB–BDL, feeding PHF's evening bank.
- R144: preserve all original sectors, add early JAN–JAX–JAN and late MCI–BNA–MCI; flying rises from 5h38 to 12h04.
- R146: add FSD–MCI–FSD evening return; flying rises from 5h27 to 7h49.
- R158: substitute ALB–RDU–ALB for the late ALB–SYR–ALB turn; flying rises from 6h15 to 8h13.
- R176: insert PHF–GSO–PHF midday return, preserving AVP originator and AGS terminator; flying rises from 6h11 to 8h03.
- R107, R160 and already optimized R125 remain unchanged in the final group round because reviewed alternatives failed physical constraints or reduced commercially useful connectivity.

## Operating validation and fleet

Structural, planning, overnight, fixed gate/stand and operating checks pass with **zero effective operating errors and zero hard-stop failures**. Fixed stands remain **15 claims / 3,061 minutes**. Fleet use remains **MAX9 24/35; CRJ900 28/45; CRJ700 56/65; CRJ200 76/80**, leaving respectively 11, 17, 9 and 4 spares. No new aircraft or line is needed. The unavailable runway-data check and inherited warning/grace exceptions remain visible.

## Full passenger-network comparison with released v1.3.1

The final audit, using the app itinerary enumerator and the 2.25× geographical reasonableness screen, finds **60 gains and 5 losses in direct/one-stop directional market coverage**, with **154 faster and 155 slower fastest reasonable journeys**.

The five losses or one-stop downgrades are:

| Market | Directional underlying O-D/day | Explanation |
| --- | ---: | --- |
| OMA–PHF | 7.1 | Loses one-stop choice; two-stop still available with unchanged fastest 5h31 journey |
| ATW–OKC | 1.7 | Loses one-stop option due to R144 MCI bank shift; two-stop retained |
| DSM–SHV | 0.8 | Loses geographically reasonable one-stop coverage |
| ATW–FSD | 0.7 | Loses one-stop coverage after R146 shift |
| ATW–SHV | 0.2 | Loses one-stop option; two-stop remains |

These changes are **documented and accepted**, not operating-rule failures. Other notable previously reviewed journey tradeoffs include loss of CHS–SFB and SFB–CHS nonstops in favor of one-stop alternatives and a DAB–BDL nonstop replaced by a one-stop journey via PHF. Several hub retimings affect faster journeys in both directions. This release is not described as a no-regression network.

Demand numbers are underlying directional O-D opportunity figures, not projected passenger loads or guaranteed loads.

## Reproduction and verification

```bash
python scripts/build_schedule_7_v1_3_2_draft.py
python scripts/prepare_schedule_7_v1_3_2_release.py
bash scripts/run_latest_regression.sh
python -m caa_scheduler build-web --output dist
```

The published canonical must exactly match the 1,229 accepted draft legs. The release config `config/optimizations/schedule_7_v1_3_2_release.json` pins that source with SHA-256; the packaged `data/schedules/schedule_7_v1_3_2/` artifacts and app manifest set v1.3.2 as the default only after the release checks pass. The user requested publication conditional on a clean audit; the listed commercial tradeoffs were reviewed as part of that decision.
