# v1.4.3 cross-line AK/AS route reassignment — GSP/RDU swap

**Research candidate only. Do not release or merge.** The protected accepted Schedule 7 v1.4.3 draft remains 1,286 flights, 191 routes and 17 lines. The previous independent six-added-flight 1,292-flight reconstruction (R313 JAX, R338 RDU, R345 BWI) remains reproducible.

## Exchange concept

- R338 (AK day 1), originally PHF–SYR–PHF–PVD–PHF–SAV–JAX–SAV, takes over **existing flight #2035 PHF→GSP**, moving it from R345's evening into **13:53–15:08**, and **existing flight #2036 GSP→PHF** into **15:48–17:03**. Flight numbers, pairing identities and directional service remain intact.
- R338's #1493 PHF→SAV moves to **17:45–19:11**, with 42 minutes after #2036 and 49 minutes before its existing SAV→JAX 20:00 flight. R338 still terminates at SAV for AK day 2's SAV originator.
- R345 (AS day 6) retains newly staged CLT→BWI→CLT (13:37–16:27) and existing CLT→PHF 17:10–18:16; it takes over newly staged **PHF→RDU 19:15–20:05** and **RDU→PHF 20:45–21:35** from R338, terminating at PHF as before. Its next line day starts at PHF. No aircraft added.
- The GSP and RDU flight pairs are **both reassigned to a different physical line/day**, with their flight IDs (for original GSP) and route-day continuity preserved. This is a genuine swap, not relabeling.

## Preliminary passenger screen

A direct-plus-one-stop clock-window comparison (30–240 minute connection window), versus the retained 1,286-flight draft, found **zero lost direct/one-stop directional markets** and nine additional covered directionals with the full experimental 1,292-leg package. Therefore **no directional >8 pax/day market lost the last one-stop option** in this initial technical screen. The route assignment no longer has to sacrifice the AUS→SAV 18.9/day market that invalidated the earlier SAV→JAX transfer hypothesis.

**Important:** This screening is **not equivalent** to the application’s geographically reasonable-itinerary audit, native fixed-gate allocation, structural/overnight/planning tests, or passenger bank validation. Those checks remain mandatory before the swap can enter the accepted v1.4.3 draft. The 65-minute CLT–BWI block in the experimental 1,292 candidate still requires real-world review.

## Reproducible native check

`scripts/v143_gsp_rdu_pair_swap.py` builds from the separate experimental 1,292-flight R313/R338/R345 candidate, moves both flight pairs across AK and AS, reassigns exact PHF bank memberships, runs structural, overnight, fixed-gate, operating and planning validators, then writes `data/schedules/schedule_7_v1_4_3_gsp_rdu_swap_candidate/` **only on a full pass**. The official user-defined >8 pax directional one-stop guard is `scripts/v143_rebuild_guard.mjs`. The workflow `.github/workflows/v143-targeted-gsp-rdu-swap.yml` is a targeted research check; run on demand after confirming workflow controls are manual-only. **No native pass has yet been confirmed.**

## Rejected AK transfer

Moving original R338 SAV–JAX–SAV flights #2127/#2128 onto R339's early SAV hold initially required BHM→SAV #2068 to leave at 05:50 and arrive 08:03; alternatively it required significant retiming of R339's SAV→PHF leg. A technical one-stop screen found **AUS→SAV (18.9 pax/day)** lost its last one-stop option in either tested configuration, violating the explicit >8 pax safeguard. Even adding a new evening SAV–BWI return did not restore it. **Reject** that proposed transfer unless the AUS→SAV feed is explicitly preserved through a different reassembly. The research script `scripts/v143_ak_crossday_reassignment.py` remains available but is not an accepted draft change.

## Status

- Accepted saved draft: **1,286 flights**, unchanged.
- Staged R313/R338/R345 + BWI experimental reconstruction: **1,292 flights**, previously native and passenger-guard validated, not published.
- New genuine AK/AS GSP↔RDU exchange on that candidate: **1,292 flights**, preliminary stop-coverage-only pass; native validation pending.
- Production `main`: Schedule 7 v1.4.2, unchanged.
