# R501 investigation — MYR hold and SFB point-to-point flying

Investigated October 14, 2026 against the unpublished maintenance draft at commit `4d2f26623ecc1359df061d03f20cd06f2aeada9c`. The user accepted `rfd_later_turn` into the v1.3.2 draft later on October 14. Its overlay is `config/optimizations/schedule_7_v1_3_2_round_2.json`; other alternatives below remain unaccepted. Publication is not authorized.

## Findings

The 5h12 MYR hold is real: R501 arrives at 06:03 and leaves at 11:15. The current CRJ900 aircraft-day is ABE–MYR–ABE–SFB–CHS–SFB–SAT, with 10h12 of block flying. Its endpoint and next-day handoff can remain unchanged under all three principal options below.

ABE–MYR has **31.7 daily ABE→MYR and 30.8 MYR→ABE O-D passengers**. MYR is ABE's second-largest destination in the pinned matrix, after SFB (39.1 outbound). It is a credible nonstop market, although these figures alone do not demonstrate that a CRJ900 is the right gauge or predict flight loads. The app supplies no additional one-stop connecting credit to these P2P legs. Removing the nonstop leaves ABE→MYR at 2h51 and MYR→ABE at 5h07 through PHF, versus 1h33 nonstop. Retain this market in the first repair rather than remove it merely because the timing is poor.

SFB–CHS has **30.2 / 31.5 daily directional O-D**, also without one-stop feed credit. Stronger local markets can use the aircraft:

| Market, first city→second / reverse | Pinned O-D/day | Existing nonstop frequency each direction | Reviewed opportunity |
|---|---:|---:|---|
| SFB–CHS | 30.2 / 31.5 | 1, CRJ900 | Current turn |
| SFB–CLT | 258.7 / 256.1 | 1, MAX9 | Second turn fits existing afternoon window |
| SFB–RDU | 287.9 / 284.9 | 1, MAX9 | Second turn fits existing afternoon window or released midday time |
| SFB–BNA | 284.9 / 285.9 | 1, MAX9 | Second turn fits after an early MYR return |
| SFB–RFD | 820.3 / 820.8 | 1, MAX9 | Second turn fits after an earlier MYR return, replacing CHS |

These are underlying market totals, shared with existing flights and other choices, not passengers assigned to the proposed flights. The source matrix already applies the dampened own/primary blend to secondary airports; no Chicago/Orlando metro totals or second deflation were added.

## Preferred demand-based replacement: RFD

Retain ABE–MYR, bring its return forward 2h45, bring ABE–SFB forward 2h45, and use the larger afternoon window for a second SFB–RFD round trip in place of CHS. All times below are airport-local; RFD and SAT are Central.

| Flight/market | Current | Reviewed RFD option |
|---|---|---|
| F1255 ABE–MYR | 04:30–06:03 ET | Unchanged |
| F1256 MYR–ABE | 11:15–12:48 ET | **08:30–10:03 ET** |
| F1219 ABE–SFB | 13:30–15:47 ET | **10:45–13:02 ET** |
| SFB outbound turn | CHS 16:30–17:37 ET | **RFD 14:15 ET–15:49 CT** |
| SFB return turn | CHS 19:00–20:07 ET | **RFD 16:29 CT–20:03 ET** |
| F2074 SFB–SAT | 21:00 ET–22:35 CT | Unchanged |

R501 stays at **six flights**, uses no additional aircraft and gains **2h54 of block flying**, reaching 13h06. The MYR hold drops to **2h27**; later turns are 42 minutes at ABE, 73 at SFB, 40 at RFD and 57 at SFB. No same-day R501 turn exceeds 2h30. Both RFD directions gain a second daily nonstop, well separated from the retained morning MAX9 service.

The explicit cost is loss of the CHS–SFB nonstop pair. Both directions retain one-stop JAX service, but fastest elapsed journeys change:

| Market | Current nonstop | Remaining fastest journey |
|---|---:|---:|
| CHS→SFB | 1h07 | **2h50** via JAX |
| SFB→CHS | 1h07 | **3h54** via JAX |

The app audit loses precisely those two direct itinerary choices and downgrades those two markets to one stop. It loses no direct/one-stop market coverage and changes no other fastest journey. It does not claim zero passenger impact or new network reach: the RFD benefit is an additional departure choice in a much stronger existing market.

## Alternative: retain CHS and add RDU

Return MYR→ABE at **06:43–08:16**, advance ABE→SFB to **08:56–11:13**, add **SFB→RDU 11:53–13:25 / RDU→SFB 14:05–15:37**, and preserve the existing CHS turn and SFB–SAT flight. All these clocks are Eastern except SAT's unchanged arrival.

