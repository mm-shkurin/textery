# Story 4: Auto-generate: реферат — Progress

Bootstrapped 2026-08-01 from `04_AutoGenerateReferat.md` + `tests/`. Three-file layout
from the start: this file holds the story-level narrative, decisions and the Spec
checklist; `progress-backend.md` owns Backend + Integration + Security + Load +
Infrastructure Scenarios; `progress-frontend.md` owns Frontend Scenarios.
`ProductSpecification/stories.md` is the cross-file rollup.

## Spec Phase

- [x] interview — `interview.md`
- [x] story — `04_AutoGenerateReferat.md` + `_Notes.md`, hazard-scanned against groups 1–8
- [S] mockups — the only visual change is the реферат card losing its "скоро"
  treatment; story 1's `02-type-modal` mockup already renders the four cards. No new
  screen, so no new mockup.
- [x] api-spec — no new endpoint. `generations_create.yaml` corrected: its
  `document_type` enum said `[доклад]` while the domain has accepted all four types
  since story 1 and `documents_create.yaml` already listed them. A client trusting that
  enum expected 422 for эссе and would have got 201.
- [x] test-spec — `tests/` (6 categories + extended), scan record in
  `tests/HAZARD_SCAN.md`

## Decisions Carried Into Implementation

From `interview.md`, settled before any code:

- The prompt template table lives in `backend/domain`, keyed by document type; the
  GigaChat adapter composes nothing.
- The доклад entry holds today's string verbatim. Story 1 is being finished in
  `textery-editor` and `textery-projects` against the current доклад output — perturbing
  it, even by whitespace, would redden their tests for a reason unrelated to their work.
- No список литературы is ever generated. A model asked for sources invents ISBNs the
  user cannot check.
- `volume_pages` stays `[1, 10]` for all types. No per-type range.
- The type card's `available` flag is UX. The server accepts all four types today, so
  эссе and сочинение stay reachable over the API until #2/#3 — deliberate, recorded as a
  passing security scenario so nobody "fixes" it with a gate those stories would remove.

## Open

- The реферат and доклад outputs must be distinguishable to a reader. Nothing in the
  automated suite can prove this — the stub returns a fixture regardless of the prompt.
  Judge one real generation by hand before calling the story done.

## Load / Infrastructure

Both `n/a`, with the reasoning written in `tests/03_Load_Tests.md` and
`tests/04_Infrastructure_Tests.md` rather than left as a blank column.
