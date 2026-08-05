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

## This story cashes in another story's risk acceptance (2026-08-05)

Story 17 deferred its `clears`-at-the-real-CAS gap — `document_storage._update_values` asks only
`carries_a_value()`, so a `TitleUpdate.clear()` falls into the omit branch and the erasure no-ops,
while the fake (`document_fakes.py:169-173`) asks `erases()` first and honours it. The usecase test
`test_should_forward_a_clear_and_null_the_stored_title` therefore passes against a fake the real
adapter contradicts. The deferral was accepted on a stated premise: *not wire-reachable today,
because the route passes `request.title` as `str | None` and `clears` is never set.*

**`green-adapter rest` is the commit that expires that premise.** The moment the route constructs
`TitleUpdate.clear()`, the no-op becomes reachable from HTTP. Story 17 has the fix in flight
(`progress-backend.md:2825`, `red-adapter db … closes (b)`, at `[~]`) — this is a note about
ORDERING, not a second charter: if story 10's green lands first, the clear path is wire-reachable
and silently broken in the window between them. Nothing in either story's progress recorded the
dependency until now. Do not fix it here — it is story 17's file and another worktree's branch.

## Two title-shaped gaps the route change makes reachable (2026-08-05)

Both surfaced by the premortem pass over `08080394`, both verified, and neither fixable inside
this story's own files — recorded here rather than chartered as a 2.1 step.

