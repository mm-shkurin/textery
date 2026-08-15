# Story 10: Editor pages (pagination, page setup, headers/footers) — Progress

Story-level narrative and the shared Spec checklist. Backend/Integration/Security/Load/
Infrastructure state lives in `progress-backend.md`; Frontend state in `progress-frontend.md`.

## Spec

- [x] interview
- [x] story
- [x] mockups
- [x] api-spec
- [x] test-spec

## Build order (decided at interview, 2026-08-01)

`page_settings` → editor pagination → page counter → manual page break → headers/footers.

Settings come first deliberately, even though the first user-visible result arrives later:
pagination written against hardcoded constants would be rewritten once settings land, and
every pagination test written against those constants would be rewritten with it. This is
why `progress-backend.md`'s first scenarios are contract work with nothing on screen.

## Decisions carried into implementation

- **Page equality between the editor and the PDF is NOT claimed.** The editor is laid out
  by the browser, the PDF by WeasyPrint — two engines, and their drift accumulates down the
  document. No test in this story may assert editor↔PDF page equality (known-debt #14). The
  divergence gets measured once pagination ships, and the engine decision follows the
  numbers rather than preceding them.
- **DOCX page equality is unreachable by any implementation** — Word repaginates on open.
  Breaks, headers and section geometry are carried; where a page *ends* is not asserted.
- **One bundled font (Liberation Serif), font choice deferred** (known-debt #15). The editor
  and the renderer must draw with the byte-identical file or the geometry diverges.
- **`page_settings` is a wholesale replace, not a per-key merge.** A supplied object omitting
  `header_text` clears that header. The panel must send the complete object; a naive partial
  send is a silent data-loss path that satisfies every other rule.
- **Settings ride the existing version CAS** (`save_content_if_version_matches`), not a new
  concurrency mechanism and not a separate endpoint.

## Hazard-scan record

- **Story spec:** scanned 2026-08-01 against groups **1–8** (the `_index.md` **Groups** list
  at scan time). 29 GAPs, all folded into acceptance criteria or dismissed with a reason —
  the full disposition table is in `10_EditorPages_Notes.md`.
- **Test spec:** the Phase-3 scan **was not run** — skipped at the user's direction
  (2026-08-01) on the grounds that the spec-level scan had already folded its findings into
  the scenarios. Recorded here rather than left silent: a skipped scan and a clean scan
  produce identical artifacts, and this one was skipped. If a scenario below turns out to
  need a guard the spec named but the tests never pinned, this is why.

## Orchestration lesson (2026-08-04)

`/refactor` and the two pre-commit review passes are documented as safe to run
concurrently because the passes read the *immutable behavior commit*. That is not what
they actually do: both `agent-review` and `premortem` verify their findings by **mutation
testing** — editing production files in the working tree, running the suite, and reverting.
During the `red-adapter rest (PUT)` unit that collided with `/refactor` mid-edit; `/refactor`
correctly detected a foreign process rewriting its files and stopped, and its in-flight work
was reverted by the other agent's `git checkout`. Only finding 1 survived (committed
separately as `0bfae4dd`).

**Run the review passes serially against `/refactor` in this repo**, or give them a
worktree. The mutation testing is worth keeping — it is what turned "the test passes" into
"the test fails when I break the thing it guards", and it caught two findings a read-only
pass would have missed.

## Refactor findings raised but not applied (2026-08-04)

Both were accepted on merit by `/refactor` and lost to the collision above:

- **A shared usecase-double factory.** `Mock()` + `AsyncMock` repeats ~25 times across
  `backend/adapters/rest/tests/router/document/`; only 4 sites use `create_autospec`. Every
  `execute.assert_awaited_once_with(...)` against a bare `Mock` checks the test's own spelling
  against itself — a free-form mock accepts any keyword, so a renamed argument satisfies the
  assertion and fails only in production wiring. `a_usecase(mocker, spec, returns=None)` in
  `document_router_fixtures.py` makes autospec structural instead of per-call discipline.
  Caveat for whoever does it: `test_document_router_auth_and_types.py:71` uses `Mock()` as a
  *token service*, not a usecase — that one must stay bare.
- **`test_document_list_router.py:11,21,48`** re-declares the `2026-07-17T12:00:00Z` literal and
  its matching `datetime` locally instead of importing `CREATED_AT` / `CREATED_AT_ON_THE_WIRE`.
  That module exists to keep the pair matched, and for this file the invariant is unenforced.
  Import the literal — do NOT derive it: `CREATED_AT.isoformat()` yields `+00:00`, pydantic emits
  `Z`, so a derived expectation is wrong rather than merely tautological.

## Notes for later scenarios

- Pagination is measured in a real browser. jsdom reports every element as zero-height, so
  unit tests can cover the settings value object and the break-decision logic given
  *supplied* heights — "does it break in the right place" only has meaning in Selenium.
- The page-break sanitizer allowlist entry collides with story 5's paste-sanitize scenario
  E5.1. Whichever lands first owns the change.
- Budgets in the spec's Validation Rules (≤ 2 s initial layout, ≤ 150 ms incremental,
  ≤ 200 code points per header) are first-pass numbers chosen to be assertable, not measured.
  Confirm them against a real max-size document when the first budget scenario runs.
