# Schedule 7 v1.4.1 release — October 20, 2026

User-approved CRJ200 utilization improvements from the 1,259-flight v1.4.0 baseline. Published configuration: **1,266 flights, 188 routes, 17 aircraft routing lines**. Fleet sizes and fixed gate/stand inventory are unchanged. The release pipeline rebuilds and checks the canonical package before publication.

## Accepted scope

- **R105:** BGR–SYR–BGR evening turn. Flying 6h46m → 9h26m.
- **R162:** SYR–BGR–SYR morning turn. Flying 6h53m → 9h33m.
- **R107:** ISP–PHF–SYR connection via PHF B3 and SYR M12, with an eight-minute BDL adjustment. Flying 5h47m → 7h29m.
- **R108:** SYR–PIT–SYR turn, retaining BTV→SYR evening service and BTV↔RFD connection. Flying 6h09m → 8h21m.
- **R356:** supporting BDL–SYR timing adjustment to preserve BDL–PIE connections.
- **R106 and R167:** unchanged. Commercially weak R167 alternatives and unrelated experiments were rejected.

Adds logical SYR-M09, SYR-M12 and PHF-M12-V141 banks without increasing physical gate inventory. BTV→RFD and RFD→BTV underlying directional O-D average 30.1 and 30.3 daily respectively, above the user-defined 15/day protection threshold.

Known commercial compromises: R107 weakens ISP→BNA (3.7 daily directional O-D); R108 slows ORH→PGD. These were documented during acceptance, rather than concealed as validation errors.

## Reproducibility

Run `python scripts/build_schedule_7_v1_4_1_draft.py`, then `python scripts/prepare_schedule_7_v1_4_1_release.py`, then `bash scripts/run_latest_regression.sh` and `python -m caa_scheduler build-web --output dist`. The accepted four overlays are pinned into the draft provenance; the release config fingerprints the canonical input. This release intentionally excludes experimental screening scripts, workflows and unpublished alternative schedule outputs.
