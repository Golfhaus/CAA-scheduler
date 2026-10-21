# v1.4.2 — Three spare aircraft as cyclic-line extension candidates

October 20, 2026. Latest native screen: GitHub Actions run 39536876174; script `scripts/v142_cyclic_day_screen.py`. The candidate route days insert into existing 9–11-day cyclic lines and shift following line days, rather than creating short independent lines. **Unpublished hypothetical work; not incorporated into v1.4.2 tactical canonical.**

| Intended use | New route | Fleet | Existing line | Line length | Structure | Overnight | Gate export | Effective operating findings |
| --- | ---: | --- | --- | --- | --- | --- | --- | ---: |
| BNA–BHM multi-turn | R359 | CRJ700 | AH | 9→10 days | pass | pass | **fail** (3 passenger touches off-gate) | 9 |
| DAY–SRQ–DAY | R177 | CRJ200 | AF | 11→12 days | pass | pass | **pass** | 2 |
| SYR–RDU–SYR | R178 | CRJ200 | AC | 10→11 days | pass | pass | **pass** | 3 |

Total line-length increase across the three candidates is exactly **three aircraft-days/three spare physical aircraft** in the project's cycle counting. CRJ700 AH's new BNA day is inserted between existing BNA terminator and next-day BNA originator. AF's new DAY day likewise bridges DAY→DAY; AC's SYR day bridges SYR→SYR. This preserves repeating line geography and keeps all new lines inside the 9–12 day window. CRJ200 route identifiers 177 and 178 are unused in v1.4.1; the original exploratory use of 174 collided with an existing route and was corrected.

**Important caveat:** The two nonzero operating finding totals on DAY and SYR are not release passes. They include bank alignment and/or tiered-service-minimum findings; compare finding IDs with published v1.4.1 before identifying any as genuinely new, then resolve actual new errors without broad overrides. Gate/structure/overnight pass does not imply complete commercial or native operating compliance.

BNA/BHM R359 remains blocked at both fixed inventories, despite the valid 10-day line structure. Do not release that spare or insert the candidate into a canonical until the physical conflicts are eliminated, the last BNA arrival at 23:10 is reconciled with all operating rules, and commercial audits pass.

DAY R177 (DAY 10:00–SRQ 12:25; SRQ 13:10–DAY 15:35) is the leading insertion candidate. SYR R178 (SYR 10:50–RDU 12:20; RDU 13:00–SYR 14:30) is structurally possible, but the necessary HVN–SYR #1879 retiming of about -30 minutes must be jointly checked, including the SYR-B3 bank assignment.

The accepted tactical-only draft still contains only flight #1357 +6 minutes and #1077 -11 minutes. The original v1.4.1 production release and web manifest remain unchanged. Work remains in draft PR #43.
