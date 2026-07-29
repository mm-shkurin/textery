# Story 19: AI chat editing of an existing document (SSE, revisions, rollback) — Progress

## Spec
- [x] interview
- [x] story
- [x] mockups
- [x] api-spec
- [x] test-spec

Scenario checklists live in the split per-layer files:
`progress-backend.md` (Backend + Integration + Security + Load + Infrastructure — 130
scenarios, bootstrapped 2026-07-29) and `progress-frontend.md` (Frontend — 35 scenarios
from `tests/02_UI_Tests*.md`, not bootstrapped yet; the frontend session creates it).

Counting the `###` scenario headings across the test spec gives **165** scenarios
(130 backend + 35 frontend), not the 156 `stories.md` carried from the test-spec phase;
the rollup is corrected to 0/165 with this commit.

## Decisions

- **Test files are split beyond the six category names.** API and UI each exceeded the
  200-line file limit, so they are split by concern: `01_API_Tests.md` → `_Lifecycle` /
  `_Apply`, `02_UI_Tests.md` → `_Streaming`. The hazard-scan guards are their own files
  (`01_API_Tests_Guards.md`, `_Guards2`, `02_UI_Tests_Guards.md`) rather than interleaved,
  so the scan's coverage stays auditable against the catalogue. Each split file names its
  predecessor and shares the first file's DSL table.
- **Hazard scan: all 8 catalogue groups, 45 GAPs, all folded, none dismissed.** One is
  folded as a forced decision rather than a plain test: revision-history growth
  (`04_Infrastructure_Tests.md` 4.8) is written so the project must either prune revisions
  or state explicitly that they are unbounded by design — each revision holds up to a full
  document, so leaving it unsaid is the one outcome not allowed.
- **Race scenarios carry a determinism rule.** The scan found every "submitted
  concurrently" scenario would pass against a non-conditional write most runs. The rule at
  the top of `01_API_Tests_Guards.md` binds all of them to a barrier at the read-write
  window plus a zero-rows-affected assertion.
- **Contract decisions forced by the review passes.** Four questions the spec had left
  implicit are now answered in the contracts, because a test cannot go red on an
  unstated policy: a manual `PUT /documents/{id}` during a live AI edit is ALLOWED (the
  edit loses its own CAS and refunds) rather than blocked, otherwise a hung edit locks a
  user out of their document for the whole deadline; the unknown-constant policy is
  stated once in `api-specs/README.md` (unrecognised STORED value = clean failure,
  unrecognised WIRE value = tolerated by the client); cursor semantics are pinned there
  too (empty = first page, invalid = 400, foreign = 404); the idempotency key is scoped
  to (account, document), not to the account alone.
- **The SSE stream needs a heartbeat, and that came out of the premortem.** A slow
  provider leaves the response byte-silent and any idle intermediary closes it — while
  the client's reconnect state is asserted to work, so the whole suite would have stayed
  green with every long edit looking broken. `KEEPALIVE_SECONDS < proxy idle timeout` is
  now a startup-validated ordering alongside the deadline orderings.
- **Cancel is cheap only if the worker re-checks before calling the provider.** Every
  cancellation assertion was about rows, so a worker that always calls the model passed
  them all while a third party billed for work nobody wanted — and the refund hid the
  spend from the quota counter.

## Status Summary (as of 2026-07-29)

Spec phase complete: interview, story, mockups, api-spec, test-spec all `[x]`. Nothing is
implemented — no backend, frontend, or migration code exists for this story yet.
`progress-backend.md` is bootstrapped (130 scenarios); the next backend work unit is
`red-acceptance` for Backend Scenario 1.1 (`01_API_Tests.md` — every endpoint refuses an
absent document indistinguishably from a foreign one). `progress-frontend.md` is still
unbootstrapped and belongs to the frontend session.

