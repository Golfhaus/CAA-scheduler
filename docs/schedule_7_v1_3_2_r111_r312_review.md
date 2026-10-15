# R111 and R312 hold review — proposal only

Reviewed October 15, 2026 against cumulative v1.3.2 draft commit `0e9a17f48b9de56d50be89a4cc49defd4d2a3bd6`, canonical SHA256 `ecf5306874c274135e8d6b3bbfbd33bfb5ef6e7ed8b2dc2a1bd731bc435e733f`.

No schedule changes have been adopted from this review. The accepted draft remains 1,218 flights / 184 routes / 17 lines. Main and the app remain v1.3.1.

## R111: strongest candidate is an additional BHM–PIE turn

Current BHM hold: 13:14–17:50 Central, 4h36. Candidate clocks:

| Flight | Current | Proposed | Time zone |
| --- | --- | --- | --- |
| F1991 OMA–BHM | 11:06–13:14 | 10:40–12:48 | Central |
| New BHM–PIE | — | 13:28–15:59 | Origin Central, destination Eastern |
| New PIE–BHM | — | 16:39–17:10 | Origin Eastern, destination Central |
| F1992 BHM–OMA | 17:50–19:58 | Unchanged | Central |

All other R111 clocks remain unchanged. Two 91-minute sectors add 3h02 block. The old long sit becomes three 40-minute turns; the longest remaining R111 hold is 56 minutes at OMA. No extra aircraft or other-route changes are needed.

The pinned airport O-D matrix has 36.7 BHM→PIE and 37.4 PIE→BHM passengers/day across each underlying market, not per flight. Existing R143 has only a morning pair: BHM 06:53–PIE 09:24 / PIE 10:04–BHM 10:35. The proposed afternoon pair therefore offers a distinct time of day. It improves OMA–PIE and adds geographically reasonable one-stop PIE→OKC and PIE→TUL coverage. Its competitive opportunity indices are 61.6 outbound / 84.9 inbound, including connections; these are opportunity indices, not load forecasts.

Tradeoffs are material:
- Advancing F1991 by 26 minutes makes its connection to F1928 BHM 17:00→PHF 19:50 take 252 minutes, exceeding the 240-minute connection limit. OMA→PHF loses that one-stop choice (underlying demand 7.1/day). A two-stop option remains; the market's fastest journey remains 5h31.
- Twenty raw itinerary choices disappear, 15 of which pass the geographic screen. Most are two-stop journeys continuing through PHF. This is a loss of choices, not the disappearance of those markets from the network.
- Sixteen geographically reasonable fastest journeys, all OMA-origin, become 26 minutes longer; 14 become faster. Raw enumeration has 17 slower / 14 faster.
- Direct/one-stop coverage gains PIE→OKC and PIE→TUL and loses OMA→PHF. No nonstop is removed.

Native structural, operating, planning, overnight-turn and gate-export checks pass with zero effective operating errors/hard stops. Stand use remains 15 claims / 3,061 minutes. Existing maintenance grace and unavailable runway-data limitation are inherited.

Other tested R111 alternatives:
- CLT with original clocks fails physical gate inventory. Advancing F1991 and the turn by 15 minutes still fails gates; 30- and 42-minute advances pass, but add one stand claim / 138 stand minutes and incur the same lost OMA connection choices. The 30-minute case has only eight geographically reasonable faster markets versus PIE's 14, with 16 slower. Local demand is 23.9 / 24.0; competitive indices 35.9 / 85.4.
- JAX with original clocks fails spacing in both directions. A nine-minute F1991 advance still fails JAX→BHM spacing: the proposed 16:43 departure is only 37 minutes before the existing 17:20 flight, versus the applicable 151.2-minute minimum. BHM is not treated as a hub-bound destination by this rule.
- DAY and SFB candidates fail same-pairing spacing.

Recommendation: PIE is the strongest R111 candidate, with the OMA connection costs explicitly presented for a decision. It has not been inserted into the draft. A simple shift of BHM→PHF cannot restore the lost connection: R346's preceding BWI→BHM arrival already has the minimum 40-minute turn, and further upstream turns/banks also constrain an advance.