**The title field has no length cap on the path a user controls.** `SaveDocumentRequestDto.title`
(`document_dtos.py:38`) is a bare `str | None` with no `max_length`; `TitleUpdate.__post_init__`
validates the contradiction and blankness but not length; `documents.title` is an unbounded
`String`; and `documents_save.yaml` declares no `title` property at all, so there is no `maxLength`
and no 400 row. The cap exists only on the path a user CANNOT influence —
`generated_title.py:8`, `MAX_GENERATED_TITLE_LENGTH = 120`, whose comment names this exact harm
("a title that long is not a title, it is the first paragraph, and it would push every history row
and every Content-Disposition header out of shape"). Probed with the correct green applied: a PUT
carrying a 50,000-character Cyrillic title returns **200 OK** and reaches the port as
`TitleUpdate.of(<50000 chars>)`. The export route's `quote(rendered.filename, safe="")`
(`document_router.py:157`) expands each Cyrillic character to 6 bytes, so that document's
`Content-Disposition` becomes ~300 KB — past a default 4 KB `proxy_buffer_size` at roughly 700
characters, and every export of that document then fails at the proxy on every retry. What makes it
unrecoverable rather than merely ugly is the risk already recorded above: the one wire shape that
would remove the title (`"title": null`) no-ops at the real CAS until story 17 closes it, and there
is no title editor in the frontend — so recovery is a database edit. Scenario 2.1 is page settings;
title length belongs with the 3.x validation scenarios or with story 17, and the owner should be
named before either ships.

**`documents_save.yaml` is silent on `title`, and its neighbour says the opposite.** The
three-state contract `08080394` pins lives only in a test docstring and in story 17's
`blank-title-semantics-decision.md`. The `SaveDocumentRequest` schema declares `content`, `version`
and `page_settings` — the asymmetry is stark inside that one file, since `page_settings` carries a
twelve-line tri-state description warning "do not collapse them" while `title`, now a four-shape
field one of whose shapes is destructive, carries nothing. Worse, `documents_from_generation.yaml:92`
lists `title` among the fields "the client cannot set through the body", so a reader of the specs
concludes the reverse of what this scenario establishes. The concrete cost is a frontend session in
its own worktree implementing "clear the title" the obvious way — send `""` — which after green is
`preserve()`: the clear button does nothing, forever, with the whole backend suite green. The fix
lives in `ProductSpecification/api-specs/`, outside this story's documentation boundary, so it is
recorded and not applied. Nothing pins `documents_save.yaml` against `SaveDocumentRequestDto`, and
no acceptance test drives blank-preserves / null-clears over real HTTP — every assertion in this
contract stops at an autospec mock.

**Correction (2026-08-06, agent-review on `3f676865`): the blank-preserves half of that last
sentence is false.** `acceptance/tests/backend/documents/test_export_document_acceptance.py:144`
(`test_blank_title_save_does_not_wipe_the_stored_title`) is parametrized over `""` and `"   "`,
drives a real HTTP PUT against a stored Cyrillic title, and asserts survival through the export
`Content-Disposition` header — by its own statements class the only black-box observation of the
stored title that exists. That guard was NOT run against this behavior change (the sweep was
`backend/` only — no Postgres, no live backend in this worktree), and the sentence above told the
next reader there was nothing to run. It should still pass by construction (blank → `preserve()` →
the storage omits the column) but that is reasoning, not a run; **verify it when a backend is up.**
This is the fourth unqualified absolute in this scenario falsified by the pass that checked it, and
it was written by the commit whose own notes say "Stop writing them."

The null-clears half IS true, and structurally so: `acceptance/clients/application/application_client.py:128-129`
builds the save payload as `{"content", "version"}` and adds `title` only `if title is not None`, so
the acceptance client **cannot express `"title": null` at all**. The one wire shape this scenario
exists to enable is unreachable end-to-end until that client learns an omit-vs-null distinction —
a change in `acceptance/`, outside this layer's file ownership, so it is recorded and not applied.

## Notes for later scenarios

- **The editor cannot read a title, so `null` is the only thing it can send back** (premortem
  CREDIBLE, 2026-08-06). `GetDocumentResponseDto` has no `title` field — deliberately, per its own
  docstring — and `frontend/.../documentApi.ts`'s `GetDocumentResult` mirrors that. A client that
  cannot read the title holds `null` for it, and the idiomatic `useState<string | null>(null)` +
  `JSON.stringify({content, version, title})` emits `"title": null` — which scenario 2.1 just made
  DESTRUCTIVE. The blank-fold safety net catches the other spelling only: `""`/`"   "` preserve, but
  a `string | null` field serialises to `null`, not `""`. Today the harm is masked because the db
  arm drops the clear; story 17's `green-adapter db` removes that mask, and then a user who opens a
  titled document, types one word and lets autosave fire loses the title. **Before the frontend
  phase sends `title` at all, decide the omit-vs-null rule and pin it** — either a frontend contract
  test asserting the key is ABSENT when the editor holds no title, or put `title` on the read model
  so the client has something to round-trip. Story 17 calls exposing it "what turns the ADR's
  conceded residual live"; the inverse is the actual risk — NOT exposing it is what makes `null`
  the client's only option.
- **Story 17 is queued to rebuild this same mapping in the router** (premortem CREDIBLE). Its
  `[ ] green-adapter rest` (`17-export-document/progress-backend.md:2853`) says "the route BUILDS
  the intent from `model_fields_set`", but `3f676865` moved that mapping onto
  `SaveDocumentRequestDto.title_update()`. Different files → git merges both cleanly, leaving two
  implementations with the DTO's orphaned, and no test can tell which one production runs (nothing
  calls `title_update()` directly). Story 17's planned RED has only two rows — absent and null, no
  blank — so if its copy wins, the blank-preserve fold silently stops being pinned against the code
  that actually executes. Both branches also queue the identical `SaveDocument.execute` `str`-arm
  deletion. Whichever lands second must reconcile, not re-add.
- Pagination is measured in a real browser. jsdom reports every element as zero-height, so
  unit tests can cover the settings value object and the break-decision logic given
  *supplied* heights — "does it break in the right place" only has meaning in Selenium.
- The page-break sanitizer allowlist entry collides with story 5's paste-sanitize scenario
  E5.1. Whichever lands first owns the change.
- Budgets in the spec's Validation Rules (≤ 2 s initial layout, ≤ 150 ms incremental,
  ≤ 200 code points per header) are first-pass numbers chosen to be assertable, not measured.
  Confirm them against a real max-size document when the first budget scenario runs.