This makes the MYR turn 40 minutes, retains all existing flights and itinerary choices, and adds a second daily RDU flight each direction without another aircraft. R501 grows to **eight flights / 13h16 block**, an increase of 3h04. It preserves every existing nonstop and loses no geographic itinerary choices or fastest-journey performance. Its practical tradeoff is substantially earlier MYR→ABE and ABE→SFB service; the demand matrix does not establish traveler preference for those times. A less-early version (07:30 MYR return, 09:45 ABE departure and 17:10 SFB→CHS) fails SFB's four-gate inventory, so it is not presented as feasible.

An early-return BNA addition also passes and has similar underlying O-D (285 each way), with more block flying than RDU. RDU is the shorter of these otherwise comparable additive options.

## Alternative: preserve morning clocks, add JAX and replace CHS with RDU

Keep F1255/F1256/F1219 and F2074 at their current times. Insert **MYR→JAX 06:43–07:47 / JAX→MYR 08:27–09:31** during the hold, and replace the CHS turn with **SFB→RDU 16:30–18:02 / RDU→SFB 18:42–20:14**. This uses existing JAX B4 windows for both touches.

The original MYR sit becomes two turns of **40 and 104 minutes**, separated by productive flying. R501 becomes **eight flights / 13h10 block**, up 2h58, using no extra aircraft. The JAX insertion itself preserves all existing choices, opens seven geographically suitable one-stop directional markets and improves 19 fastest journeys. Its local MYR–JAX demand is only 1.9 / 2.0; its justification is the connecting opportunity, with competition-adjusted indices of 127.2 / 148.1, not a claim that those passengers will board. The largest new directional one-stop coverage is SFB→MYR (27.6 underlying O-D); the other gains are MYR→AUS/HSV and SAT/ELP/DAB/MLB→MYR. Some new one-stop options do not beat an existing two-stop journey.

The combined option retains the same two CHS nonstop losses and elapsed-time penalties described above. It is a credible alternative if improving MYR's connections and preserving morning clocks is more important than the stronger local-demand RFD replacement.

## Other screens and verification

Twenty-five timetable variants were screened; sixteen pass structural, operating, next-day turn and physical inventory checks. The three principal options also pass planning validation. Their fleet allocations, R501 origin/terminus, line AB maintenance cycle, other routes, banks and policy remain unchanged; each has **zero effective operating errors and zero hard stops**, and stand use remains **15 claims / 3,061 minutes**. The inherited AM maintenance grace remains explicitly reported; this study introduces no new grace or waiver. Runway data remains unavailable in the existing native check.

The first PHF insertion (MYR 07:20→PHF 08:25; PHF 09:05→MYR 10:10) fails PHF's 16-gate inventory. The BWI and PIT midday additions tested while retaining CHS fail spacing/turn and SFB gate checks. A second CLT flight in the original afternoon window passes, but is weaker on O-D than RDU; a midday CLT flight at 11:53 conflicts with the existing 11:45 departure. An 08:00 MYR return paired with a 13:15 SFB–RFD departure also fails SFB physical inventory; the selected 08:30 MYR return and 14:15 SFB departure pass. No exceptions were added to force any of these through.

MYR–FLL, MYR–BWI, MYR–PIT and MYR–BNA turns fit the existing MYR hold. Their directional local markets are approximately 46, 42, 38 and 22 respectively. FLL cuts its two fastest journeys; BWI opens BWI→MYR to direct/one-stop coverage. These are useful screened alternatives, but their local demand is smaller than the principal SFB opportunities and the connecting opportunity of the JAX insertion. Filling the hold alone is not the selection rule.

New CRJ900 blocks use the pinned planning profile (0.1364 minutes per nautical mile + 31.94), including local timezone offsets. Existing leg block times are preserved. The network audit uses the same app enumerator, 30–240 minute connection window and 2.25× geographic screen. Competitive indices split underlying demand across choices within 30 minutes of the fastest at the same stop count, excluding connections when a nonstop exists. They are opportunity comparisons, not load or profitability forecasts.

Reproduce the native screens and network audit:

```bash
python scripts/build_schedule_7_v1_3_2_draft.py --maintenance-only
python scripts/review_schedule_7_v1_3_2_r501.py
node scripts/audit_schedule_7_v1_3_2_r501.mjs
```

Detailed reviewed evidence is saved in `data/analyses/schedule_7_v1_3_2_r501_review.json`. The selected RFD option is applied to the cumulative v1.3.2 draft. Published v1.3.1 remains unchanged.
