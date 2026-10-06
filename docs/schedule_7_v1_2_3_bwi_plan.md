# Schedule 7 v1.2.3: BWI aircraft utilization and a late DAY bank

Proposal dated October 6, 2026. Baseline: released Schedule 7 v1.2.2
(1,128 flights). This work is unpublished; the app and main remain on v1.2.2.

## Recommended first round

Add two turns to Route 331, plus CLT and SDF feeders to a new DAY-B9,
21:05–22:05 Eastern. Preserve every existing flight and its time, including
Route 332's 07:45 BWI–PHF originator. All added flying is CRJ700.

| Flight | Route | Origin | Departure | Destination | Arrival | Connecting opportunity score |
|---|---|---|---|---|---|---:|
| 2131 | 331 | BWI | 05:35 | PHF | 06:23 | 367.9 |
| 2132 | 331 | PHF | 07:03 | BWI | 07:51 | 114.9 |
| 2133 | 331 | BWI | 19:52 | DAY | 21:14 | 36.3 |
| 2134 | 331 | DAY | 21:54 | BWI | 23:16 | 276.1 |
| 2135 | 340 | CLT | 19:48 | DAY | 21:05 | 30.8 |
| 2136 | 340 | DAY | 21:55 | CLT | 23:12 | 297.7 |
| 2137 | 327 | SDF | 20:17 | DAY | 21:05 | 43.7 |
| 2138 | 327 | DAY | 21:55 | SDF | 22:43 | 236.7 |

All table times are Eastern. Flight numbers are provisional draft assignments.
Scores include one- and two-stop opportunities and all competing schedule
choices. They are seat-uncapped, full-capture relative allocations, **not
passenger forecasts, expected loads, or net incremental passengers**. A
traveler using two added flights contributes to both flight scores; do not
sum the rows as unique customers. Demand remains pinned to
`bts-db1c-6mo-jul2025-apr2026-v7`.

Route 331 starts at 05:35 rather than 10:05, and terminates at 23:16 rather
than 19:12. The morning turn returns 134 minutes before the unchanged 10:05
BWI–PHF departure. Its first gate touch begins at 04:35, when the existing
BWI–JAX originator releases a gate; BWI's other gate remains occupied by the
05:05 BWI–MCI originator.

PHF already has five BWI flights each way, so this is its sixth round trip.
The earlier window still has a strong connection case: the added BWI departure
feeds FLP, CGI and TEX markets, particularly PIE, FLL and HOU. The return
collects CGI/FLP traffic, including MYR and SFB. It has the strongest modeled
connecting opportunity per added block minute among the feasible morning
turns.

The DAY turn introduces the first daily BWI–DAY round trip. Its local O-D is
only 2.7 BWI→DAY and 2.5 DAY→BWI daily. Without other late DAY departures,
the added inbound leg has no connecting opportunity. CLT and SDF make the bank
bidirectional: BWI's 21:14 arrival connects to their 21:55 departures in
41 minutes; their 21:05 arrivals connect to BWI at 21:54 in 49 minutes and to
each other at 21:55 in 50 minutes. The DAY departures also use existing
19:40–20:28 arrivals. GLC and LEC feed is particularly important to the BWI
and CLT returns; TEX contributes strongly to SDF.

CLT has no existing DAY nonstop, and SDF has one each way. FWA could add a
fourth daily DAY round trip, but its modeled value is much lower and it loses
priority to CLT and SDF. ROA fits aircraft timing but requires a further
hub-count policy decision and has a weaker case; it is not included.

## Morning DAY alternative

If expanding DAY's morning coverage is preferred to PHF's sixth round trip,
replace Flights 2131/2132 with BWI 05:43–DAY 07:05 and DAY 07:53–BWI 09:15.
This uses the existing DAY morning bank and leaves 50 minutes before Route
331's unchanged 10:05 departure. With the same evening bank and feeders,
the two morning legs score 189.2 and 111.9 connecting opportunities. BWI–DAY
then has two flights each way, well separated between morning and evening.
Both morning choices are independently feasible; they are alternatives.