## R312: PHF–DAB–PHF–BDL works, with a nonstop tradeoff

Interpretation: retain the first five flights, including PHF 14:45→DAB 16:33, then replace F1360 DAB 21:00→BDL 23:37 with:

| Sector | Departure | Arrival |
| --- | --- | --- |
| PHF–DAB (existing) | 14:45 | 16:33 |
| DAB–PHF (new) | 17:13 | 19:01 |
| PHF–BDL (new) | 20:20 | 21:40 |

All times Eastern. DAB hold falls from 4h27 to 40 minutes. PHF has a 79-minute turn, the route's longest remaining hold. BDL termination is 1h57 earlier. Replacing 157 block minutes with 108 + 80 adds 31 minutes block and one net flight.

The 20:20 departure passes gates and spacing, 104 minutes after the existing PHF→BDL 18:36 departure. The earliest-turn 19:41 departure fails spacing and gates. Tested 20:30 and 20:45 departures fail physical gates. The valid case uses existing PHF-M6 arrival / PHF-B7 departure banks, with no new waiver.

Passenger effects:
- DAB→BDL loses its only nonstop; the reverse BDL→DAB nonstop remains.
- Underlying DAB→BDL demand is 18.7/day. The fastest remaining one-stop journey is 3h48 versus the current 2h37 nonstop, a 71-minute increase. The proposed evening journey is 4h27, 1h50 longer than the removed nonstop, despite arriving earlier because it leaves DAB much earlier.
- Only the removed nonstop itinerary is lost. No market loses direct/one-stop reachability.
- Ten geographically reasonable fastest journeys improve, one becomes slower. Four markets gain reasonable direct/one-stop coverage: DAB→BNA, ILM, ROA and ACY; ACY has zero demand in this matrix.
- DAB→PHF local demand is 2.2/day. PHF→BDL total underlying demand is 21.7/day, split across three daily nonstops after this change. Competitive opportunity indices are 28.3 for DAB→PHF and 14.4 for the added PHF→BDL. These do not establish a strong demand case for both new CRJ700 sectors.

Native structural, operating, planning, overnight-turn and gate-export checks pass with zero effective operating errors/hard stops; stand use remains 15 claims / 3,061 minutes. No other route changes or extra aircraft are needed.

## R312 alternative: JAX turn retaining the BDL nonstop

DAB 17:13→JAX 17:55 / JAX 18:35→DAB 19:17 fits, retaining DAB 21:00→BDL 23:37. It adds 84 block minutes, leaves a 1h43 final DAB hold, passes all the same native checks and preserves every existing itinerary choice. It adds six reasonable one-stop markets and improves 32 reasonable fastest journeys.

Demand is weak: local DAB–JAX demand is only 0.7/day each way, and competitive opportunity indices including connections are only 11.6 / 16.1. That is insufficient evidence to recommend an extra CRJ700 round trip simply to occupy the hold.

A CLT turn needing a 19-minute advance of BDL→PHF and PHF→DAB failed physical gates in the tested case.

Recommendation: R312's suggested PHF routing is operationally feasible, but is a passenger-service tradeoff rather than a clear demand-supported improvement. Retain the present routing unless the earlier BDL termination and extra PHF connectivity are judged worth losing the DAB→BDL nonstop. Do not add the weak JAX turn merely to fill time.

## Method and scope

All scenarios were evaluated independently against the pinned accepted draft using the repository's optimization overlay, structural validation, operating rules, planning reconstruction/validation, overnight turns and physical gate export. Passing candidates were enumerated with the same app service analysis and airport O-D matrix as the prior route reviews. Connections use the app's 30–240 minute window; geographically reasonable journeys pass the 2.25× circuity screen. Direct/one-stop coverage is distinct from reachability requiring two stops.

The competitive indices allocate each underlying market among geographically reasonable choices within 30 minutes of the fastest journey at the same stop count, exclude connections where a nonstop exists, and include at most one stop. They are screening indices, not capacity-constrained passenger assignments or commercial forecasts.

These are independently tested proposals; combining candidates would require a fresh cumulative validation. Publication and application to the draft have not been authorized by this inquiry.
