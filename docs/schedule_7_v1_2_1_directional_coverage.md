# Directional clustering and alternate-hub coverage

This is read-only analysis of the cumulative v1.2.1 draft, not another schedule optimization round. It reconstructs the current draft from released v1.2.0 and both v1.2.1 overlays. No flights, clocks, assignments, inventories or app defaults change.

## Matches and priorities

A strict match has 2–3 daily flights in both directions, departure spans no longer than six hours, directional medians at least six hours apart, and a largest daytime gap of at least six hours in each direction. A broader screen permits a seven-hour span. Departure gaps are evaluated over 04:30–21:00 local; late flights still count toward frequency and clustering. These explicit screens identify two strict matches and one broader match in the current draft.

| Pair | Spoke → hub departures | Hub → spoke departures | Profile | Replacement coverage |
|---|---|---|---|---|
| SAT–MCI | 06:20, 08:45 C | 14:00, 17:15 C | Strict | Low; highest demand exposure among the current matches |
| JAN–MCI | 06:30, 08:10 C | 12:15, 15:35 C | Strict | Low; missing morning arrivals have no alternate |
| CAE–PHF | 05:00, 09:40 E | 13:55, 20:55 E | Broader: reverse span is seven hours | Partial Florida rescue via JAX; weak spread and MAC coverage |

The published v1.2.0 schedule also met this profile for PIT–SYR: PIT departures 04:30/09:35, SYR departures 16:50/22:14. The current draft retains those flights with the authorized minor retimings and adds PIT 13:04 and SYR 11:18 departures, so it no longer meets the cluster screen. It is included as a reference because late PIT-origin NEC access is still limited.

## What coverage means

The comparison universe is the non-hub destinations that the constrained hub actually serves in the relevant direction. For each directional O-D market in that universe, examine the largest missing period, split into bins of up to three hours. Outbound bins use departure times at the spoke. Inbound bins use spoke arrival windows implied by the missing hub departures: add the direct flight's sector duration and timezone difference. This evaluates when connecting travelers can actually arrive, rather than treating all departures from other hubs as interchangeable clocks.

An alternate counts if it is a direct flight or one-stop itinerary through another hub, its relevant spoke departure/arrival lies inside the bin, each transfer is 30–240 minutes, total circuity is ≤2.25, and its elapsed duration is at most two hours longer than the reference-hub benchmark. The benchmark is the fastest actual one-stop journey via the constrained hub; where none exists, use the scheduled sector blocks plus a 45-minute transfer. Two-stop rescue is measured separately. Such a journey may still visit the reference hub, but must use another hub for the connecting flight immediately adjoining the spoke.

Two complementary percentages are shown:

- **Spread coverage:** O-D-weighted share of market/time bins with a qualifying alternate, additionally weighted by bin duration. This is the coverage rating: High ≥80%, Moderate ≥50%, Low <50%.
- **Any-gap coverage:** O-D-weighted share of markets with at least one qualifying alternate somewhere in the missing period. This avoids treating a market as wholly unreachable when it merely has poor frequency, but does not imply all-day access.

Group results are reported independently. Primary groups are those whose dominant first-hub assignment is the constrained hub: MCI's TEX/UMP/OZK, PHF's MAC and SYR's NEC. Daily O-D is assumed uniform across the gap; one connection covers its whole three-hour bin. This is a reachability proxy, not passenger demand by hour, a load forecast or a commercial benefit calculation. No seat caps, fares, competitor share or day-of-week effects are modeled.

## Results

| Reference pair / missing direction | Spoke-local missing window | Spread coverage | Any-gap coverage |
|---|---|---:|---:|
| SAT–MCI / SAT departures | 08:45–21:00 C | 3.0% | 12.1% |
| SAT–MCI / SAT arrivals | 06:26–15:56 C | 0.0% | 0.0% |
| JAN–MCI / JAN departures | 08:10–21:00 C | 5.3% | 22.8% |
| JAN–MCI / JAN arrivals | 06:13–13:58 C | 0.0% | 0.0% |
| CAE–PHF / CAE departures | 09:40–21:00 E | 8.0% | 30.2% |
| CAE–PHF / CAE arrivals | 05:45–15:10 E | 8.3% | 26.0% |
| PIT–SYR / PIT departures | 13:04–21:00 E | 16.6% | 44.0% |
| PIT–SYR / PIT arrivals | 05:36–12:24 E | 49.98% | 86.6% |

SAT has 01:00 service to JAX, outside the daytime departure gap, and 18:30 service to BHM. Neither gives useful replacement reach to TEX or UMP in that gap. Only 7% of OZK demand has any qualifying late alternate. Inbound JAX service arrives at 17:48 and BHM at 23:30, after the missing morning/early-afternoon window. SAT's reference-hub footprint totals roughly 1,205 directional O-D units outbound and 1,219 inbound, substantially larger than JAN or CAE; it is the first current-match priority for a capacity and timing review.

JAN's 15:00 JAX departure provides partial east/south access, including 55% any-gap FLP reach, but no qualifying TEX/UMP/OZK replacement under the two-hour tolerance. JAX's return reaches JAN at 20:03, entirely after the missing morning-arrival window. Its footprint totals about 192 O-D units in each direction.

CAE has one JAX flight each way: 16:40 outbound and an 08:31 arrival. These provide any-gap FLP coverage of 73% outbound and 73% inbound. However, FLP spread coverage is only 19%/23%, and MAC spread coverage is 14%/18% (54%/57% any-gap). CGI gets no qualifying alternate in these particular missing periods despite JAX's group role. Hub presence is therefore insufficient evidence of timed coverage.

For PIT's remaining late departure gap, NEC any-gap coverage is 55%, with only 21% spread coverage. For the missing morning PIT-arrival window, NEC any-gap coverage is 24%, with 11% spread. Other groups fare much better on morning arrival options, so a broad network score would conceal the NEC deficit. PIT merits a group-specific follow-up despite the draft's additional midday flying.

Two-stop choices do not materially improve the measured coverage for these cases under the stated journey limits. Raising the extra elapsed allowance from two to six hours leaves the broad conclusions unchanged: JAN outbound spread rises only from 5.3% to 5.5%, while its TEX any-gap coverage becomes 3.2%. Other reported direction scores remain unchanged. The missing SAT/JAN morning arrival windows still have no alternative.

## Reproduction and checks

```bash
python scripts/analyze_schedule_7_v1_2_1_directional_coverage.py
```

The ignored report `builds/schedule_7_v1_2_1_directional_coverage.json` contains eight directional results, 72 group results and 1,209 market/time cells, using pinned BTS DB1C Jul 2025–Apr 2026 v7. Cell weights reconcile to every directional O-D pool. The workbook derives spread, any-gap and group ratios from the raw cells and verifies all ratios against the report. The only published-schedule comparison is current release v1.2.0; no v1.1 schedule is reconstructed or regressed.