## Why Route 332 is preserved

An extra early hub turn cannot fit before the current 07:45 originator using
the existing gates and banks. A wider ten-flight plan does physically fit:
move the BWI–MCI originator six minutes earlier, add PHF flying to 332, use a
DAY morning turn on 331, and cascade four Route 332 flights by +46, +44, +5
and +2 minutes. But this delays the original PHF arrival from 08:33 to 09:19.
The best modeled BWI–BNA journey increases from 187 to 317 minutes, and
BWI–PGD from 216 to 297 minutes. This is a material loss of useful feed.
Do not prefer this plan merely because it adds two more flights.

A morning SYR turn with small Route 331 retimings requires a seventeenth
passenger gate at SYR. Moving its bank start five minutes earlier clears the
gate issue, but creates a 65-minute bank against the fixed 60-minute maximum.
Neither option is included in the recommended draft.

## Gate margin and connection protection

The evening DAY turn uses the 40-minute minimum at both BWI and DAY. Its BWI
arrival touch is 23:16–00:01, ending exactly when the MCI arrival needs that
gate; the other BWI gate is occupied by the MAX9 overnight. Returning ten
minutes later fails passenger gate allocation under the current timetable.

Delaying MCI–BWI twenty minutes makes that later return fit, but removes the
only valid OKC–BWI and XNA–BWI itineraries under the 240-minute maximum
connection window. The existing XNA arrival at MCI 16:35 connects to the
20:35 departure at exactly 240 minutes; OKC 16:36 connects at 239 minutes.
This flight is load-bearing and must retain its clock in the recommended
round. Any effort to improve the evening gate margin must preserve those
connections in a jointly validated revision.

Aircraft utilization and customer connection checks do not prove crew duty,
crew rest or maintenance feasibility. Route 331's aircraft day grows to
17h41m and 10h31m of block time. Separate crews or relief would be needed;
the late CLT/SDF arrivals also leave short overnights before their successors.
Review staffing and maintenance windows before accepting the flying. Seat
capacity, real market capture and operating economics also need a separate
load forecast before treating the opportunity scores as expected traffic.

## Validation and saved work

The recommended draft has 1,136 flights on the same 181 routes and 20 lines.
It adds no aircraft and no physical gates or stands, and retimes no existing
flights. Structure, planning, overnight turns and gate allocation pass, with
zero effective operating errors or hard-stop failures. The existing 183
review warnings remain unchanged. Stand claims remain 15; stand minutes fall
from 4,277 to 3,763, a reduction of 514 minutes (12.0%).

The full itinerary audit finds 30 markets with a faster best journey and no
market with a slower best journey or loss of all valid service. Newly
connectable O-D markets total 283.8 daily underlying demand units; this is
addressable demand, not a forecast of incremental carried passengers. The
DAY-morning alternative also preserves every old itinerary: 31 faster
markets, no slower/lost markets, and 3,771 stand minutes.

Saved files:

- `config/proposals/schedule_7_v1_2_3_round_1.json`: proposed eight-flight overlay.
- `data/schedules/schedule_7_v1_2_3_draft/canonical_schedule.json`: review checkpoint.
- `config/proposals/schedule_7_v1_2_3_bwi_screen.json`: comparisons, rejected trials,
  per-flight O-D/connections, geographic groups, and retiming harm audits.
- `scripts/analyze_schedule_7_v1_2_3_bwi.py`: deterministic screen and draft builder.

Reproduce with `python scripts/analyze_schedule_7_v1_2_3_bwi.py`. Review reports
are generated under `builds/schedule_7_v1_2_3_draft/`. Publication and the
morning-turn choice remain the user's decision; no application manifest,
released v1.2.2 asset, or main-branch file is changed by this script.
