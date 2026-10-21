# Schedule 7 v1.4.2 — First native physical feasibility screen

**Unpublished findings.** GitHub Actions run 39535400658 completed successfully (the screening script itself passed, but each individual fictional single-day route has operating findings). Script: `scripts/v142_concept_native_screen.py`. Inputs are hypothesized one-day aircraft service, not valid cyclic lines. The test intentionally does not claim these are release-ready.

| Concept | Structural | Effective operating errors | Fixed physical inventory | Gate assignment export | Additional concerns |
|---|---|---:|---|---|---|
| Five-leg BHM/BNA | pass | 9 | **BHM and BNA fail** | fails: 3 passenger touches off-gate | cyclic continuity, placeholder route number, stand handling |
| SYR–RDU–SYR | pass | 6 | **SYR fails** | fails: 1 passenger touch off-gate | placeholder number, bank alignment/stand and cyclic line |
| DAY–SRQ–DAY | pass | 3 | no fixed-inventory finding | **success** | placeholder number and bank-alignment findings, cyclic line still missing |

The system's tiered service and bank alignment reports include historical findings, so do not attribute their full counts solely to the new conceptual flights without checking new finding IDs. New one-day line names and route numbers are intentionally placeholders, therefore expected to trigger cyclic/numbering constraints.

**Decision:** Do not integrate the raw hypothetical service into canonical `schedule_7_v1_4_2_draft`. Preserve the two already validated MCI tactical retimings. To progress, solve BHM/BNA and SYR physical gate occupancy through exact-slot retiming and/or selective existing-service reorganization, then design complete 9–12-day aircraft rotations (up to three spare physical aircraft released) preserving cyclic transitions, bank assignments and maintenance base visits. DAY/SRQ is the strongest first candidate for full aircraft-route construction because the isolated gate export succeeded, but it is *not yet operationally valid*.

Reference: `docs/schedule_7_v1_4_2_hold_fitting.md` proves no existing same-station hold accommodates these turns unchanged. The passenger-audit-only upper bound remains in `docs/schedule_7_v1_4_2_aircraft_concepts.md`.
