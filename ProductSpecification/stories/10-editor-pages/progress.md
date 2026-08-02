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

## Notes for later scenarios

- Pagination is measured in a real browser. jsdom reports every element as zero-height, so
  unit tests can cover the settings value object and the break-decision logic given
  *supplied* heights — "does it break in the right place" only has meaning in Selenium.
- The page-break sanitizer allowlist entry collides with story 5's paste-sanitize scenario
  E5.1. Whichever lands first owns the change.
- Budgets in the spec's Validation Rules (≤ 2 s initial layout, ≤ 150 ms incremental,
  ≤ 200 code points per header) are first-pass numbers chosen to be assertable, not measured.
  Confirm them against a real max-size document when the first budget scenario runs.
