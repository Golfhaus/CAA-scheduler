# Coastal American Airways — Build Instructions Template

---

## How This Document Works

Every item below is tagged by how often it should change:

| Tag | Meaning | Touch it when... |
|---|---|---|
| 🔵 **PERMANENT** | Strategy, process, and lessons learned about *how* CAA builds schedules. | Only after a deliberate, reviewed process change — not per build. |
| 🟢 **PERSISTENT** | Standing constraints and conventions (hub list, caps, formatting rules). Stable, but not frozen. | Rarely — review at the start of each build, edit only with a clear reason. |
| 🟡 **VARIABLE** | This build's specific parameters and decisions. | Every build. Section 0 and Part 3 are meant to be rewritten each time. |

**Versioning:** this file is a single, evolving document in Project Knowledge — it is never copied per schedule. A new build chat pulls it fresh from `/mnt/project/`, fills in Part 0 and Part 3 locally for that session only, and those answers stay in that chat. Nothing from Part 0/3 is written back here. Only Part 1 and Part 2 content — lessons, Persistent-condition changes — gets promoted back into *this* file, through Finalize (§1.11), and only after explicit review. This document's own version number (currently **v2.0**) increments only when that happens; it has nothing to do with which schedule number is being built. **v2.0 is this file as of the end of Schedule 6 prep, built entirely before Schedule 6 kickoff** — the v1.6.1/v1.6.2/... patch-level scheme used during prep has now collapsed into this single release, reflecting the scale of what changed (multi-hub assignment, bank/wave design, and a full construction-file rename are a bigger jump than a routine per-build tweak). Patch-level versioning is retired as of v2.0 — the next content promotion goes to v2.1, not back to a third digit, unless a future prep cycle of comparable scale calls for it again.

**Read this document expecting a live build, not a plan.** Everything in §1.3c and §1.6a — multi-hub assignment, hub bank design, the rescoped §2.6 checks — was written and parameter-tuned against Schedule 5's actual data *before* Schedule 6 construction began. None of it has been run against a real Schedule 6 build yet. Part 0 of the Schedule 6 build chat should treat these as the confirmed starting baseline (per the checklist items already added for them below), not as settled history — the MODERATE threshold calibration, the bank-count table, and the tier-cap interaction with Standing Lessons Log #28a are all real candidates for adjustment once real construction surfaces problems v2.0's authors couldn't see from data alone.

**List discipline:** per Eric's standing instruction, no destination/served-city list is stored inline in this document. The authoritative roster lives in `city_information.csv` and is referenced, not duplicated, throughout — see §2.11.

---

## PART 0 — 🟡 Before You Start (check/update every build)

Work through this list first. It's the fast pre-flight check before opening Part 3 in full.

- [ ] **Is this a Skunkworks build?** Confirmed explicitly, not inferred from the chat title or anything else. This controls what Finalize (§1.11) is allowed to write back to shared files at the end.
- [ ] **Schedule number / version** being built, and whether it's a full reset or an incremental revision.
- [ ] **Will there be destination changes this build?**
  - **No** → skip straight to the next item. Don't re-walk the roster.
  - **Yes** → for each addition, work through §1.3 (group, hub pairing, classification, demand data, `city_information.csv` row, `Active = Y`). For each removal, work through §1.3b (`Active = N`, reason in Notes). Confirm each against `city_information.csv` as you go — don't inline the list here.
