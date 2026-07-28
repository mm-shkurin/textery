# Story 19: AI chat editing of an existing document (SSE, revisions, rollback) — Progress

## Spec
- [x] interview
- [x] story
- [x] mockups
- [x] api-spec
- [x] test-spec

<!-- Scenario sections are bootstrapped from the test-spec on the next `/continue`.
     Backend/Integration/Security/Load/Infrastructure scenarios go to
     progress-backend.md; Frontend scenarios go to progress-frontend.md. -->

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
