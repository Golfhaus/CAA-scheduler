# Disconnect-resilient development

Long schedule builds must be recoverable from a fresh workspace without relying
on uncommitted files or a running process. Use the following workflow for solver
and schedule-package work.

## Durable iteration loop

1. Work on a task-specific branch created from the approved base commit.
2. Open a draft pull request after the first coherent, tested checkpoint.
3. Divide the work into independently reviewable behavior changes.
4. Run the smallest relevant regression set after each change.
5. Commit and push each passing checkpoint before starting the next change.
6. Record unfinished behavior and the next command in a version-controlled plan.
7. Run the complete Python and JavaScript suites before packaging a review build.
8. Keep generated review packages off the main branch until they are approved.

Checkpoint commits may be incomplete with respect to the overall milestone, but
they must be internally coherent: source, schemas, policy, tests, and explanatory
documentation for the behavior in that commit travel together.

## Long solver runs

Use the approval-gated commands in
[`staged_regeneration.md`](staged_regeneration.md) for candidate regeneration.

- Commit and push all solver inputs before starting a long run.
- Fingerprint every checkpoint from all behavior-affecting inputs.
- Save a checkpoint after each fleet and after each successful global-repair
  incumbent.
- Resume only when the checkpoint fingerprint matches the current inputs.
- Prefer bounded phases over one monolithic solve. A timeout must produce an
  explicit blocked artifact or resumable checkpoint, never an ambiguous absence.
- Write completed artifacts atomically so interruption cannot expose a partial
  JSON document as a completed result.
- Record the input commit, checkpoint fingerprint, solver phase, completed
  fleets, objective, and next command in the progress notes.

## Test cadence

The minimum cadence is:

1. focused unit tests for the edited module;
2. cross-stage regression tests for its direct consumers;
3. a candidate smoke build when the change crosses a construction boundary;
4. the full Python and JavaScript suites before a review package is pushed.

A test result from an uncommitted or lost workspace is historical information,
not verification of the recovered branch. Re-run it against the pushed commit.

## Pull-request discipline

- Never reuse, merge, or close an earlier review pull request for a new schedule
  version.
- Keep the implementation branch and pull request in draft state while solver or
  validation work remains.
- Push generated review artifacts only after all non-waivable hard stops pass.
- Do not merge a review package to the main branch without explicit approval.
