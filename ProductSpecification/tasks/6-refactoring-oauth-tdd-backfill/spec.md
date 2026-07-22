# Task 6: Backfill TDD coverage for the OAuth sign-in slice (Story 16)

Type: refactoring

## Why

Story 16 (OAuth sign-in, VK ID + Yandex ID) was implemented under a **reduced-TDD** mode
ahead of a Friday demo: one commit per scenario instead of per-step red/green work units,
and the `/test-review`, `/test-coverage`, `/refactor`, `/agent-review`, `/premortem` and
formal `adapters-discovery` steps skipped. Every reduced scenario is marked
`[S] reduced-TDD <date>, backfill pending` in
`ProductSpecification/stories/16-oauth-signin/progress-backend.md`, and the narrative debt is
in that story's `carryover.md`.

This task restores the coverage the reduced mode skipped. Behavior must not change — the
backfilled tests characterize the code as it stands. Where a layer is already genuinely
covered, confirm it and move on rather than rewriting existing tests.

## Not in scope

The security invariant gate
(`acceptance/tests/backend/oauth/test_oauth_security_invariants.py`, I1–I8) was **not**
reduced and stayed green throughout. It is not backfill material; it is the baseline the
backfill must not break.

## Done when

- Every `[S] reduced-TDD` entry in `progress-backend.md` has a matching completed step here.
- Usecase, adapter (rest / db / oauth provider) and acceptance layers for the OAuth slice
  report no genuine coverage gap under `/test-coverage`.
- The deferred scenarios named in `progress-backend.md` ("Deferred to the weekend") are
  implemented with a real red-first cycle.
- VK is either carried end to end (credentials arrived) or explicitly recorded as
  unconfigured with its named error under test.