- [ ] **Fleet composition** — total aircraft and type breakdown for this build. Fleet size/mix is fully Variable and has changed materially between recent builds — never assume carried-over (§3.2).
- [ ] **Hub list** — confirm the 5 hubs are unchanged; note any addition/removal.
- [ ] **Focus city roster** — BHM is a standing (Persistent) focus city; confirm no additions/removals to the focus-city list itself.
- [ ] **Enplanement/demand-scaling targets** — any hub getting a target-driven O-D adjustment this round (e.g. PHF's historical-peak baseline)?
- [ ] **Estimated-demand check** — count cities in `city_information.csv` with `Demand_Data_Source = Estimated`. 5 or more means a BTS refresh is due before proceeding — prompt for it and wait for explicit confirmation it's done.
- [ ] Review last build's **"Deferred to Future Work"** log — anything ready to act on now?
- [ ] Confirm the **hard-constraint values** in Part 2 still hold (gate/stand caps, time windows, percentile minimums) — rare to change, but check rather than assume.
- [ ] Confirm adoption status of the **departure-spacing matrix** (proposed, not yet applied retroactively as of Schedule 4) and the **per-market frequency ceiling** (currently inactive).
- [ ] **Multi-hub qualification thresholds (§1.3c)** — confirm the MODERATE calibration still holds, or re-run `compute_multihub_assignments.py` with adjusted thresholds if the demand refresh or network has changed meaningfully since it was last run. Review `multihub_summary.md`'s "Changed" column for any city whose hub count would drop, not just gain.
- [ ] **Hub bank counts and window width (§1.6a)** — confirm the per-hub bank-count table still matches current per-hub connecting-demand totals; recompute if the demand refresh changed materially.

---

## PART 1 — 🔵 PERMANENT: Strategy, Process & Lessons Learned

### 1.1 Network Philosophy
Hub priorities, in order:
1. Facilitate connecting opportunities between spoke destinations where the hub is geographically positioned to do so.
2. Satisfy local O-D demand into/out of the hub itself.
3. Provide inter-hub connectivity for city pairs farther apart than average.

Focus-city priorities use a deliberately different order (local demand first, then relief to other hubs' service — see the BHM precedent in §2.1 for the worked example).

**As of Schedule 6: a destination's hub relationship is no longer a single fixed assignment.** Through Schedule 5, `Hub_Assignment` bound most cities to exactly one hub (occasionally two, set manually at add-time). This was the direct cause of D1's finding that 78% of zero-opportunity city pairs shared no hub at all — two single-hub-assigned cities on opposite sides of the network had no way to connect within one hub touch, no matter how well timing was optimized. Schedule 6 replaces this with a demand-and-geometry-qualified multi-hub roster (primary, plus secondary/tertiary/quaternary where the intergroup data and geography actually support it) — see §1.3c for the full methodology. This is a genuine network-design change, not a scheduling optimization; it changes which destinations are even reachable from which hubs before construction begins.

**Apply geographic-balance constraints alongside pure demand ranking when selecting hubs or focus cities.** Demand-only selection has produced real coverage gaps in past network iterations — entire regions with zero focus-city presence while other regions accumulated several. Weigh geographic coverage explicitly, not just raw demand rank, when a hub/focus-city selection decision comes up. (Skunkworks Alpha)

### 1.2 Demand Data Principles
- Real-world BTS-derived demand (the consolidated intergroup matrix and airport O-D matrix) governs city-pair prioritization throughout — not assumed or estimated demand, except where explicitly noted as a fallback.
- The **BTS DB1C Market file** (OD40 program, 40% sample, monthly) is the correct source for true O-D pairs; the Product file collapses incorrectly for this use.
- Direct O-D demand between a spoke and a specific hub measures narrow point-to-point demand, **not** that hub's connecting value. Geographic home-hub assignment drives *which* hub(s) serve a destination; direct demand only weights splits between already-assigned hubs.
- Raw BTS demand cannot convert directly to flight frequency — use relative-share allocation (sqrt-damped weights against a real capacity budget), not demand/(seats×LF) directly.
- **Metro-summing deflation applies whenever a secondary-summed city is the *origin* of a pair being evaluated, not only when it's the stated target.** A city whose data absorbed a nearby primary airport's traffic (the confirmed pairs in §2.11's Classification field) shows inflated direct demand to *every* destination it's paired with, not just to its own totals — apply the same deflation ratio across the board, not just where it was first noticed. (Skunkworks Alpha)
- **Check a sizing methodology's actual target before concluding a secondary connection is undersized.** A destination's smaller, secondary spoke connection can look "undersupplied" by raw demand math even though it's intentionally sized smaller — most of that destination's real demand may already be allocated to its primary connection on purpose. (Skunkworks Alpha)
- **An existing superior alternative can undercut a connecting-value case even when raw feed demand looks real.** If a proposed connection's feed traffic is already well-served by an existing direct flight, that undercuts the case for the connection regardless of what the raw feed number shows. (Skunkworks Alpha)
- **Cross-check implausible-magnitude source data against an independent reference.** Already standard practice for PHF's enplanement baseline (§2.1) — treat it as a general habit, not a one-off: whenever a data source's magnitude seems out of line with a city's real-world size, check it against something independent (FAA enplanements, comparable cities) before trusting it. (Skunkworks Alpha)

### 1.3 Process: Adding a New Destination
1. Assign it to a geographic **Group** (match precedent from similar-era additions where possible).
2. Assign **hub pairing(s)**: primary hub by geography and group precedent (unchanged); secondary/tertiary/quaternary hubs per the demand-and-geometry qualification in §1.3c, gated by the new city's expected percentile tier (§2.3).
3. Classify **Primary vs. Secondary** (secondary-airport summing) per the nine confirmed summing pairs in §2.x demand notes — decide case-by-case if it doesn't fit an existing pair.
4. Attempt a fresh BTS DB1C pull for the destination, using the same seasonal snapshot months as the rest of the network. If unsuccessful, estimate its O-D profile from comparable in-group cities, set `Demand_Data_Source = Estimated`, and **recount how many cities across the whole file are currently `Estimated`.** If that count reaches 5 or more, stop and prompt for a refreshed BTS pull covering all of them before continuing — don't let this accumulate silently. Wait for explicit confirmation that the refresh happened before treating the roster as current again. (Enforcement of actually doing the refresh is on the build lead, not something this process can verify on its own.)
5. Add it to the ranked population for percentile tiers (§2.3) and apply the resulting minimum flight-count floor.
6. **If a row for this code already exists** in `city_information.csv` with `Active = N` (i.e. it's a returning destination — see §1.3b), skip to step 7 below rather than rebuilding it from scratch; that's the entire point of keeping removed cities on file. **Otherwise, add a full new row** — never inline-only in build notes, and never partially filled (the Schedule 4 workbook shipped CHS and BTR with placeholder codes in the City column instead of real names — don't repeat that). At minimum, resolve: City name (per §2.11 naming convention), Long City (only if a multi-city metro name was compressed), Airport Name, Group, Hub Assignment, Status (almost always "Destination" for a new addition), MX Base (almost always "N"), Classification (Primary unless it's a genuine secondary-airport summing case), Timezone, Latitude/Longitude. Leave Gate/Stand Allocation Override blank unless there's already a known reason to deviate from the Status-based default.
7. Set `Active = Y` and `Status_Changed_In` to the current schedule/version, whether the row is brand new or being reactivated.
8. Look up the airport's real runway length (and elevation) once, and record it in `Runway_Length_Ft`/`Elevation_Ft` — this is a one-time cost, not something to re-derive on future builds. Compare against §2.12's fleet minimums for whichever fleet type is being assigned to this destination. If it's below the threshold, this isn't an automatic disqualification — check the aircraft manufacturer's actual airport-planning data before ruling it out, since §2.12's numbers are conservative screening triggers, not precise cutoffs.

### 1.3b Process: Removing a Destination
Cities are never deleted from `city_information.csv` — only deactivated. The row (and everything researched to build it) stays, so a future reintroduction skips straight to step 7 above instead of redoing the work.
1. Set `Active = N` and `Status_Changed_In` to the current schedule/version.
2. Add a short reason to `Notes` (demand collapsed, gate capacity reassigned elsewhere, network restructuring, etc.) — a bare flag flip six schedules from now won't explain itself.
3. Confirm the city is actually absent from the finished schedule (no flights reference it) before finalizing — `extract_schedule.py`'s data-quality check will flag a mismatch either direction (an `Active = Y` city with no flights, or a served city that's `Active = N`) if this step gets missed.

### 1.3c Multi-Hub Assignment Methodology (Schedule 6+)
**Status: built during Schedule 6 prep, prior to kickoff — confirm at Part 0, not yet
run against a real build.** Replaces the old single/manual-dual `Hub_Assignment` with a
computed roster, re-derivable whenever hubs, groups, or the demand refresh change — not
a one-time hand edit. Implemented in `compute_multihub_assignments.py`; re-run it rather
than editing `Hub_Assignment` directly.

**Two-stage process — a group-level qualification, gated by a city-level tier cap:**

**Stage 1 — Group-level hub qualification.** For each of the 11 groups, rank all 5
hubs by *servable demand*: the summed intergroup pax/day across every pairing where
that hub appears in the pairing's hub list. The top-ranked hub is the primary (this
should match the existing geography-based assignment — a mismatch is worth a manual
look, not an automatic override). Each next-ranked hub qualifies as secondary,
tertiary, or quaternary if it clears **both** a minimum servable-demand floor and a
maximum distance-ratio ceiling (its distance from the group's centroid, divided by
the primary hub's distance from that same centroid):

| Rank | Min. servable pax/day | Max. distance-ratio vs. primary |
|---|---|---|
| Secondary | 443 (rating-2 cutoff) | 2.75x |
| Tertiary | 1,356 (rating-4 cutoff) | 1.75x |
| Quaternary | 2,173 (rating-5 cutoff) | 1.30x |

Pax cutoffs reuse the intergroup file's existing quintile breakpoints rather than
inventing new numbers. These are the **MODERATE** calibration confirmed at Schedule
6 Part 0 kickoff (19 total group-hub links, closing 13 of 42 previously-unreachable
group pairs to 29/55) — a **CONSERVATIVE** (17 links, 33/55 unreachable) and
**LOOSE** (21 links, 25/55 unreachable) calibration were also run for comparison;
see `multihub_summary.md` from that Part 0 session if revisiting this choice.

**Known ceiling, not a bug:** FLP, GLC, NEC, OZK, and UMP do not qualify for a
second hub under any calibration tested, loose or conservative — their next-best
hub candidate sits 3.7–4.9x farther than their primary, and no demand level
justifies that detour. This is geography, not a threshold-tuning problem. Full
reachability for these five groups' connecting traffic depends on inter-hub trunk
capacity and BHM's secondary-connection role (§2.1), not on giving them a second
real hub. Don't loosen thresholds specifically to force these five to qualify.

**Stage 2 — City-level tier cap.** A city's actual hub count is
`min(its percentile tier's cap, its group's qualified hub count)` — see the updated
§2.3 table. This is the "smallest cities" exemption: a city in the bottom tier stays
single-hub even if its group qualifies for three or four, matching real load
realities (a thin destination can't fill meaningful frequency to multiple hubs).
**Note this can reduce an existing city's hub count**, not just add to it — a
handful of small cities in newly-multi-hub-qualified groups currently carry a
manually-set second hub from an earlier build that predates this tiering; the
computed roster caps them back down to primary-only. Review `multihub_summary.md`'s
"Changed" column for these before accepting the roster — they're a real behavior
change, not a computation artifact.

**Re-run cadence:** same as the existing Hub_Assignment review cadence (Persistent,
checked at Part 0, not recalculated mid-build) — but re-run for real whenever a hub,
group, or the demand refresh changes, rather than hand-editing the result.

**Tactical relief valve for tier-capped cities:** a city's tier cap (§2.3) can leave
it eligible for fewer hubs than its group qualifies for — the smallest cities in a
multi-hub-qualified group (e.g. ROA, AGS, MCN in CGI, all capped to `JAX` alone
despite CGI qualifying for `JAX/PHF/DAY`) are the main case. Don't loosen the tier
cap or the qualification thresholds to chase these — Standing Lessons Log #28a
handles it instead, as a post-generation, evidence-based add keyed to real observed
idle capacity on that specific city's route, not a permanent roster change.

### 1.4 Fleet Assignment Methodology
Fleet-constrained greedy approach:
1. Rank all city-pairs (hub-spoke, inter-hub trunk, focus-city connections, and qualifying point-to-point routes) by target demand.
2. Greedily assign the highest-ranked pairs to the largest aircraft type until its fleet-capacity ceiling is used up.
3. Repeat for each smaller type in descending size order, using what remains.
4. Routes just below each cutoff will run at higher effective load factors than a theoretical target — expected and acceptable, not a flaw.
5. Build largest aircraft to smallest; smaller-type scheduling may require adjusting already-drafted larger-type routings — nothing is locked until the full build is validated.
6. Fleet build order must be **sequential and cumulative**, not independent parallel builds reconciled at the end — each subsequent fleet schedules around prior fleets' real occupancy, with standing permission to reach back and re-time an earlier fleet's flight if needed.

### 1.5 Percentile Ranking Methodology
- Ranking basis: total O-D volume per city — sum of that city's row + column in the airport O-D matrix, using metro-summed figures where applicable (per the confirmed secondary-to-primary summing pairs).
- Ranked population: all served destinations plus any in-build focus-city candidates.
- The percentile thresholds themselves and what they require are a standing constraint — see §2.3.

### 1.6 Build Sequencing Guidelines
- Sort destinations by O-D enplanement volume when sequencing the build.
- If an aircraft would otherwise sit ROD (remain overnight / out of duty) for a significant part of the day, look for feasible additional flying before defaulting to a hard-stand park.
- Point-to-point routes get disproportionately dropped under construction pressure — reserve dedicated capacity for them or build them first.

### 1.6a Hub Bank / Wave Design Methodology (Schedule 6+)
**Status: built during Schedule 6 prep, prior to kickoff — confirm at Part 0, not yet
run against a real build.** Resolves D1 and D2 together as originally
flagged: deliberate connection banks at each hub, sized and prioritized by intergroup
demand, replacing the old approach where hub-arrival timing was purely a byproduct of
each aircraft's own rotation logistics.

**Bank count per hub**, set by each hub's total connecting demand (summed intergroup
pax/day across every pairing where that hub appears in the hub list — recompute this
alongside the multi-hub qualification in §1.3c, same demand refresh):

| Hub | Total connecting demand | Banks/day |
|---|---|---|
| JAX | ~62,000/day | 6 |
| DAY | ~44,300/day | 5 |
| MCI | ~33,400/day | 5 |
| SYR | ~29,600/day | 4 |
| PHF | ~21,100/day | 4 |

**Bank window: 60 minutes core.** Spoke arrivals feeding a given bank cluster within
that 60-minute window; outbound spoke departures follow within the existing
`minConnect` floor (30 min, §2.5/Timetable_App_Process.md) plus reasonable turn
allowance — a bank is a clustering target for arrivals, not a promise every
connection inside it hits the legal minimum. This is a narrower, separate concept
from `minConnect`/`maxConnect` (30/240 min), which remains the outer bound the
timetable app uses to decide whether a connection exists *at all* — bank width
governs construction, not the app's connection-search range.

**Bank placement is not fixed to specific clock times a priori.** Banks are spaced
across each hub's operating window (§2.5) roughly evenly by default, but actual
start times are a construction-time decision, shaped by what's actually achievable
given each spoke's own rotation — don't hardcode bank clock times into this
document; they're a build-time output, not a build input.

**Priority placement within a bank:** when a bank has more candidate spoke
arrivals/departures than it can cleanly hold, intergroup rating and volume (§1.3c's
underlying data) decide who gets first claim on landing inside the bank window.
A rating-5 pairing's spoke arrival and its onward spoke departure get placed first;
lower-rated pairings fill remaining slots, and the lowest-priority overflow lands in
the adjacent bank rather than forcing a fit.

**Updated construction priority hierarchy** (supersedes the informal ordering
referenced pre-Schedule 6):

1. Fleet capacity — hard constraint, never traded (unchanged).
2. RON-at-destination / RON-at-MX-base coverage (unchanged rank).
3. **Bank timing at hubs (NEW).** A hub-touching arrival/departure must land inside
   its assigned bank window. This supersedes the role §2.6's `hub_factor` used to
   play — bank assignment now decides hub-touching timing directly, rather than an
   even-spacing target nudging toward it.
4. Section 2.6 spacing — rescoped, see below.
5. Aircraft utilization — **explicitly flexible as of Schedule 6.** A turn may run
   past the 40-minute gate-claim floor (§2.5) specifically to align with the
   aircraft's next assigned bank departure — this is now an accepted trade, not a
   violation to fix. §2.5's 40-minute figure remains the absolute floor, not a
   target ceiling. If a turn would need to run past **150 minutes** to hit its next
   bank, model it as a deliberate hold (gate/stand waypoint split, §1.7) rather than
   a turn — that's no longer a quick connection, it's a scheduled wait.

### 1.7 Gate/Stand Validation Methodology
- **A claim-window feasibility check and actual gate assignment are not the same thing.** Modeling every flight as an independent claim window (e.g. 60 min pre-departure, 45 min post-arrival) is valid for checking whether total demand exceeds capacity at some moment — it is *not* valid for saying "this specific aircraft is on this specific gate," which requires tracking which claims belong to the *same physical aircraft*. Presenting the former as if it were the latter produces results that look plausible but aren't real (e.g. a gate shown holding an aircraft type that was never actually there). (Skunkworks Alpha)
- **Conflict checks must be cyclical, not linear.** The schedule repeats every 24 hours — check every candidate placement against existing events shifted by −1440, 0, and +1440 minutes, not just as given. A continuous overnight hold spanning midnight competes with next-morning recurring traffic even though raw timestamps don't overlap in a single 48-hour read.
- **RON aircraft default to holding their gate**, not moving to a stand. A stand is only used when a continuous gate hold would genuinely exceed that city's gate capacity at some point in the window. Validation order: test whether a single continuous gate hold fits within capacity (accounting for all other gate activity at that city during the window) *first*; only fall back to terminate (45 min) + stand + originate (1 hr) when the continuous hold doesn't fit. When multiple aircraft compete for limited gates overnight, prioritize continuous holds for whichever aircraft has the shortest wait until its next departure.
- **The waypoint pattern: validate *successful* placements for inefficiency, not just check for outright failures.** A gate-hold algorithm that finds *a* conflict-free gate for every aircraft can still be wasteful — e.g. parking an aircraft on a gate for 6+ hours during a long wait, when the middle of that wait could instead sit on an otherwise-idle stand, freeing the gate for a different aircraft's brief touch in between. After automatic assignment, scan specifically for gate holds much longer than the aircraft's actual touch-time need, and check whether a gate → stand → gate split (the aircraft "touches down" at a waypoint stand for the bulk of the wait, then swaps back to a gate before its next departure) relieves pressure elsewhere. This won't surface from a standard conflict-checker, since a long continuous hold isn't a violation — it just isn't the most efficient allocation. (Skunkworks Alpha)
- **Rebuild manual fixes from the last known-good baseline, never from a re-derived one.** Re-running the automatic placement algorithm with certain aircraft excluded changes how it places *everything else* (availability and ordering shift), which can silently introduce brand-new conflicts elsewhere. When hand-patching specific aircraft: start from the last verified-clean dataset, remove only the exact entries being replaced, add the verified replacement, then re-check the *entire* affected city for conflicts — not just the touched entries. (Skunkworks Alpha)
- **Use a small time tolerance when conflict-checking, but investigate every flagged case regardless.** Floating-point or rounding differences between independently-computed times (e.g. 1408.8 vs. 1409.0) can produce false-positive "conflicts" of a few tenths of a minute — but don't reflexively dismiss all near-misses as rounding noise; several will be genuine bugs. Check each one before deciding which it is. (Skunkworks Alpha)
- **Hardcoded time conversions are a recurring error source.** Converting a displayed time like "7:35P" back to minutes by hand is where mistakes creep in (e.g. typing 1355 instead of 1175). Capture and reuse the exact numeric values a feasibility check already computed, rather than re-deriving them from a formatted string. (Skunkworks Alpha)
- **Sample at 1-minute resolution**, not coarser. A 5-minute-step check can silently miss real, narrow single-minute capacity spikes that only surface once detailed per-airport charts are built — chart-building is an inherently stricter test since every event needs an actual assignable slot.
- **No acknowledged-but-unresolved capacity violations at final delivery.** "Documented exception" is not an acceptable resolution for a genuine overbooking — it invites piling more service onto an already-broken spot. When resolving a capacity cluster by shifting a route's timing, first confirm the route doesn't also touch a *second* capacity-constrained city (or the fix may just relocate the problem), and prefer shift candidates with genuine unused slack over arbitrary shifts.
- Distinguish a **true capacity ceiling** (fix: cap increase or frequency cut) from a **scheduling/interleaving difficulty** (fix: restructuring, not more gates) — test empirically rather than assume.
- Same-day shuttle patterns that won't reconcile need structural splitting across more tails/days, not more gates.
- A hand-built greedy-plus-restart heuristic plateaus around 95–97% conflict-free on a network this size; closing the remainder needs real constraint-solver tooling.
- **Full implementation detail** (exact touch-time thresholds, code, and a worked example) lives in `Gate_Utilization_Process.md` and its counterpart `Gate_Consumption_Process.md` in Project Knowledge — this section covers the methodology and principles; those files are the authoritative technical reference.

### 1.8 Exception & Iteration Policy
- Gate/stand exceptions are only acceptable in the **opening stages** of a schedule build. After the third schedule file has been generated for a given build, every gate and stand exception must be fully cleared — resolved for real, not documented and carried forward — before a new schedule file can be assembled.
- Resolving a late-stage exception may require materially restructuring the affected route's day, not a light touch. If an exception reappears on a *different* route after a fix, that's a sign the fix moved the conflict rather than resolved it — the underlying capacity, not just the specific route, needs another look.
- **Maintaining service to all destinations is a hard constraint, checked explicitly after every reconciliation pass** — never assumed. A fix aimed at one problem (fleet-cap trimming, gate conflicts, closed-loop restructuring, frequency capping, shuttle-splitting, etc.) can silently zero out an unrelated destination as a side effect. If a fix would drop a destination to zero, revise the fix rather than trade the destination away.
- When an optimization pass operates on data copies, verify results are written back to the actual object graph before saving — spot-check a known structural invariant after every finalization step.

### 1.9 File Versioning Convention
Every regenerated schedule file must include its version number in the file name (e.g. "Schedule 5, Version 3"). Increment on every regeneration, so the version number and the "which regeneration is this" count (relevant to the exception policy in §1.8) always agree.

### 1.10 Deliverable-Request Convention
By default, a generic "regenerate the files" request means the Schedule workbook and the route map only — not per-airport gate/stand utilization charts, which are produced only when specifically requested. Re-deliver the Build Instructions file only if it has been edited since the last regeneration.

### 1.11 Finalize Procedure

**Throughout the build — not just at Finalize:** watch for two things and say so explicitly the moment they happen, rather than trying to reconstruct them later from memory of the whole session:
- **Lesson candidate** — something that took real trial-and-error to work out, a mistake caught and fixed, or a pattern likely to recur in a future build. Not every fix qualifies; a one-off correction specific to this schedule isn't a lesson, a reusable insight about *how* to build schedules is.
- **Override candidate** — any point where this build deliberately runs with a Part 2 Persistent value, or a `city_information.csv` field, set differently from its current stated default.

Keep a running list as these come up. Finalize's Phase 1 below only works if this happened along the way — it reviews what was flagged, it does not go looking for it retroactively.

**Trigger:** the build lead says something like "finalize this" or "finalize Schedule X" when a build has reached a stopping point worth locking in. This replaces the separate `Finalize_Procedure.md` document, which is retired — everything it covered now lives here.

**First question, every time, no exceptions: is this a Skunkworks build?**
This is asked directly and confirmed explicitly — it is *not* inferred from the chat's title or any other passive signal, since there is no reliable way to detect that automatically. The answer controls what Phase 1 is allowed to touch below. If the conversation has made this obvious well before Finalize is triggered, a quick explicit confirmation ("confirming — this is a Skunkworks build, so the shared reference files won't be touched, correct?") still happens rather than assuming. **This is a process rule, not a technical one** — nothing prevents a file from actually being written except this instruction being followed; there's no permissions system enforcing it. (Concrete example this actually caught: Skunkworks Alpha's lessons-learned document included a 6→9 focus-city gate-count change and SFB/RFD's promotion to focus-city status — both real outcomes of that build, both correctly *not* promoted into §2.2's defaults or `city_information.csv`'s `Status` column, since they're Skunkworks-specific results, not confirmed mainline decisions.)

**Phase 1 — Lock & Stage**
1. Confirm the version label being finalized (e.g. "Schedule 5, Version 12" or "Skunkworks Bravo, Version 3").
2. Review anything flagged as a candidate lesson during the session. Walk through each one explicitly — keep, discard, or reword. Anything kept gets drafted directly into §1.12 (Standing Lessons Log), tagged with the schedule/version it came from. **This step happens regardless of Skunkworks status** — a genuine process lesson learned while testing a divergent build is still a real lesson.
3. Review anything flagged as a candidate Persistent-condition override during the session (Part 2 tables, or a `city_information.csv` field). Same explicit per-item decision.
4. **If this is a Skunkworks build, stop here — skip steps 5 and 6.** `city_information.csv` and every Part 2 Persistent table are read-only reference for a Skunkworks session. Nothing from step 3 gets drafted back into them, no matter what was overridden mid-build, and no destination or Active-status change from this build gets written to `city_information.csv` either. If the build needs its own lasting record of what it ran with (a different gate cap, a hypothetical new destination, etc.), that record lives in the Skunkworks build's own schedule-specific file — never in a shared reference file. If `extract_schedule.py` needs metadata for a hypothetical destination that doesn't exist in the mainline `city_information.csv`, maintain a small supplementary CSV for that build and pass it via the script's optional 5th argument, rather than editing the shared file.
5. *(Mainline builds only.)* If there were destination changes this build (per the Part 3 gate), confirm each addition has a complete row in `city_information.csv` and each removal has its `Active` status flipped — draft the updated file.
6. *(Mainline builds only.)* Draft any other promoted Persistent-table or `city_information.csv` changes from step 3.

**Phase 2 — Export**
7. Ask for the finished workbook to be uploaded directly into this chat — not read from Project Knowledge. The PK mirror truncates large sheets (confirmed: Schedule 4's All Flights tab, 1,535 rows, doesn't come through complete, and the PK copy isn't even a valid `.xlsx` binary). This step is never skipped by pointing at `/mnt/project` instead.
8. Run `extract_schedule.py` against the uploaded workbook and the current `city_information.csv` (or a Skunkworks build's supplementary CSV, per step 4).
9. Report the script's data-quality check in full before treating anything as final — duplicate Pairing Numbers mapped to more than one city pair, duplicate/reused Flight Numbers mapped to more than one Pairing or departure time, null values, cities with flights but missing metadata, any city with an unrecognized `Status`.
10. If issues were found, resolve them (fix the workbook, or fix `city_information.csv` if it's a genuine metadata gap) and rerun — never ship a known-bad export.
10a. Generate the timetable app data files (`schedule_<id>.json` and the updated `schedules.json` manifest entry) following `Timetable_App_Process.md`'s schema and generation steps exactly — this is a standard, automatic part of every Finalize, not a separate request. Confirm the connection-window values (`minConnect`/`maxConnect`) for this schedule explicitly rather than defaulting silently — see that document's field notes.
11. Hand back everything generated this session as one batch: `schedule_<id>.json`, an updated `schedules.json` entry, and — if Phase 1 produced them — the updated Template and/or `city_information.csv`.

**What Finalize does not do:**
- Does not upload anything to Project Knowledge. Every file handed back still needs to be manually uploaded.
- Does not push or verify anything on GitHub. Also manual, whether done directly or via Claude Code.
- Does not touch `city_information.csv` or any Part 2 Persistent table for a Skunkworks build, regardless of what was discussed or overridden mid-session.

### 1.12 Standing Lessons Log
*Carried forward from the Schedule 4 build. Add new lessons here (with a version tag) as future builds surface them — don't delete prior lessons even if a given build didn't trigger them.*

**Data validation**
1. Always validate an O-D matrix's actual dimensions before use — a truncated file can look complete at a glance.
2. Check whether a hub's O-D figures are already metro-summed with a secondary airport before computing any target-driven scaling multiplier.

**Demand modeling**
3. Direct O-D demand between a spoke and a hub measures narrow point-to-point demand, not connecting value (see §1.2).
4. Use relative-share allocation, not demand/(seats×LF) directly (see §1.2).
5. Metro-summing deflation applies whenever the inflated city is the pair's *origin*, not only when it's the stated target; check a sizing methodology's actual target before calling a secondary connection undersized; an existing superior alternative can undercut a connecting-value case even with real feed demand; cross-check implausible source-data magnitude against an independent reference as standing practice (see §1.2). (Skunkworks Alpha)

**Fleet & capacity**
6. Fleet capacity must be measured in aircraft-minutes (block + turn time by actual distance), never a flat flights/day proxy. Calibrate the total flight-count budget against real aircraft-minutes capacity before doing proportional demand allocation.
7. A flat per-market (per-Pairing, not per-Route) frequency cap is a high-leverage lever for controlling gate load at the busiest markets for a small flight-count cost. Schedule 4 used 7 round trips each-way informally; Skunkworks Alpha's more deliberate 6 RT/day cap is the one carried forward as the active default — see §2.7.
8. Sanity-check real-world runway/aircraft compatibility for any candidate destination that's notably small or unusual, not just demand and gate math (see §1.3 step 8, §2.12). (Skunkworks Alpha)
8a. Track fleet-count against capacity *inline during construction*, not only after the schedule is complete — check the running total as each line finishes, and rebalance (move the over-capacity fleet's largest non-trunk routes to a sibling fleet type with spare capacity) before building goes further, rather than discovering an overage only at the end. (Schedule 5 v3)

**Line construction**
9. A greedy line-builder must not abort an entire fleet's construction on one failed attempt — retry from whichever anchor has the most available legs, stop only when nothing schedulable remains.
10. Verify day-to-day location continuity explicitly and separately from day-count.
11. Fleet build order (largest to smallest) must be sequential and cumulative — see §1.4.

**Gate/schedule reconciliation**
12–19. See §1.7 in full — claim-window-vs-assignment distinction, cyclical checks, RON gate-hold default, the waypoint pattern, rebuilding manual fixes from a known-good baseline, time-tolerance discipline, hardcoded-time-conversion risk, 1-minute sampling, no-unresolved-violations policy, true-ceiling-vs-difficulty distinction, shuttle splitting, and heuristic plateau. (Several added from Skunkworks Alpha — see §1.7 itself for which.)

**Network design**
20. Apply geographic-balance constraints alongside pure demand ranking for hub/focus-city selection — demand-only selection has produced real regional coverage gaps in past network iterations (see §1.1). (Skunkworks Alpha)

**Process**
21. Verify data-copy results are written back to the real object graph before saving (see §1.8).
22. Reserve dedicated capacity for point-to-point routes or build them first — they get dropped disproportionately under construction pressure.
23. Verify three things independently for every routing line, not just day-count: (a) day-to-day continuity, (b) true closure (start city = end city), (c) at least one overnight at a hub or focus-city MX base. A line can pass day-count and even continuity checks while still never closing, or closing but never touching a hub. Build closure into line construction from the start (Eulerian-circuit decomposition, Hierholzer's algorithm) rather than patching afterward.
24. Maintaining service to all destinations must be checked explicitly after every reconciliation pass — see §1.8.
25. Flag explicitly when a routing under discussion is already load-bearing for a prior fix, before modifying it further — and if the change is safe, say why (e.g. "this frees the gate earlier, not later") rather than just asserting it is. (Skunkworks Alpha)
26. Treat user-caught errors as signal, not noise. Direct, specific spot-checks catch real bugs that automated checks miss — when one lands, verify precisely and correct it, rather than defending the original answer. (Skunkworks Alpha)
27. Respect a "leave it alone" decision without re-litigating it — but keep proactively surfacing other genuinely thin trade-offs (e.g. gate tightness plus weak demand together) rather than stopping at the first constraint found. (Skunkworks Alpha)

**Route-by-route fleet optimization (post-delivery refinement)**
28. Repeatable per-route method for filling idle aircraft time: compute the idle window, check inter-hub demand from the anchor city for hubs not yet touched that day, check destination markets with an evening (17:00–20:00) demand-weighted coverage gap, then verify every addition against both curfews and real gate capacity. When a destination-curfew violation shows up, the fix is resequencing (curfew-constrained legs first, hub legs last), not dropping or downgrading the destination.

28a. **Extended for multi-hub assignment (Schedule 6 prep):** when the "check inter-hub demand from the anchor city for hubs not yet touched that day" step in #28 comes up empty against the anchor's *currently-scheduled* hub(s), don't stop there — check the anchor's full §1.3c-qualified hub list, not just what it currently has flights to. A city's tier cap (§2.3) can leave it eligible for a hub its group qualifies for but that didn't make the cut at that city's own size — this is exactly the tactical valve for those cases, using real observed idle capacity as the evidence a second hub touch is actually worth adding, rather than waiting for a tier-cap or threshold change. Concretely: a bottom-quartile city capped to its primary hub alone, but whose group qualifies for a secondary, is a legitimate candidate for an idle-time add to that secondary — do the demand/curfew/gate checks in #28 exactly the same way, just against the wider candidate set.

  Bounds on this: (a) never route to a hub the anchor's *group* doesn't qualify for at all under §1.3c, even if a route happens to have idle time near it — group-level qualification is still the geographic/demand floor, this only relaxes the *city-tier* cap, not the underlying eligibility; (b) this is a tactical, per-build add, not a roster change — it doesn't rewrite `Hub_Assignment` in `city_information.csv`; (c) if the same anchor city gets the same tactical add across multiple consecutive builds, that's worth flagging at Finalize as a candidate for revisiting its tier cap for real, rather than re-adding it by hand every time.
29. Individual gate-conflict checks against a static snapshot go stale the moment a second edit touches the same city. After a batch of manual edits, always re-verify **both gate/stand capacity and routing continuity** across the whole network from scratch before considering the batch final — a batch of fixes can silently break continuity even when gate/stand capacity still checks out. (Continuity re-check added from Skunkworks Alpha; the original version of this lesson only named gate/stand capacity.)

**Section 2.6 / departure spacing (Schedule 5 v3)**
30. Section 2.6 compliance must be checked *inline during construction* (a live search across the full valid start-time range against a running registry of what's already been placed), not as a post-hoc repair pass on a finished schedule — a repair pass working inside a solution space already constrained by ~150 other independent decisions plateaus far short of full compliance, chasing its own tail (fixing one pair's spacing re-breaks another's) rather than actually converging.
31. Rolling 10-day base-RON window: a 1-day-over-boundary overage has now been accepted twice (Schedule 5 v2.1, v3) as a minor, non-blocking exception. This is now a **standing permanent grace** — a 1-day overage doesn't require active confirmation each time, but must still be logged/flagged wherever build results are reported, so it stays visible rather than silently accepted.
32. Curfew must be validated as a full window (an explicit EARLIEST floor *and* the curfew ceiling), never as an upper-bound-only check. A one-sided check silently allowed a day to start at 01:00 for several build iterations before being caught — the bug hid in plain sight because every existing check only asked "is this too late," never "is this too early."
33. Flight numbers must key on Route (a unique Line+Day position), never on Line, and never on city-pair-and-time alone. Two different lines coincidentally sharing a departure slot must never collapse onto the same flight number — and critically, whatever key flight-numbering uses, any deduplication-based validation (e.g. Section 2.6 checking) must use the *same* key, or genuine violations hide underneath the numbering bug undetected.
34. When retiming to fix a bug, a fix that touches an EARLIEST-floor violation must also confirm no OTHER numbering/validation logic implicitly depended on the corrupted timestamp — a single root-cause fix can surface several previously-hidden violations at once (Schedule 5 v3 found 18 genuine zero-minute Section 2.6 violations this way, previously invisible under a flight-numbering bug).
35. Construction fixes proven out in Schedule 5 v3, now permanent defaults (see §1.1–1.7 as applicable): leg-by-leg hub-context tracking for RON credit (not day-boundary-only tracking); explicit trunk-route exemption from any demand-based fleet reassignment; explicit pendant/spoke clustering in circuit construction rather than random-shuffle; disconnected sub-component detection and splicing during circuit construction; a physics-derived day-length ceiling (from block-time formulas) rather than an arbitrary fixed leg cap.

---

## PART 2 — 🟢 PERSISTENT: Standing Constraints & Conventions

### 2.1 Hubs & Focus Cities
- **5 primary hubs:** PHF (Newport News VA — HQ), SYR (Syracuse), DAY (Dayton), MCI (Kansas City), JAX (Jacksonville).
- **PHF enplanement planning baseline:** ~510,000 annual (PHF's 2005–2011 AirTran-era historical high) — used to scale PHF's O-D pairs upward given the metro's small underlying size relative to CAA's HQ-hub role. *Scaling method (flat vs. weighted) is a per-build decision — see Part 3.*
- **Focus cities:** BHM (Birmingham) is a standing focus city (Persistent designation, not a per-build toggle). BHM functions as a maintenance base: routing lines anchored there RON at a hub on the same cadence as hub-based lines (preferably ~halfway through a 9–12 route line).
- **BHM as a secondary connection option (added Schedule 6 prep):** BHM does not count as one of the 5 hubs and does not participate in §1.3c's hub-qualification math — but it's a geographically viable secondary *connecting waypoint* for 28 of 55 intergroup pairings (flagged `(BHM)` in the Intergroup Demand Consolidated file), most heavily for FLP-bound traffic, where FLP's own geographic isolation means it never qualifies for a second real hub (§1.3c). Construction-time use of this annotation (e.g. weighting BHM-routed alternatives during bank/trunk-capacity decisions) is not yet implemented — it's documented and available, not wired in.
- **MX base rule (Persistent as of Schedule 5 Finalize):** MX bases = the 5 hubs + BHM + the top 6 non-hub/focus destinations by demand rank. The *rule* is now permanent; the specific 6 cities are re-derived from current demand rank each build (as of Schedule 5: SFB, RFD, FLL, DAL, PIE, BNA) and may change build-to-build as rankings shift.
- **RIC (Richmond):** cleared for service after PHF rescaling reduced the RIC:PHF asymmetry below the CVG:DAY caution threshold of 7:1, but not yet added as of Schedule 4 — standing candidate for a future round.

### 2.2 Gate/Stand Capacity Caps
| Location type | Gates | Hard Stands |
|---|---|---|
| Destination (standard) | 2 max | 2 max |
| Focus city (e.g. BHM) | 6 max | 4 max |
| Hub | 16 max | 8 max |

Gates and stands are tracked as **separate resource pools** — never combined in tracking or reporting.

### 2.3 Percentile Tiers & Minimum Flight Counts
Ranked population: all served destinations plus any active focus-city candidates.

**As of Schedule 6, the hub *count* per tier is a cap on how many of the city's
group-qualified hubs (§1.3c) it actually gets service to** — `min(tier cap, group's
qualified hub count)`. Which specific hub(s) fill each slot is no longer a manual
choice; it's whichever hub(s) the group qualified for, in qualification order
(primary first, then secondary, tertiary, quaternary).

| Percentile | Minimum | Hub count cap |
|---|---|---|
| 0–25th | ≥3 flights to one hub | 1 (primary only — the "smallest cities" exemption) |
| 26th–70th | ≥6 flights, split across qualified hubs | 2 (primary + secondary, if qualified) |
| 71st–89th | ≥8 flights, split across qualified hubs; at least one round trip to each qualified hub beyond the first | 3 (+ tertiary, if qualified) |
| 90th+ | ≥8 flights, split across qualified hubs; at least one round trip to each qualified hub beyond the first | 4 (+ quaternary, if qualified) |

- A city's hub count can be **lower** than its tier cap if its group simply doesn't
  qualify for that many (e.g. an FLP city at the 90th percentile still gets 1 hub —
  FLP doesn't qualify for a secondary at all, see §1.3c). The cap is a ceiling, not
  a guarantee.
- These are literal flight (leg) totals, **except** the round-trip minimums for hubs
  beyond the first, which mean one full round trip (2 legs) — a single leg would
  strand passengers.
- Point-to-point flying cannot be used to satisfy these minimums, except as a
  substitute for a hub-count minimum at the 71st percentile and above, same as prior
  schedules.
- A focus city (BHM) may still substitute for one hub slot per prior convention.

### 2.4 Point-to-Point Flying Rules
- Allowed where strong demand justifies bypassing the hub structure. No real-world competitive-share assumptions (don't concede routes to competitors, but don't assume 100% capture either).
- Capped at **10% of the schedule**, measured by number of flights.
- Focus-city connections (e.g. BHM↔spoke) are exempt from this cap — they count as focus-city service, the same way hub-spoke flights aren't point-to-point.
- Err toward the hub-spoke operation when balancing aircraft allocation between the two.
- Apply the **200nm rule** (§2.9) when assessing whether a market needs standalone service at all.

### 2.5 Time Windows & Gate Claim Rules
- No originating departure before **04:30**.
- No destination departure after **21:00**.
- No hub/focus-city departure after **23:30**.
- Red-eyes may depart after 21:00 but not after 01:00, landing 04:30–06:30.
- **Gate claims:** originating flights claim a gate 1 hour prior to departure; terminating flights claim it for 45 minutes after arrival; turns claim a gate for a minimum of 40 minutes (longer if needed). One aircraft per gate at a time. Hard stands are for RON/ROD aircraft.
- **As of Schedule 6:** "longer if needed" routinely means aligning with the aircraft's next assigned bank departure (§1.6a) — 40 minutes is the absolute floor, not a target. A turn needing more than 150 minutes to hit its next bank should be modeled as a deliberate hold (§1.7's waypoint pattern), not a turn.

### 2.6 Departure Spacing Matrix
**Status: rescoped during Schedule 6 prep, prior to kickoff — confirm at Part 0.** Its
relevance diminishes under
multi-hub assignment (§1.3c) — a destination reaching 2-4 hubs naturally spreads
across the day without the formula forcing it — but it still needs to catch the
degenerate case: a destination with two departures at 06:15 and 07:30, then nothing
for the rest of the day. Split into two checks that now run at different scopes.

**Check A — same-pairing degenerate clustering (unchanged, non-hub-bound flying
only).** Original purpose and formula, unchanged, for spoke-to-spoke and
point-to-point pairings not governed by bank timing:

    HARD_FLOOR = 30 min       -- absolute minimum, never overridden by any other factor
    CEILING = 240 min          -- 4-hour cap; more than this doesn't meaningfully help
    station_factor = clamp(sqrt(4 / station_total_daily_departures), 0.7, 1.8)
    target = clamp(480 / N_pairing * station_factor, HARD_FLOOR, CEILING)

    One-exception allowance: a pairing with 4+ daily departures may have ONE gap below
    target (never below HARD_FLOOR) if every other gap for that pairing clears target.
    Near-target tolerance: a gap within 90% of target counts as compliant outright.

**For hub-bound pairings (destination is one of the 5 hubs): the even-spacing
*target* formula above no longer applies.** §1.6a's bank timing decides when these
departures happen — two departures to the same hub 40 minutes apart because they're
each serving a different bank is correct, not a violation, even though it would have
failed the old `hub_factor`-weighted target. The `HARD_FLOOR` (30 min) still applies
as a sanity check against genuinely redundant back-to-back departures with no bank
rationale.

**Check B — city-level dead-zone check (NEW, replaces the old per-pairing coverage
role for hub-bound flying).** For each origin city, take the union of *all* its
daily departures — every pairing, every hub, combined into one sorted sequence — and
check cyclically (per the existing −1440/0/+1440 convention, §1.7) for any gap
exceeding `CEILING` (240 min). This is what actually prevents "06:15 and 07:30 and
nothing the rest of the day" under a multi-hub network: a city doesn't need any
*single* pairing to cover the day alone anymore, since its combined schedule across
2-4 hub connections is what has to avoid a dead zone.

**Updated priority order:** RON-at-destination / RON-at-MX-base coverage outranks
bank timing and 2.6 alike; bank timing (§1.6a) outranks 2.6; 2.6 (both checks)
outranks aircraft utilization, which is now explicitly flexible re: turn times
(§1.6a) — see the full updated hierarchy in §1.6a.

**Construction-time integration, not post-hoc repair:** unchanged principle — check
both A and B inline as each day's start time is chosen, against a live registry,
rather than building the whole schedule first and patching afterward (Standing
Lessons Log #30).

**Known open item, carried forward:** the constants above (480 numerator, 0.7/1.8
station-factor bounds, 90% tolerance) were tuned to "good enough" for Schedule 5 v3,
not independently stress-tested, and now apply to a narrower slice of flying
(non-hub-bound only) — worth re-checking whether they still fit that narrower role
once Schedule 6 has real data.

Check within a single direction only (not mixed with the return). Distinct from the
per-market frequency *ceiling* (§2.7) — this is a spacing floor, not a cap on total daily
service.

### 2.7 Per-Market Frequency Ceiling
**Status: ACTIVE as of Schedule 5 Finalize.** A hard cap of 6 round trips/day (12 flights)
per spoke/market (i.e. per Pairing, not per Route) applies -- originally used in
Skunkworks Alpha as a fix for a specific demand-formula failure mode on very short,
high-demand routes. Confirm the exact number at Finalize each build if it needs
revisiting; 6 RT/day is the carried-forward default.

### 2.8 Routing Line, Pairing, and Flight Numbering Conventions
Three distinct numbers appear on the All Flights tab, and they mean three different things — don't conflate them:

- **Route** — the aircraft's operating day: everything one tail flies in a single 03:00-to-03:00 window, which can be several legs (up to 13+ seen in practice). Sequential within a Line, chained so the aircraft's day-N route ends where day-N+1 begins. Since a Line is single-fleet-type throughout, Route numbers naturally fall into per-fleet blocks — the actual current ranges (verified against the Schedule 4 v14 workbook, not assumed):
  - CRJ200: 100s–200s (101–170 seen)
  - CRJ700: 300s–400s (301–360 seen)
  - CRJ900: 500s–600s (501–539 seen)
  - MAX9: 700s (701–730 seen)
  - *(Correcting the record: earlier versions of this document attributed this block table to "routing numbers" generically and it was actually being read off the wrong field — see Pairing Number below for what those numbers actually were.)*
- **Pairing Number** — identifies a specific directional city pair (e.g. BUF→DAY is Pairing 300, DAY→BUF is Pairing 313 — each direction gets its own number). Renamed from what earlier versions of this document called "Flight Number." **Not fleet-type blocked** — a pairing can be served by more than one fleet type over its life, and nothing about the number should be read as implying a fleet type. Schedule 4's pairings happened to cluster by fleet type only because each one was served by a single fleet type in practice at the time — that was incidental, not a structural rule, and shouldn't be treated as one going forward.
- **Flight Number** — new as of this version. Identifies one specific scheduled departure (a city pair *and* a specific time of day) — the 8:05a BUF-PHF departure and the 1:00p BUF-PHF departure get different Flight Numbers even though they may share a Pairing Number. A Flight Number recurs identically every day that specific departure operates — it does not change day to day the way a truly per-occurrence identifier would.
  - Four digits, starting at **1001**. Flat — not fleet-blocked, deliberately, to avoid a fleet type ever outgrowing a sub-range (a real risk with a blocked scheme once any non-MAX9 type approaches 200+ daily departures).
  - Assignment order: where usable demand data exists, rank pairings by demand and assign ascending from 1001 (busiest routes get the lowest numbers). This tends to hand larger aircraft lower numbers too, without hard-coding fleet type into the scheme. If demand ranking isn't practically available at assignment time, fall back to straightforward sequential or random assignment — don't force a demand-based algorithm to work if the data isn't there.
  - Distinct number space from both Route (tops out under 800) and Pairing (tops out under 900) by construction — starting at 1001 guarantees no collision with either.
- **Line lettering:** MAX9 lines use single letters (A, B, C…); CRJ lines (all sub-types, one continuous sequence) use double letters starting AA, AB, AC…
- Each routing line: 9–12 routes (9–12 operating days), fleet type consistent throughout a line.
- Aircraft flying a line should RON at least once in a hub city (or active focus city), preferably around the fourth or fifth routing in a 9-day line.

### 2.9 Market-Service Distance Floor
The **200nm rule**: used to assess whether a market needs standalone service at all (a short-hop pair essentially duplicating an adjacent city's catchment gets excluded). Also governs connection filtering in timetable production — direct great-circle distance < 200nm excludes a city pair from Type C connections and Type 1 stopovers (does not affect nonstops to/from hubs).

### 2.10 Workbook Structure & Formatting Standards

**Tab order:** Summary, Routings, AC Utilization, one tab per hub, one tab per focus city, All Flights, Destination Summary, Routing Summary, Gate-Stand Utilization, Gate Exceptions (or equivalent named-exceptions tab whenever a schedule carries documented limitations).

**Destination Summary columns:** Code, City, Group, Tier, Demand Rank, Hubs Served, P2P Destinations (comma-separated list of other non-hub destinations with direct nonstop service — computed fresh from the actual current schedule each regeneration, not from any earlier planning list), Total Daily Flights, Gate Cap, Stand Cap.

**AC Utilization columns:** one row per route (line, fleet type, route number, day number, originator departure, terminator arrival, flight count, max idle time). Originator Departure Time and Terminator Arrival Time include city context in parentheses — e.g. `06:00 (DAY)` for a departure (destination in parens), `18:30 (JAX)` for an arrival (origin in parens). Max Idle Time includes the city the aircraft is idling in, e.g. `151 (CAK)`.

**Flight-listing tab color coding** (Routings, hub tabs, focus-city tabs — route-based coloring):
- Yellow (`#FFF2AE`) — originating flight (first leg of a routing day, starts fresh after an overnight).
- Light blue (`#D6E8F5`) — terminating flight (last leg of a routing day, aircraft RONs after).
- Light orange (`#FFE0B2`) — single-leg routing day (simultaneously originating and terminating).
- No fill — mid-day turn.

**All Flights tab (different rule — Pairing-based, not route-based):** sort order is Pairing Number, then Departure Time. Yellow = pairing's earliest departure of the day; light blue = its latest; light orange = operates once only; no fill = any operation in between. Call out both conventions on the Summary tab since they differ from the route-based rule above. (This shifted from "Flight Number" to "Pairing Number" once Flight Number became unique per departure time — under the old field this rule made sense because the same number could legitimately appear several times a day on a shuttle-style route; Flight Number, by design, essentially never repeats within a single day, so it can't drive this convention anymore.)

**City naming convention (Destination Summary "City" column):**
- Single airport in the city, or we fly to the primary: `[City] [State]` — e.g. `Buffalo NY`.
- Airport genuinely serves two named cities: `[City]/[2nd City] [State]` — e.g. `White Plains/Westchester NY`.
- Secondary airport, same city as the primary: `[City] [State] ([Airport])` — e.g. `Dallas TX (Love)`, `Houston TX (Hobby)`.
- Secondary airport in a *different* city from the primary: `[Big City]-[Airport City] [State of airport]` — e.g. `Chicago-Rockford IL`, `Philadelphia-Trenton NJ`, `St. Louis-Belleville IL`, `Orlando-Sanford FL`.
- Conventionally-hyphenated two-city airport names keep the hyphen (don't convert to slash) — e.g. `Akron-Canton OH`, `Gulfport-Biloxi MS`, `Greenville-Spartanburg SC`, `Raleigh-Durham NC`, `Sarasota-Bradenton FL`.
- Three-city metros use the first/primary city name only — e.g. `Allentown PA`, `Appleton WI`, `Greensboro NC`.
- Metro spans two states — resolve case by case — e.g. `Hartford CT` (BDL, also serves Springfield MA), `Tri-Cities TN/VA` (TRI).
- A demand-model "secondary" airport with its own strong independent place identity isn't automatically renamed under the secondary-airport rule — e.g. `Fort Myers-Punta Gorda FL` (PGD), `Tampa-St Pete FL` (PIE), unlike the unambiguous DAL/HOU cases.
- Regional-branded airports may not fit the pattern at all — e.g. `Fayetteville/Northwest AR` (XNA, officially "Northwest Arkansas National").
- When in doubt or a case doesn't cleanly fit any rule above, flag it for a decision rather than guessing.

**Logo usage:** Coastal American Airways logo (`assets/coastal_american_logo.png`, transparent background, pre-trimmed) placed top-left on route maps and any other generated PNG (e.g. per-airport gate/stand charts), sized to roughly 20–22% of figure width, positioned to avoid overlapping subtitle/legend. Not required inside the Schedule workbook itself.

**Standalone gate/stand chart naming:** `"XYZ Gate Utilization, Sked N, Ver M"` — XYZ = airport code, N/M = schedule and version numbers of the underlying data.

**Workbook-wide conventions:**
- Font: Arial throughout, all tabs.
- Header rows: bold white text on dark navy fill (`#1F3864`), centered.
- Data tabs: freeze panes below the header row; auto-size columns to content (min ~8 chars, max ~40).
- Numeric/derived summary values use real formulas (e.g. `=SUM(...)`), not hardcoded results, where the underlying values live elsewhere in the same tab.

### 2.11 City Reference File — `city_information.csv`
Replaces the earlier `metro_mapping_final.csv`. One row per airport code (5 hubs + all destinations, BHM included). This is the single source of truth for per-city facts — nothing in this list should ever be duplicated inline in this document or in build notes.

| Column | Contents |
|---|---|
| Code | IATA airport code |
| City | Display name per the naming convention in §2.10 |
| Long_City | Only populated where the display City compresses a multi-city metro name (e.g. three-city MSAs) — sparse by design; most rows are blank |
| Airport_Name | Full official airport name |
| Group | One of the 11 geographic groups (NEC, MAC, LEC, APP, GLC, UMP, OZK, TEX, CGI, FLP, GCP), or `HUB` for the 5 hubs |
| Hub_Assignment | **As of Schedule 6:** a computed, slash-separated list of the city's qualified hubs in priority order (primary first — e.g. `JAX/PHF/DAY` for a 90th-percentile CGI city), produced by `compute_multihub_assignments.py` (§1.3c) — not hand-edited. Still `-` for hubs themselves. This remains the geographic/demand *eligibility* list, not a per-schedule count of which hubs actually get flights in a given build (that lives in the schedule workbook's Destination Summary tab) — a city can be eligible for a hub and still end up with zero flights there if construction-time capacity doesn't support it |
| Status | `Hub`, `Focus City`, or `Destination` |
| MX_Base | `Y`/`N` — independent of Status; today this equals hubs + focus cities, but is tracked separately since that may not always hold (e.g. Skunkworks-style builds) |
| Classification | `Primary`, or `Secondary (summed w/ [airport])` for the confirmed secondary-to-primary demand-summing pairs |
| Demand_Data_Source | `BTS` (a real DB1C pull), `Estimated` (§1.3 step 4's fallback — regression/comparable-city method, not a real pull), or `Zero-BTS-Floor` (a real pull came back with no measurable volume, likely a survivorship-bias data artifact — different problem than `Estimated`, don't conflate) |
| Gate_Allocation_Override / Stand_Allocation_Override | Blank = use the Status-based default from §2.2. Populated only when a city has a standing, deliberate cap different from its default — this is a durable policy change, not the same thing as a workbook's per-build Gate Exceptions tab (which documents transient conflicts in one schedule, not a permanent cap change) |
| Timezone | Eastern / Central / Mountain — drives the ‡ Central-time marking convention in timetable production |
| Latitude / Longitude | For route-map and geographic tooling use |
| Runway_Length_Ft / Elevation_Ft | Real-world operational facts, not derived judgments — don't store a pre-computed "compatible with fleet X" flag here, since that would go stale the moment the fleet mix changes. Compare against §2.12's fleet minimums instead, whenever it actually matters. Populated at §1.3 step 8 for new destinations; blank for the rest of the roster as of this version — a backfill for existing cities is a separate decision, not assumed by adding the column. |
| Notes | Freeform — naming-convention exceptions, demand-data caveats, anything flagged for a decision rather than guessed |

**Explicitly not included:** Tier and Demand Rank. Both are recomputed from the O-D matrix every build and would go stale in a persistent file — they belong in the schedule workbook's Destination Summary tab, not here.

### 2.12 Fleet Runway Minimums
Reference thresholds for the runway/aircraft compatibility check in §1.3 step 8. These are **conservative screening triggers, not engineering-grade cutoffs** — actual minimum runway length depends on weight, temperature, elevation, and flap setting, and varies by thousands of feet depending on conditions. Treat a candidate airport below its assigned fleet's threshold as "look at this one more carefully" (using the aircraft manufacturer's actual airport-planning documents, not general web content), not as an automatic disqualification.

| Fleet | Conservative screening threshold |
|---|---|
| MAX9 | 6,000 ft |
| CRJ900 | 5,500 ft |
| CRJ700 | 5,000 ft |
| CRJ200 | 4,500 ft |

*(Placeholder figures pending a real sanity-check against manufacturer airport-planning data — treat as directional until verified, not as settled fact.)*

---

## PART 3 — 🟡 VARIABLE: This Build's Specifics

*Rewrite this entire part for each new schedule. Nothing here should be assumed carried over from the prior build without an explicit check.*

### 3.1 Destination Changes
- Total destination count this build: _____
- **Additions** — for each, confirm §1.3 was completed and give: code, City, Group, hub pairing, Classification, demand-data method (fresh BTS pull vs. estimated from comparable cities).
- **Removals** — for each, confirm §1.3b was completed (Active flipped, reason noted).
- If neither applies (Part 0's gate answered "No"), leave this section as "No destination changes this build" and move on.

### 3.2 Fleet Composition
- Fleet size and mix are fully Variable — confirmed to change build over build. Never assume continuity from the prior schedule.
- Total aircraft: _____
- By type: _____
- Update §2.8's routing-number-block mapping if the type mix changes (e.g. a fleet type is dropped or added).

### 3.3 Enplanement / Demand-Scaling Adjustments
- Hub(s) receiving a target-driven scaling adjustment this round: _____
- Method (flat proportional / weighted / other): _____
- Multiplier or target basis: _____

### 3.4 Deliverables This Round
- [ ] Schedule workbook
- [ ] Route map (PNG)
- [ ] Timetable (if in scope this round)
- [ ] Per-airport gate/stand utilization charts (only if specifically requested)
- [ ] Finalize (§1.11) — once the schedule is ready to ship, not before. Produces `schedule_<id>.json` and a `schedules.json` entry; also the point at which any Phase 1 changes to the Template or `city_information.csv` get drafted for upload.

### 3.5 Deferred to Future Work
*Running list — review at the start of the next build (Part 0 checklist) and promote items in or explicitly re-defer them.*
- _____

---

## Resolved Since v0.1
1. Fleet size/mix: confirmed fully Variable.
2. BHM status: confirmed Persistent (standing focus city).
3. Percentile tiers, gate/stand caps, time windows: confirmed Persistent.
4. Roster now lives in `city_information.csv` (§2.11), built directly from `Schedule_4__Version_14.xlsx`'s Destination Summary and Gate-Stand Utilization tabs plus `metro_mapping_final.csv`'s Group→Hub assignments — includes CHS and BTR. `metro_mapping_final.csv` has since been deleted from Project Knowledge.

## Resolved Since v0.2
5. `Finalize_Procedure.md` merged into §1.11 and retired as a standalone file.
6. Skunkworks builds are confirmed read-only with respect to `city_information.csv` and all Part 2 Persistent tables — enforced by an explicit Y/N confirmation at the start of Part 0 and again at the top of Finalize (§1.11), not by any attempt to read the chat's title (no tool available makes that possible).
7. `Active` / `Status_Changed_In` columns added to `city_information.csv`. §1.3 (additions) and new §1.3b (removals) updated accordingly; `extract_schedule.py` gained a matching reconciliation check, tested clean against the real Schedule 4 v14 workbook (1,535 flights, 105 cities, no issues found).

## Resolved Since v0.3
9. Versioning note rewritten — no longer describes the abandoned copy-per-schedule model. Each build is its own long-lived chat (confirmed); Part 0/3 answers stay there and are never written back.
10. Added the explicit "flag lesson/override candidates throughout the build" instruction that §1.11's review steps were silently assuming.
11. Part 3 streamlined: 3.1 (roster) and the old 3.4 (new-destination detail) merged into one Destination Changes section; Deliverables reconciled with what Finalize actually produces instead of duplicating it.
12. Skunkworks write-protection explicitly noted as a process rule, not a technical one — no permissions system backs it.

## Resolved Since v1.0
13. `Demand_Data_Source` column added to `city_information.csv` (`BTS` / `Estimated` / `Zero-BTS-Floor`) — estimated-vs-real demand data is now a queryable field, not something findable only by reading `Notes` text. §1.3 step 4 and Part 0 both check the running count and stop to prompt for a BTS refresh at 5 `Estimated` cities.

## Resolved Since v1.1
14. §2.8 corrected: the fleet-type block table was actually describing Pairing Number, not Route — Route has its own, separate, previously-undocumented block convention, now recorded accurately (verified against the real Schedule 4 v14 workbook, not assumed).
15. "Flight Number" renamed to "Pairing Number" and confirmed **not** fleet-type blocked — a pairing can be served by more than one fleet type; Schedule 4's apparent fleet clustering was incidental, not a rule.
16. New "Flight Number" introduced: unique per specific departure time (not per calendar occurrence — recurs identically every day that departure operates), 4-digit starting at 1001, demand-ranked assignment where feasible with a random/sequential fallback where it isn't. Forward-only; Schedule 4 is not being retrofitted.
17. §2.10's All Flights tab coloring convention shifted from the old Flight Number to Pairing Number, since Pairing is the field that still legitimately recurs multiple times a day on shuttle-style routes.
18. `extract_schedule.py` updated to read both `Pairing` and `Flight` columns, gained a Pairing-integrity check (does a Pairing map to more than one city pair) and a new Flight-integrity check (does a Flight Number map to more than one Pairing/departure-time combination) — tested against deliberately broken synthetic data, both fire correctly. This is a breaking change for any workbook built before this rename.

## Resolved Since v1.2
19. 15 lessons from the Skunkworks Alpha lessons-learned document added across §1.1 (geographic-balance constraint), §1.2 (demand-data nuance: origin-side deflation, sizing-target checks, superior-alternative discounting, independent-reference cross-checks), §1.7 (claim-window vs. assignment, the waypoint pattern, rebuild-from-baseline, time-tolerance discipline, hardcoded-time-conversion risk), and the Standing Lessons Log (process/communication discipline; the routing-continuity refinement to the old #18, now #29). Runway/aircraft compatibility infrastructure added: `Runway_Length_Ft`/`Elevation_Ft` in `city_information.csv` (blank for the existing roster — population happens going forward at §1.3 step 8, not backfilled as part of this change), and a new §2.12 with conservative, explicitly-not-engineering-grade fleet runway thresholds. Two Skunkworks-specific items were deliberately excluded from promotion — see §1.11's Skunkworks note for the reasoning.

## Known, Accepted, Not Blocking v1.0
- Multi-session continuity: each build stays in one long chat, so a separate cross-session storage mechanism isn't needed for now. Revisit if that assumption ever stops holding.
- Skunkworks protection depends on the instruction being followed, not on any enforcement mechanism (see §1.11).

## Still Open
1. **JAX stand cap:** the live Schedule 4 workbook has JAX at 16 gates / **12 stands**, but §2.2's standing hub default is 16/8. Intentional override, or does §2.2 need updating?
2. **Classification cleanup:** several old "Secondary-candidate...FLAG" cities (MHT, ORH, PVD, HVN, ISP, SWF, HPN, ACY, TTN) are recorded as standalone Primary in `city_information.csv`, reflecting how the live schedule treats them — worth a quick confirm this was a real decision.
3. **Long City is sparse by design** (ABE, ATW, GSO, XNA, TRI only) — meant to grow as cases come up, not to be filled preemptively.
4. ~~**Connection quality was never a construction-time consideration through Schedule 5.**~~ **Addressed in v1.6 — see §1.3c (multi-hub assignment) and §1.6a (bank/wave design).** The 78%-structurally-impossible portion of this problem is what multi-hub assignment targets directly; §1.6a's deliberate bank design targets the remaining 22%-timing-failure portion. Not fully closed — §1.3c documents which group pairs remain unreachable in one hub touch even after multi-hub assignment (FLP/GLC/NEC/OZK/UMP's geographic ceiling) — but no longer an open design question, just a known residual gap.
5. ~~**The Intergroup Demand Consolidated file has never factored into route building.**~~ **Addressed in v1.6 — see §1.3c and §1.6a.** Intergroup demand now drives both multi-hub qualification (§1.3c) and hub bank sizing/priority placement (§1.6a), tackled together as this item originally proposed.
6. **Fleet mix reassessment for CRJ200** — the tightest-margin fleet type three consecutive builds running (Schedule 5 v2, v2.1, v3). Not resolved at Schedule 5 Finalize; carry into Schedule 6 Part 0 as a standing check.

---
## Resolved Since v1.4 (Schedule 5 Finalize)
- CHS/BTR demand data confirmed updated to real BTS pulls (August 2026 six-month refresh); `city_information.csv`'s `Demand_Data_Source` and `Notes` fields corrected to match — see "Still Open" #4 in the prior version, now removed.
- §2.6 Departure Spacing Matrix: adopted permanently. Fixed round-trips/day lookup table replaced with the context-sensitive formula developed in Schedule 5 v3 (station-size and hub-arrival factors, one-exception allowance, near-target tolerance) — see §2.6 for the full formula and its still-open constant-tuning question.
- §2.6's place in the priority hierarchy confirmed permanent: outranks utilization, does not outrank RON coverage.
- §1.7's waypoint-pattern gate assignment methodology: confirmed staying in `Gate_Utilization_Process.md` / `Gate_Consumption_Process.md` as the authoritative technical reference, with a pointer added to §1.7 for discoverability, rather than duplicating implementation detail into this document.
- Cross-connect P2P guidance (checking a hub's own spokes for real demand between them before assuming a new P2P pair needs dedicated capacity) confirmed as guidance, not a required screening step.
- Five Schedule 5 v3 construction fixes confirmed as permanent defaults — see Standing Lessons Log #35.
- §2.1: MX base rule (5 hubs + BHM + top 6 by demand rank) promoted from provisional to Persistent. The specific 6 cities still re-derive from demand rank each build.
- §2.7 Per-Market Frequency Ceiling: activated (was "not currently active"). 6 RT/day per market, confirmed as a per-Pairing (not per-Route) concept — Standing Lessons Log #7's "Schedule 4 used 7 round trips" reference was a separate, less formal historical number and has been reworded to remove the ambiguous "per-route" phrasing.
- Rolling 10-day base-RON window: a 1-day-over-boundary exception is now a standing permanent grace (see Standing Lessons Log #31) — still must be logged when it occurs, no longer requires active per-build confirmation.
- Flight-numbering and curfew-window bugs from Schedule 5 v3 documented as Standing Lessons Log #32-34, so they don't silently reappear if construction code gets rewritten rather than reused.

---
## Resolved Since v1.5
- Section 1.11 Phase 2 (step 10a, new): timetable app data-file generation (`schedule_<id>.json`, `schedules.json`) confirmed as a standard, automatic Finalize deliverable, now pointing to the new `Timetable_App_Process.md` for the full schema and generation steps -- reverse-engineering the schema from `index.html` should never need to happen again.
- `index.html` updated: the connection-window bounds (`minConnect`/`maxConnect`) were hardcoded constants in the app; moved to per-schedule variables read from the schedule's own JSON file, with a 30/240-minute fallback for schedule files generated before this change (e.g. `schedule_4_v14.json`) so nothing breaks retroactively. Footer display updated to surface the active connection window.

---
## Resolved Since v2.0
*Squashed from the v1.6 / v1.6.1 prep-cycle patch history — see git-style detail below.
All of it was built and reviewed before Schedule 6 kickoff (see the versioning note at
the top of this document).*

**Multi-hub assignment & bank design (originally v1.6):**
- **Fixed single/manual-dual `Hub_Assignment` retired.** Replaced with the demand-and-geometry-qualified multi-hub roster in §1.3c, computed by the new `compute_multihub_assignments.py` rather than set by hand at city-add time. Directly targets D1's root cause (single-hub spokes with no shared hub to connect through) rather than only its timing symptom.
- **§2.3 percentile tiers restructured** around a hub-count *cap* (1/2/3/4 by tier) applied against each city's group-qualified hub count, rather than a fixed "split between two hubs" rule with no mechanism for choosing which two.
- **Deliberate hub bank/wave design adopted (§1.6a)**, sized and prioritized by intergroup connecting demand — first real construction-time use of the Intergroup Demand Consolidated file (D2, resolved).
- **§2.6 rescoped**, not retired: same-pairing degenerate-clustering check unchanged for non-hub-bound flying; hub-bound pairing timing now deferred to bank assignment; new city-level (cross-pairing) dead-zone check added to preserve the "no long gap in a city's day" protection under a multi-hub network.
- **Construction priority hierarchy updated**: Bank timing inserted above §2.6 and aircraft utilization; utilization explicitly flexible on turn times beyond the 40-minute gate-claim floor (§1.6a, §2.5) to accommodate bank alignment, up to a 150-minute ceiling before a turn should be modeled as a deliberate hold instead.
- **Intergroup Demand Consolidated file**: `(BHM)` annotation added to 28 of 55 group pairs where Birmingham is geographically viable as a secondary *connection* option (distinct from a qualifying hub under §1.3c — BHM is a focus city, not one of the 5 hubs, and this annotation doesn't feed the §1.3c hub-qualification math). Methodology: circuity ratio ≤1.40x, the same approach used for the 200nm connection filter's exclusion table. The file's Group Key also picked up a majority-rule `(BHM)` flag (FLP, GCP, OZK, TEX).

**Naming, tactical-add extension, and version protection (originally v1.6.1):**
- **Construction library and orchestrator renamed**, dropping the Schedule-5-v3-specific naming that no longer described their role: `v3_lib.py` → `construction_lib.py`, `build_v3.py` → `construction_orchestrator.py`. Every calling file (`section26_repair.py`, `compute_opportunity_matrix.py`, `build_opportunity_matrix_wb.py`) and `README.md` updated to match. The working session directory these files (and their intermediate pickles) assume also generalized, from `/home/claude/schedule5/v3` to `/home/claude/caa_build`. The two old files themselves were removed from Project Knowledge as part of the v2.0 review (see below) — nothing should still reference them.
- **Post-generation utilization-add process (Standing Lessons Log #28) extended** with #28a: when filling idle time on a route, the anchor city's full §1.3c-qualified hub list is now in scope, not just its currently-scheduled hub(s) — the tactical mechanism for cases like ROA/AGS/MCN, capped to one hub by tier (§2.3) despite their group qualifying for more. Bounded to the group's actual qualification (doesn't override §1.3c), and doesn't rewrite `city_information.csv` — a recurring tactical add across builds is a Finalize-time signal to revisit the tier cap for real, not something to keep hand-patching.
- **File-path version protection.** New `pk_paths.py` resolves every reference file (`city_information.csv`, `airport_od_matrix_consolidated.csv`, etc.) to whatever the highest-versioned copy in Project Knowledge actually is, and generates the *next* version number when writing a new draft. Also recognizes the legacy `-N` suffix (e.g. the original `intergroup_demand_consolidated-1.xlsx`) as equivalent to `_vN`, so a file that predates the naming convention doesn't get silently missed. Wired into every script that touches a reference file: `construction_lib.py`, `construction_orchestrator.py`, `section26_repair.py`, `compute_opportunity_matrix.py`, `build_opportunity_matrix_wb.py`, `extract_schedule.py`, `process_chunk.py`, `compute_multihub_assignments.py`.

**Full Project Knowledge review, prior to v2.0:**
- **`v3_lib.py` and `build_v3.py` removed from Project Knowledge.** Confirmed byte-identical to `construction_lib.py`/`construction_orchestrator.py` except for the intentional rename edits — fully superseded, no unique content, not referenced by anything else in PK.
- **`FINALIZE_DISCUSSION_ITEMS.md` updated**: D1 and D2 marked addressed, each pointing to the specific sections above rather than left reading as open questions for Schedule 6 Part 0.
- **`Timetable_App_Process.md` and `Gate_Utilization_Process.md` updated**: bare `city_information.csv` references (stale now that PK keeps a version suffix on it) pointed at `pk_paths.py` instead, including the embedded example code in `Timetable_App_Process.md` Step 3. Also added a note distinguishing `minConnect`/`maxConnect` (the app's connection-search bounds) from the new hub bank window (§1.6a, a narrower construction-time concept) — the two are easy to conflate and aren't the same thing.
- Every other file in Project Knowledge (`Gate_Consumption_Process.md`, `index.html`, `schedules.json`, `schedule_4_v14.json`, `schedule_5_v3.json`, `airport_od_matrix_consolidated.csv`, the logo assets) checked and confirmed current — no stale references found.

---
*Template v2.0 — the multi-hub assignment and bank/wave design work (§1.3c, §1.6a), the construction-file rename, and file-path version protection, built and reviewed as Schedule 6 prep, entirely before Schedule 6 kickoff. `city_information.csv`, `extract_schedule.py`, `compute_multihub_assignments.py`, `construction_lib.py`, `construction_orchestrator.py`, and `pk_paths.py` ship alongside it.*
