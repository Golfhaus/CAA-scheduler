# v1.4.2 — Three-aircraft topology screen, October 20, 2026

**Exploratory only.** Tested from published v1.4.1 in `scripts/v142_three_aircraft_concept.mjs` with hypothetical legs, not integrated into a canonical aircraft rotation. These are **passenger-network screens, not native gate/maintenance/operating validation or authorization to release spares**. Two MCI tactical retimings have separately passed native validation and reside in the reproducible tactical v1.4.2 builder.

## Network concept results

| Proposed aircraft | Tentative added flying | Target outcomes in both directions |
|---|---|---|
| 1 BNA/BHM | BHM–BNA 13:35–14:50; BNA–BHM 15:30–16:45; BHM–BNA 17:25–18:40; BNA–BHM 19:20–20:35; BHM–BNA 21:55–23:10 | BNA↔ECP via BHM (215/180 min); BNA↔OMA via BHM (268/250 min) |
| 2 SYR/RDU | SYR–RDU 11:20–12:50; RDU–SYR 13:30–15:00 | HVN↔RDU via SYR (185/256 min) |
| 3 DAY/SRQ | DAY–SRQ 10:00–12:25; SRQ–DAY 13:10–15:35 | GRR↔SRQ via DAY (370/243 min) |

A prior **BHM–RDU** proposal was discarded: HVN→BHM→RDU is too geographically circuitous and the passenger model correctly does not qualify it as a reasonable one-stop. Switching to **SYR–RDU** successfully creates both reasonable directional HVN/RDU paths.

Cumulative conceptual screen reports **34 geographically reasonable directional coverage gains, zero losses, 37 faster reasonable fastest journeys and no slowdowns**, compared to the original v1.4.1 timetable. Because added legs were simulated without displacing flying or consuming gates, those counts are *optimistic upper bounds*, not validation results. They are independent from the already validated tactical two-flight changes; combined release metrics must be recomputed later.

## Important construction caveats

- BNA/BHM last BHM departure is 21:55. Check focus-city curfew and operating-window policy, and cyclic aircraft terminator/next-day originator. A hypothetical aircraft ends in BNA; it needs a feasible next-day continuation rather than a stranded one-day line.
- All three hypothetical routings have unconfirmed physical gate capacity, terminal occupancy, aircraft fleet availability, turn/maintenance requirements, banking, frequency spacing and source-derived block times. Confirm times rather than treating the screening clock examples as service commitments.
- SYR–RDU requires actual gate slot/bank assignment and a complete airframe cycle. Preserve high-demand HVN/SYR connections.
- DAY–SRQ would fill the morning/daytime DAY/GRR connectivity but must fit DAY physical gates and SRQ stand inventory.
- **HOU→BLV** remains unresolved and requires a separate network solution. No additional aircraft are assumed for it under the three-aircraft ceiling.
- Do not merge draft PR #43 or change `main` until a fully reconstructed 1.4.2 release passes full native validation and passenger-regression audit.

## Development references
- `docs/schedule_7_v1_4_2_tactical_validation.md`
- `scripts/v142_three_aircraft_concept.mjs`
- `scripts/build_schedule_7_v1_4_2_draft.py`
- `config/optimizations/schedule_7_v1_4_2_mci_tactical_candidate.json`
