# Addition to CAA_Build_Instructions_TEMPLATE_v2_0.md, Section 1.7

Insert as a new bullet in **Section 1.7 (Gate/Stand Validation Methodology)**,
immediately after the "waypoint pattern" bullet (the one beginning "The
waypoint pattern: validate *successful* placements for inefficiency...")
and before the "Rebuild manual fixes from the last known-good baseline"
bullet.

---

- **A turn-on-stand is a hard-stop condition, never a Finalize-documented
  finding.** An aircraft cannot deplane or board on a stand — a route with
  a turn sitting on a stand is not a minor inefficiency to note and revisit
  later; it is an invalid schedule. Discovered during construction or
  during any verification pass, it must be remedied in the same session it
  was found, before that batch of work is considered complete. Deferring
  it compounds the problem: every subsequent change is then built on top
  of an already-invalid gate assignment, and untangling which later
  decisions depended on the bad state gets harder with each added change,
  not easier.

  Two remediation paths, in order of preference:

  1. **Modify the problem route.** Retime the conflicting leg (a different
     departure, a shorter- or longer-block destination swap, or shifting
     an earlier leg in the same day to change when the touch lands), so
     the route's own gate-need moves clear of the saturated window. This
     is the default — most turns-on-stands are resolved this way, since
     the touch itself is usually movable even when the exact original
     time isn't feasible.

  2. **Convert an existing long hold into a deliberate ROD.** If a
     *different* route at the same city is currently holding a gate
     continuously for a long stretch it doesn't structurally need (see
     the waypoint-pattern bullet above), and that hold's middle portion
     overlaps the problem route's touch, split it: brief gate touch at
     each end, genuine ROD (remain overnight / out of duty, §1.6) on a
     stand for the bulk of the hold. This frees the gate the problem
     route actually needs. Only use this path when a genuine candidate
     exists — a long hold with real, structural gate need (e.g. it's
     already at the lowest achievable duration) is not a candidate; do
     not force a split that creates a new long-turn-duration finding
     (§1.6, the [TURN, 150min] audit range) just to relieve stand
     pressure elsewhere.

  If neither path resolves a specific instance after genuine investigation
  (checked: alternate destinations, front-end/back-end retiming slack,
  §2.6 room on the contested pair, and candidate long holds at the same
  city), the turn-on-stand still does not ship. The construction decision
  that created the conflict must itself be reconsidered — a different
  extension for the problem route entirely, a different destination that
  doesn't touch the saturated city at that time, or reverting the specific
  change that introduced the crunch and choosing a different approach from
  there. A turn-on-stand that resists both remediation paths is evidence
  the schedule needs a different decision upstream, not a residual to
  carry forward. If exhausting all of this still leaves the city's
  gate/stand allocation looking genuinely undersized for its traffic, that
  observation belongs in the Finalize discussion as a capacity-planning
  question for the *next* build's allocation — but the current build's
  turn-on-stand is resolved first, by changing the schedule, before that
  observation is ever recorded.
