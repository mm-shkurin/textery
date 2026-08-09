# Story 10 — Backend / Integration / Security / Load / Infrastructure Progress

Story-level narrative and decisions: `progress.md`. Frontend: `progress-frontend.md`.

Scenario ids map to `tests/01_API_Tests.md`, `06_Integration_Tests.md`,
`05_Security_Tests.md`, `03_Load_Tests.md`, `04_Infrastructure_Tests.md`.

## Backend Scenarios (01_API_Tests.md)

### Scenario 2.1: A never-configured document reads as unconfigured, not as the defaults
- [x] red-acceptance
- [x] design (see ADR `decisions/page-settings-read-tristate-decision.md`; hazard scan: groups 1–8,
  5 GAPs folded into the ADR's Edge Cases, group 8 dismissed as out of altitude)
- [x] red-usecase
- [x] green-usecase
- [x] adapters-discovery (ports: db — insufficient, no column and to_domain passes 11 kwargs;
  exceptions: [S], None → NotFoundException → 404 already mapped in document_router;
  response shape: rest — DocumentResponseDto has no page_settings and carries title/generation_id
  the frozen 8-key assertion rejects)
- [x] red-adapter db — the mapper seam. Three guards the review passes named:
  (a) a configured row seeded directly, `commit()` + `expire_identity_map()`, re-read through
  `find_by_id_and_owner`, asserting all nine keys by `==` against a separately built object — a
  to_domain that forgets the twelfth kwarg reads every configured document back as unconfigured
  and NOTHING currently fails, because reconstitute defaults it to None;
  (b) migration shape: `documents.page_settings` nullable, `server_default is None`, and applying
  it to a table with existing rows leaves them SQL NULL — a `server_default=text("'{}'::jsonb")`
  reflex backfills every legacy document irreversibly;
  (c) stored `{}` stays distinguishable from SQL NULL — `PageSettings(**blob) if blob else None`
  is the path of least resistance and `{}` is falsy, which is exactly the conflation the ADR forbids.
  Also refresh `document_storage_assertions.assert_stored_state` — its "six columns the CAS must
  NOT touch" docstring is stale at seven.
- [x] green-adapter db — JSONB NULL column + additive migration, no server default, no backfill
- [x] red-adapter rest — GetDocumentResponseDto, the eight keys of documents_get.yaml, wired to
  `GET /{document_id}` only; the shared DocumentResponseDto stays as-is for the three write-shaped
  routes whose own spec mandates title/generation_id. Two methods, both red: null-for-unconfigured
  AND the stored geometry — the second is what forbids hardcoding `page_settings: None` on the read.
  The rest adapter has no Statements layer (none of its five router tests do); assertions stay
  inline, per the sibling shape.
- [x] green-adapter rest — `GetDocumentResponseDto` + nested `PageSettingsDto`; exactly one
  decorator changed. GET/PUT sit on the same path literal 40 lines apart and from-generation
  shares the response model, so a replace-all would have silently narrowed a write route with
  the suite still green — all three write routes re-read by eye after the edit.
- [x] red-adapter rest (coverage: POST /from-generation response body unasserted) — no RED, and
  that is the honest outcome: the route was already correct, only the assertion was missing. Three
  tests, passing first run. The load-bearing one pins `title`/`generation_id` at NON-NULL values —
  the sibling manual-create test pins both at `None`, which a drop-and-redefault would survive.
- [S] green-adapter rest (coverage: POST /from-generation response body unasserted) — no
  implementation needed; the red half was a regression guard over already-correct code, and no
  production file changed.
- [x] red-adapter rest (coverage: PUT response asserts version only, not shape) — no RED; guard
  verified by mutation instead: flipping PUT's `response_model` to `GetDocumentResponseDto` (the
  plausible mis-edit — same `"/{document_id}"` literal, 40 lines apart) fails the new whole-body
  test. The old `["version"] == 2` survived that mutation, because `version` is on both DTOs.
- [S] green-adapter rest (coverage: PUT response asserts version only, not shape) — no
  implementation needed; regression guard over already-correct code, no production file changed.
- [x] red-adapter rest (premortem: PUT's title-erasure path is unreachable from HTTP. The route
  forwards `title=request.title` raw; `SaveDocumentRequestDto.title` is `str | None = None`, so an
  omitted title and an explicit wire `"title": null` both arrive as `None` and both map to
  `TitleUpdate.preserve()`. `SaveDocument`'s own docstring forbids exactly this, and
  `test_save_document_title.py` says the absent-vs-null split "is the rest adapter's
  (`model_fields_set`) and is covered by its own steps" — `grep -rn model_fields_set
  backend/adapters/rest/` returns NOTHING. `TitleUpdate.clear()` is constructed only by tests; no
  route can produce it. A user who clears a title keeps the old one in history and in the export
  filename, with green domain and usecase suites. This one is a REAL red, not a regression guard.
  Also: PUT has no `side_effect` test at all — a `NotFoundException` on the write path (deleted or
  foreign document, still-open editor tab) is unasserted, and autosave treats 500 as retryable.)
  RED landed 6 failing / 2 passing, split by which half it was: the title contract is genuinely red
  on all three arms, the PUT 404 was NOT — `not_found_exception_handler` is already registered
  (`main.py:155`), so that gap was a missing assertion, not a missing mapping. Both 404 tests ship
  unskipped as regression guards, with a negative control so a route that 404s unconditionally
  cannot satisfy them. **GREEN removes FOUR markers, not three:** three pre-existing tests in
  `test_save_document_router.py` assert the WHOLE `execute` call including `title=None` /
  `title="Новое имя"`, so they encode the contract GREEN deletes. They were restated in the new
  contract and skipped alongside — left alone they would have handed GREEN a suite it could only
  pass by editing tests, which is the rule that stops expectations being corrected to match the
  code. No assertion was loosened in the move. `/test-review` additionally expanded
  `test_should_return_200_with_the_stored_document`'s lone `["version"] == 2` into the full 9-key
  write body: the same version-is-on-both-DTOs hole this scenario's own PUT guard was raised for,
  still open one class below it.
- [x] red-adapter rest (agent-review: the FOURTH wire row is unpinned and the docstring argues it
  away on a false premise. `TestSaveDocumentTitleIntent` says blankness "could only pin a guard that
  cannot fire" because `TitleUpdate.__post_init__` folds a blank to preserve — but that invariant
  only fires on the `of()` path, and the route decides WHICH constructor is called. Mutation:
  spelling the null check `if not request.title` instead of `if request.title is None` routes
  `{"title": ""}` into `clear()`, where `__post_init__` never sees the value — 95 passed, 0 failed.
  A silent title wipe from the most ordinary frontend bug, and story 17's
  `blank-title-semantics-decision.md` has a FOUR-row wire table naming this exact failure as why it
  chose preserve. Parametrize over `""` AND `"   "`: whitespace is truthy, so it survives
  `not request.title` but not `not request.title.strip()`. This lands BEFORE green deliberately —
  green is written against this contract.)
  RED landed, prediction matched first run — and `/test-review` then falsified the parametrize
  rationale ABOVE, which is the second time in this scenario a convincing docstring turned out not
  to be true. `not request.title.strip()` catches `""` too (`"".strip()` is `""`, falsy), so BOTH
  named mis-spellings are caught by `""` alone and the stated reason for the second parameter was
  wrong. `"   "` still earns its place, for a different variant: `if request.title and not
  request.title.strip()` — the ADR's REJECTED "blank clears" reading, spelled with a `None` guard —
  lets falsy `""` fall through to `of("")`, which folds to preserve and passes. Only the whitespace
  case catches it. Verified against six route implementations with a throwaway unskipped probe,
  since the class is skip-marked and a suite run proves nothing about it.
- [x] green-adapter rest (premortem: title absent-vs-null via `model_fields_set`; PUT 404)
  Two constraints from agent-review, both checkable: (i) the rest suite must come back **97 passed,
  0 skipped** (restated from 95/0 — the blank row added two parametrized cases). Four marker SITES,
  not three: the class-level one in `test_save_document_title_router.py` plus three method-level
  ones in `test_save_document_router.py`. Nothing fails if green lifts only three — the guard is
  prose, so check the number. (ii) `document_router.py` is at 179 lines and the mapping adds ~8;
  under the 200 cap but with no room for the `_ERROR_CODE_STATUS_MAP`/log work chartered nearby.
  (iii) `if request.title is None` is the spelling the four rows were built to force — the blank arm
  exists to make that true. Stated as "the ONLY spelling" when it was written; agent-review
  falsified the absolute (`if not isinstance(request.title, str)` also passes 5/5). The practical
  claim stands — both mis-spellings the rows were aimed at are caught — but this is the THIRD
  unqualified absolute in this scenario to be falsified by the pass that checked it. Stop writing
  them.
  (iv) **premortem CREDIBLE — the four marker sites are spelled TWO ways, and the obvious grep finds
  only three.** `test_save_document_router.py:20` holds a shared `_RED_TITLE_INTENT` constant used
  at :69/:97/:134; the class-level marker at `test_save_document_title_router.py:8` is an inline
  literal sharing no token with it, rewritten fresh by this commit. `grep -rn _RED_TITLE_INTENT
  backend/adapters/rest/` returns exactly the three whose removal leaves the whole four-row contract
  dark. Proved: correct green applied, only the three greppable markers lifted → **92 passed, 5
  skipped, 0 failed** — a clean green with its own contract disabled. Lifting the fourth → 97 passed.
  Nothing fails; the count is the only guard, and this scenario's prose count has already been wrong
  once (95, corrected to 97 by this commit). Check the NUMBER, and prefer moving the class marker
  onto the shared constant so one grep enumerates all four.
  (v) **agent-review — green must forward `request.title` RAW; it must not trim.** `TitleUpdate.of(
  request.title.strip())` passes all four rows today (5/5 with the class unskipped; 646 passed
  across the backend), because the set arm sends `"Привет Мир"` — internal space only, so `.strip()`
  is the identity on it. `title_update.py`'s own `__post_init__` docstring names the rejected
  spelling by hand ("the rejected `value.strip() or None` would have trimmed every real title as a
  side effect"), and the padded guards that do exist — `test_title_update.py:112`/`:124` and
  `test_document_storage_title.py:95` — sit BELOW the route, so a route that trims before calling
  `of()` never presents the padding to any of them.
  (vi) Recording correction: this commit's message reports the unit sweep as 598 passed / 11 skipped.
  It does not reproduce — `pytest backend/` at `08080394` is **641 passed, 73 skipped** (62 db-adapter
  skips because no Postgres is up in this worktree, 3 rendering import guards, 8 rest RED markers).
  The 598/11 figure excluded `backend/adapters/db` entirely. The rest-suite number green is actually
  checked against (97/0) was verified and is correct; the sweep baseline beside it was not.
  GREEN landed on all six constraints. A module-level `_title_update(request) -> TitleUpdate` in
  `document_router.py` decides the three states — `"title" not in request.model_fields_set` →
  `preserve()`, `request.title is None` → `clear()`, else `of(request.title)` — and the PUT route
  passes its result. **97 passed, 0 skipped**, exactly; sweep 649 passed / 65 skipped, the delta
  from 641/73 being precisely the eight executions the four markers were hiding, with nothing else
  moving. All four marker sites lifted, and with them the `_RED_TITLE_INTENT` constant and two
  now-unused `import pytest` lines. No `.strip()`: probed directly, `" Отчёт "` reaches the port as
  `TitleUpdate(value=' Отчёт ', clears=False)` — padding byte for byte — and `null` is the only row
  producing `clears=True`.
  Coverage carries a warning worth more than its number. All three arcs of `_title_update` are
  covered, `BrPart 0`, branches 16/16 — but the parametrized blank pair traverses the SAME arc as
  the set test (`is None` false → `of()`), so branch coverage would read 16/16 without it. Coverage
  is NOT the guard on how line 177 is spelled; the two blank rows are the whole guard. Anyone
  deleting them as "redundant by coverage" re-opens the `if not request.title` silent wipe with a
  green suite and a green coverage report.
  Constraint (ii) cashed at the behavior commit: `document_router.py` hit **196 lines**, four under
  the cap, and the `_ERROR_CODE_STATUS_MAP`/log work chartered nearby no longer fit.
  **Superseded by the refactor commit `3f676865` — the router is back to 179 and that work fits
  again.** `/refactor` found feature envy (`_title_update` read `request.model_fields_set` and
  `request.title`, nothing of its own) and moved the mapping onto
  `SaveDocumentRequestDto.title_update()`, which is what `coding-detail.md:39`/`:57` prescribe
  ("Request DTOs own their conversions"; "convert DTO via conversion method"). Three arms and the
  docstring moved verbatim, `request.` → `self.` the only body edit; net −1 line across both files;
  no test touched. Re-verified after the move, since the suite cannot see it: `" Отчёт "` returns
  `TitleUpdate(value=' Отчёт ', clears=False)`, equal to the input at length 7, and `null` is still
  the only row with `clears=True`. 97/0 rest, 649/65 sweep — identical to `80dadf62`.
  The two review passes ran against the refactored HEAD and both returned CONCERNS. Their findings
  are chartered below; the four heaviest, in severity order:
  (a) **"Store verbatim" is pinned by nothing.** agent-review mutated the set line and ran the FULL
  suite per mutant: `.strip()`, `.strip() or ""`, `[:120]`, `html.escape`, NFKC and whitespace-collapse
  each returned **649 passed**; only an `.upper()` control went red. The set arm's `"Привет Мир"` has
  internal space only, so every value-rewriting transform is the identity on it.
  (b) **`model_fields_set` is not serialization-stable, and the flip runs the wrong way.** Proved on
  the shipped DTO: `D(content='c', version=1)` → `preserve()`, but
  `D.model_validate(that.model_dump())` → **`clear()`** — because `model_dump()` emits an explicit
  `title: None`. `model_copy()` is safe; `model_dump(exclude_unset=True)` is safe. Nothing in the repo
  round-trips it today (grepped), so this is a missing guard, not a live bug — but the absent row is
  "the shape almost every save in the app has", and it degrades toward erasure, not toward preserve.
  Passing the declared default explicitly (`title=None`) also inverts the meaning of omitting it.
  (c) **The clear path has no observability and no undo.** `logger.` appears zero times across the
  document router, storage and usecase; there is no revision/audit table, and `_update_values`
  overwrites `title` in place. A wipe would be unreportable, uncountable and unrecoverable.
  (d) **`title_update()` has one production caller and zero direct test callers** — every assertion
  reaches it through HTTP against an autospec'd mock. That is what makes (a), (b) and the story-17
  collision below all invisible at once.
- [x] red-adapter rest — landed GREEN on arrival, and that is the finding, not a formality. The
  hostile arm `" <Отчёт>  №ﬁ1  "` passes against HEAD because `80dadf62`/`3f676865` already forward
  the title verbatim through `SaveDocumentRequestDto.title_update()`; the defect was never in the
  production code, it was that nothing pinned it. Evidence the row is now real — the set line
  `return TitleUpdate.of(self.title)` (`document_dtos.py:59`) was mutated one at a time, DTO restored
  after each: `.strip()` **killed**, `html.escape(...)` **killed**, `unicodedata.normalize("NFKC", ...)`
  **killed**, `" ".join(self.title.split())` **killed**, `[:120]` **survives** (expected and
  in-charter — truncation escapes any arm shorter than a plausible cap; length stays with the cap gap
  in `progress.md`). Four of the five mutants that survived `"Привет Мир"` now die. Docstring rewritten
  against HEAD across all three stale claims: the mapping's move off the route onto the DTO,
  `TitleUpdate.clear()` now being HTTP-reachable (with the still-open db-arm caveat kept separate so
  the consequence clause cannot be half-confirmed), and the corrected collapse — Pydantic collapses
  rows **1 and 3** (absent, null), while blank differs by VALUE, not by `model_fields_set`.
  `/test-review` returned **0 violations, 0 edits** across clusters A/P/S (Se not applicable): the
  single module-level `_HOSTILE_TITLE` used as both payload and expectation is the correct spelling —
  two copy-pasted strings differing by one space would still pass a `.strip()` mutant. Se-cluster
  note for later readers: this directory has **no `Statements` classes** anywhere under
  `backend/adapters/rest/tests/`; the DSL split is `conftest.py` (infrastructure) +
  `document_router_fixtures.py` (given-phase builders) + inline assertions, which is what the
  python-fastapi-hex binding prescribes — the Java "zero assertions in the test class" rule does not
  read against this stack. File at 197/200 lines. 97/0 rest.
  (original charter: the set arm cannot catch a route that trims, and the class
  docstring claims it can. `test_should_map_a_wire_title_to_a_set_intent` sends `"Привет Мир"` —
  no leading or trailing space — so every value-rewriting transform is the identity on it:
  `of(request.title.strip())`, `of(request.title.strip() or "")` (the spelling `title_update.py`
  rejects BY NAME) and `of(unicodedata.normalize("NFKC", ...))` each pass 5/5. Meanwhile lines
  109-111, added by `08080394`, assert the opposite in prose: "Blankness is TESTED, never applied:
  the ADR forbids trimming, so a legitimate `" Отчёт "` is a set intent carrying its padding byte
  for byte." Nothing in this file pins that. Fix: parametrize the set arm over `"Привет Мир"` AND
  `" Отчёт "`, expecting `TitleUpdate.of(" Отчёт ")` exactly — that is what the ADR's row 4
  "store verbatim" actually costs. Length is NOT this row's business; see the cap gap in
  `progress.md`.
  While in this class, correct the docstring defect the same pass found: lines 25-27 still say
  "Pydantic collapses the first two to `None`", which was true when the table had three rows and
  became false the moment this commit inserted blank as row 2. Measured against
  `SaveDocumentRequestDto`: absent → `title=None`, `fields_set` without `title`; `""` → `title=''`;
  `"   "` → `title='   '`; null → `title=None` WITH `title` in `fields_set`. Pydantic collapses
  rows 1 and 3, not 1 and 2, and `model_fields_set` is therefore not "the only place" absent and
  blank are distinguishable — they differ by VALUE. Read literally the sentence tells green that
  `""` arrives as `None`, i.e. that the blank case is already covered by the absent branch, which
  is the exact wrong green row 2 exists to forbid. This is the same defect class the commit was
  written to correct, reintroduced by the correction.
  **RESCOPED 2026-08-06 by the agent-review pass on `3f676865` — `" Отчёт "` is NOT enough.** That
  arm was measured against six mutants of the set line, whole suite per mutant: it catches `.strip()`
  and whitespace-collapse, and **`[:120]`, `html.escape` and NFKC still pass at 650**. One adversarial
  arm catches four of the five: `" <Отчёт>  №ﬁ1  "` — padding, escapable chars, a compatibility
  ligature (`ﬁ`, which NFKC expands to `fi`) and a double space, expecting
  `TitleUpdate.of(" <Отчёт>  №ﬁ1  ")` byte for byte. Truncation still escapes any arm shorter than a
  plausible cap, and length is deliberately not this row's business — it stays with the cap gap in
  `progress.md`. Use the hostile arm, not the polite one.
  Docstring scope widens too: it is not only lines 25-27. Lines 22-29 now describe the PRE-green
  route — "The route forwards `title=request.title` raw today", and "`TitleUpdate.clear()` is today
  constructed only by tests — no HTTP request can produce it". Both were made false by `80dadf62`,
  and the second is the more dangerous kind of stale: its CONSEQUENCE clause still reads as true for
  an unrelated downstream reason (the db arm drops the clear — see `progress.md:83-96`), so a reader
  who half-checks it confirms the wrong story. The mapping also no longer lives in the route at all;
  it is `SaveDocumentRequestDto.title_update()`. Rewrite the whole block against HEAD.)
- [S] green-adapter rest (agent-review: the hostile set arm — forward the title byte for byte)
  SKIPPED: the set line already forwards verbatim on HEAD; the red row above was a coverage guard,
  not a behavior gap, proven by four killed mutants. A green step here would be a no-op commit.
- [x] red-adapter rest (premortem CREDIBLE: `model_fields_set` describes how the DTO was BUILT, not
  what the client sent, and the failure runs toward erasure. Proved against the shipped DTO:
  `d = SaveDocumentRequestDto(content='c', version=1)` → `preserve()`, but
  `SaveDocumentRequestDto.model_validate(d.model_dump())` → **`clear()`**, because `model_dump()`
  emits an explicit `title: None`. `model_dump(exclude_unset=True)` and `model_copy()` both survive.
  The same trap fires in plain construction: passing the field's own declared default
  (`title=None`) means CLEAR, while omitting the kwarg means PRESERVE — so the safest-looking
  spelling is the destructive one. Nothing round-trips this DTO today (grepped across `backend/`,
  `acceptance/`, `frontend/`), so this is a guard gap rather than a live bug; the incident is the
  day someone adds a save queue, an offline outbox, a request replay or a BFF hop and every
  content-only autosave in the app silently becomes a title erasure with the suite still green.
  Test: `SaveDocumentRequestDto.model_validate(d.model_dump()).title_update() == d.title_update()`
  for the absent row. It fails today — that is the point. Note this is the FIRST test to call
  `title_update()` directly; every existing assertion reaches it through HTTP against an autospec'd
  mock, which is precisely why the mutants in (a) survive. The docstring at `document_dtos.py:47-53`
  explains `model_fields_set` at length and never warns it is not serialization-stable — fix that
  in the same pass.)
- [x] red-adapter rest (both review passes on `21dc66f4`, converging: the shipped round-trip guard
  pins the Python-dict leg only, and every incident its own docstring names is a JSON one. Measured
  at HEAD: `model_validate_json(d.model_dump_json()).title_update()` → `clear()` — broken
  identically, pinned by nothing. The two legs are separably fixable, so the shipped red does not
  force green to pick the covering fix — this row exists to remove that freedom before green runs.
  Two assertions, NEITHER derived from `model_dump()`:
  (a) `model_validate({"content": "<p>saved</p>", "version": 1}).title_update() == TitleUpdate.preserve()`
  — a LITERAL dict with no `title` key, unsatisfiable by any serializer change;
  (b) `model_validate_json(request.model_dump_json()).title_update() == TitleUpdate.preserve()` — the
  JSON leg, which in Pydantic v2 bypasses the Python `model_dump` method entirely and goes to the
  Rust serializer. Cheap: the file is at 67/200.
  **LANDED, and the row's premise was half wrong — only (b) is red.** Measured at HEAD before
  writing: `model_validate({"content": ..., "version": 1}).title_update()` → `preserve()` ALREADY.
  A literal body with no `title` key never puts `title` into `model_fields_set`, so (a) passes
  today; the row read as two reds and there was one. (a) therefore landed in its OWN class,
  `TestSaveDocumentRequestDtoFromALiteralBody`, **unskipped** — parking a passing guard behind the
  class-level RED marker would make it inert for the whole red period, which is the exact defect
  the green row below already calls out in capitals about that marker. Unskipped it does its real
  job now: unsatisfiable by any writer-side green, and it forecloses the over-correcting green that
  makes absent mean CLEAR in both directions. It is a characterization guard landed in a red commit,
  not a red, and the split is structurally forced anyway — the skip marker is class-level, so a
  passing guard and a failing red cannot share a class without one being mis-marked.
  (b) joined `TestSaveDocumentRequestDtoRoundTrip` under the widened skip reason. Confirmed the
  Rust serializer emits `"title":null` exactly as the Python `model_dump` does — which is WHY the
  JSON leg breaks identically, and why a writer-side green aimed at `model_dump` would have left it
  broken. That freedom is now gone. File at 149/200.
  **THAT LAST SENTENCE IS FALSE — both review passes on `378e92a8` measured it so, independently,
  on pydantic 2.13.4.** `model_dump_json()` bypassing the Python `model_dump` METHOD does not
  foreclose a writer-side green, because `@model_serializer` is not a method override — it is
  compiled into the core schema and the Rust serializer honours it on BOTH legs. A
  `@model_serializer(mode="wrap")` that pops `title` when it is absent from `model_fields_set`,
  with `title_update()` left completely untouched, produces:
  `dump {'content':..., 'version':1}` / `dump_json {"content":...,"version":1}` / dict leg
  `preserve` / JSON leg `preserve` / literal `preserve` / explicit null `clear`. All three tests in
  the file go green AND `test_save_document_title_router.py:135` still passes. The commit removed
  one writer-side escape (overriding `model_dump`) and left the standard one open. Net constraint
  added over `21dc66f4`: one more instance of the same writer-satisfiable red, not a new class of
  red. Keep the tests — they are correct as characterizations — but do not read the charter as
  enforced. It is enforced by nothing.)
- [x] red-adapter rest (the charter repair, chartered by both review passes on `378e92a8`.
  Two things must change before green runs, and the second is the one that actually bites.
  **(1) The `title is None` assertions forbid the only real reader-side fix.** They were added by
  `378e92a8`'s own `/test-review` pass, defended on round-trip-faithfulness grounds, and nobody
  noticed they pin a REPRESENTATION green needs to be free to change. The standard pydantic answer
  to absent-vs-null is a sentinel default — `title: str | None | _Absent = ABSENT` — and it is
  production-viable here precisely because `document_router.py:174` forwards only
  `request.title_update()` and never reads `request.title`, so the sentinel stays inside the DTO.
  Measured: under the sentinel, `title is None` is **False**, so the reader-side fix fails three
  assertions while the writer-side fix passes all of them. The commit inverted its own charter.
  Restate those three as intent (`title_update()`) or as "does not reparse as a `str`" — do not
  simply delete them, the round-trip-fidelity concern that motivated them is real.
  **(2) Nothing pins the reader against input the DTO did not itself produce.** Every red in the
  file round-trips through this DTO's own serializer, which is exactly why a serializer patch
  satisfies them. Note the honest difficulty, discovered here: absent-vs-null IS key presence, and
  `model_fields_set` IS key presence, so there is no reader-side fix that keeps the current field
  representation — the sentinel changes the representation, which is why (1) blocks it and why (1)
  must be fixed FIRST. A red that a serializer cannot satisfy has to feed `model_validate` a
  hand-written body from a foreign producer, not a `model_dump()` output.
  **Worth stating plainly before green: this DTO is never serialized in production.**
  `SaveDocumentRequestDto` appears at exactly one site — `document_router.py:168`, a FastAPI inbound
  body — and there are ZERO `model_dump`/`model_dump_json` call sites anywhere in
  `backend/adapters/rest/src/`. FastAPI parses bodies, it never serializes them. The save queue,
  offline outbox, request replay and BFF hop the docstrings name exist nowhere in this repo. So the
  cheapest green is a serializer that is dead on arrival: suite green, `title_update()` unchanged,
  and the team records the erasure as protected. That is the incident.
  **CROSS-LAYER — the erasure that reaches a real user is in the FRONTEND, and this session does not
  own that file.** The actual producer of the save body is
  `frontend/src/features/generation/api/documentApi.ts` — `saveDocument(documentId, content, version)`
  / `putDocument` — which sends no `title` key at all, which is the only reason the reader is correct
  today. When the frontend scenario wires title into that call, the idiomatic TS spelling
  `title: title ?? null` serializes `"title": null` and routes every title-untouched autosave into
  `TitleUpdate.clear()`: silent data loss, user-visible, no error. No frontend test asserts the PUT
  body OMITS the `title` key when the title is untouched. The nearest thing is
  `documentApi.conflict.test.ts:62` — a strict `toEqual({content, version})` that would catch it
  incidentally today, but it is a conflict-retry test and will be rewritten to include `title` the
  moment that scenario lands. Hand this to the frontend session; it belongs in
  `progress-frontend.md`, which the file-ownership rule forbids this session from editing.
  **LANDED — and job (2) came back impossible, which is the finding.** (1) is done: the three
  `title is None` assertions now read `not isinstance(x.title, str)`, verified to hold under HEAD's
  field shape AND under a sentinel default, while still failing if `title` reparses as a `str`.
  (2) has no answer. Fed a hand-written body from a foreign producer, HEAD's reader is ALREADY
  CORRECT on every row of story 17's wire table — measured twice, independently, by red and by
  test-review: `{content,version}` → preserve, `{"title":null}` → clear, `""` → preserve,
  `"   "` → preserve, `" Отчёт "` → `of(" Отчёт ")` verbatim, `model_construct` → preserve.
  test-review additionally probed four paths where key-presence and `model_fields_set` might come
  apart (`model_copy(update=...)` both ways, post-construction `d.title = None`,
  `model_dump(exclude_unset=True)` reparsed) and found no divergence. For a body nobody serialized,
  "was the key there" is the ONLY information carried, and `model_fields_set` is exactly that
  information. A reader-side red needs the reader to be wrong about some input; there is no such
  input. **The defect is writer-side only.** Accept that rather than manufacture a red that pins
  the wrong thing.
  What landed instead is a NOT-SELF-REFERENTIAL guard, new file
  `test_save_document_request_dto_wire_shape.py` (115/200; split because 158 + ~110 blows the cap).
  The round-trip class proves self-consistency, and self-consistency is satisfiable by a PRIVATE
  ENCODING — built and measured: a `@model_serializer` emitting `title: "\x00__ABSENT__"` plus an
  `after` validator discarding the marker turns all three round-trip assertions green,
  `reparsed.title is None` included, while the emitted body carries that marker on the wire and
  HEAD's own reader parses it back as `TitleUpdate.of('\x00__ABSENT__')` — the user's title
  overwritten with a control character. The wire-shape class asserts the BODY, not the loop, so it
  closes that hole. Whole-body equality, not `"title" not in body`: membership passes a body that
  grew a spurious key, and which keys the body carries is the entire subject.
  The negative control (explicit null must KEEP the key) lives in its own UNSKIPPED class — it
  passes at HEAD, and behind the class-level marker it would guard nothing for the whole red
  period, which is the same defect this scenario already named once and acted on for
  `TestSaveDocumentRequestDtoFromALiteralBody`. Without it, a green that drops `title`
  unconditionally passes both reds and destroys deliberate erasure.
  `ruff format --check` was left alone: it already fails on three files at HEAD, two untouched
  here, so it is not an enforced gate, and the flagged line is byte-identical to HEAD.)
- [x] red-adapter rest (both review passes on `4923d835`, each having BUILT AND RUN the hostile
  green independently: the wire-shape file pins two of story 17's four wire rows — absent and
  explicit null — and never pins what the DTO writes for a REAL title. Across both test files every
  `model_dump`/`model_dump_json` call is on an absent-title or null-title request; all eight of
  them, grepped. So the row carrying actual user data is unpinned on the writer side, and the
  green's whole job is to add a serializer to this very model — which is the natural place for
  someone to "tidy" the title on the way out. Measured:

      @model_serializer(mode="wrap")
      def _s(self, handler):
          d = handler(self)
          if "title" not in self.model_fields_set:
              d.pop("title", None)
          elif isinstance(d.get("title"), str):
              d["title"] = d["title"].strip()
          return d

  passes EVERYTHING — both reds, the negative control, both round-trip tests, the live literal-body
  test — while emitting `" Отчёт "` as `"Отчёт"`. That violates the DTO's own docstring at
  `document_dtos.py:60` ("and no `.strip()` — `" Отчёт "` keeps its padding") and story 17's wire
  table, which the new file quotes TWICE in its own docstring while not enforcing it.
  **(a) Pin the real-title row**, both legs:
  `SaveDocumentRequestDto(content="<p>saved</p>", version=1, title=" Отчёт ").model_dump()`
  == `{"content": "<p>saved</p>", "title": " Отчёт ", "version": 1}`, and the `model_dump_json`
  leg for the same Rust-vs-Python reason the file already argues for the absent row. Goes in the
  UNSKIPPED negative-control class — it passes at HEAD, and behind the class-level marker it would
  be dark exactly during the red period, which is when the green that breaks it gets written.
  **(b) Whole-body equality against a frozen literal is asymmetric under extension.** It was chosen
  to catch a SPURIOUS key and it does, but it cannot catch a DROPPED declared one: when a later
  scenario adds a field to `SaveDocumentRequestDto`, a green whose serializer hand-builds its dict
  (a non-`wrap` `@model_serializer` returning `{"content":..., "version":...}`) silently omits the
  new field and `body == {...}` still holds. The live negative control has the same hole. One line
  that grows with the model instead of freezing: assert the dumped keys against
  `SaveDocumentRequestDto.model_fields` — every field in `model_fields_set` must appear in the body,
  and no key outside `model_fields`. Lower severity than (a): the natural `mode="wrap"` green is
  immune. Still one line, and this file is the only place it fits.
  **(c) Split the negative control's two legs into separate methods.** It asserts the dict body and
  the JSON body in one method, so a dict-leg regression means the JSON assertion never runs and the
  report names one broken leg where two may be broken. The RED class next door splits its legs on
  exactly the stated grounds that they are separably breakable; the fence contradicts its own
  neighbour's reasoning for no reason.
  Measured and rated REMOTE, recorded so green does not re-litigate them: the sentinel default
  leaves the published PUT contract unchanged (`model_json_schema()` emits only a
  `PydanticJsonSchemaWarning`, still a clean `anyOf: [string, null]`); the sentinel DOES make
  `model_dump_json()` raise `PydanticSerializationError: Unable to serialize unknown type: _Absent`,
  but no production path dumps this model (`document_router.py:177` forwards only
  `title_update()`, and the error handlers serialize Starlette's `Request`, not the DTO) and the
  wire-shape JSON test catches it at green time regardless; and the strip-green's damage to the
  `"   "` row is absorbed by the domain's blank fold.
  **LANDED — no new failing test, and that is the correct outcome.** All three jobs are fences over
  already-correct code; the defect they close is that nothing pinned it. Manufacturing a red would
  have meant asserting something false. rest went 99 → 102 passed, 4 skipped.
  Each fence measured against the green it forbids: the strip-green produces `2 failed, 100 passed,
  4 skipped` and the ONLY two failures are the new row-4 methods — every other test in the suite,
  both REDs and both round-trip tests included, passes under it. The key-tracking helper is honest
  about its own weakness: on the CURRENT model the frozen literal already catches the hand-built
  dict, so the helper adds nothing today; its window is strictly under extension, measured with an
  added field (`frozen equality holds: True` while `key-tracking fires, missing: ['note']`). Its
  docstring now says so, and says the sharper thing test-review named — reading `model_fields_set`
  / `model_fields` off the object under test is the SAME self-agreement structure the RED class
  spends 40 lines rejecting, re-imported on the key axis. It is a weaker pin that covers what the
  literals cannot, not a better one.
  `_HOSTILE_TITLE` was introduced as a module constant and removed again: row 4's whole subject is
  the PADDING, and a reader at the assertion site could not see there was any. Every expected value
  in these files is inline for that reason.
  **The pair was split across two files** — `test_save_document_request_dto_wire_shape.py` (87, the
  two REDs) and `..._wire_shape_control.py` (130, the live fence class + the helper). test-review
  argued against splitting at 198/200 on the real ground that the fence is only legible beside the
  RED it fences. What settled it: the file hit exactly 200 and then could not absorb a four-line
  docstring correction. A file at the cap cannot take a clarifying line, and both halves are still
  growing a row at a time as story 17's wire table gets pinned. They share only the import. The
  cross-references now name the sibling file explicitly so the pair still reads as a pair.
  **Environment correction — the journey-summary quirk is WRONG and should be struck.** Postgres IS
  running in this worktree: `pytest adapters/db/` gives 62 passed, 0 skipped, and the full backend
  sweep is **734 passed, 6 skipped**, not the 649/65 recorded earlier. Any figure in this file
  measured under the old assumption was scope-narrowed for a reason that no longer holds.
  **And 6 skips is not 4 RED markers.** The other two are silent env-skips from missing optional
  dependencies, in a module nobody has been watching:
  `adapters/rendering/tests/rendering/test_html_docx_renderer.py:14` (`could not import 'htmldocx'`)
  and `test_weasyprint_pdf_renderer.py:8` (`could not import 'weasyprint'`). The DOCX and PDF
  renderers are currently untested here, and every "full suite green" claim has been carrying that.
  Per the zero-tolerance rule in `tdd-rules.md` this needs a decision — install both deps so they
  run, or record an explicit `[S]` with justification. Not this work unit's to make.)
- [x] red-adapter rest (both review passes on `7e0ecd65`, converging on two and splitting on a
  third — the split is itself informative, so all four are recorded with their rating.
  **(a) CREDIBLE, and rated the most severe of the set: the blank-title rows are unpinned on the
  writer side.** Across the whole pair, `title` is only ever constructed as absent, `None`, or
  `" Отчёт "`. Nothing constructs `title=""` or `title="   "` — those strings appear only inside
  the RED class's prose table at `..._wire_shape.py:46-47`. Row 4 pins that a NON-BLANK title
  survives; a serializer that rewrites only blank titles is the identity on all four fenced rows
  and passes the entire suite. The damaging spelling is the most natural line a developer writes:
  `if not v.strip(): return None`. On the wire that is `"title": null`, and HEAD's reader maps null
  to `TitleUpdate.clear()` — so a documented PRESERVE silently becomes an ERASURE. This is the same
  class of harm row 4 was added to prevent, one row over, on the rows whose blank-vs-null
  distinction is the load-bearing one. Note the earlier "absorbed by the domain's blank fold"
  dismissal does NOT cover this: that was reader-side reasoning applied to a writer-side gap, and
  it does not hold in the blank→null direction. Four methods, matching the file's leg split:
  `""` and `"   "`, each on the dict and JSON legs, asserted verbatim.
  **(b) CREDIBLE, reproduced independently by both passes: the key-tracking helper is silent in the
  exact window its 23-line docstring claims as its only reason to exist.**
  `..._control.py:33` computes `missing = request.model_fields_set - body.keys()` — `model_fields_set`,
  not the `declared` set the line above it already builds. All four call sites construct only
  `content`/`version`/`title`, so a DEFAULTED added field is never in `model_fields_set`:

      declared:    {'content','version','note','title'}
      fields_set:  {'content','version','title'}     # 'note' defaulted, never set
      missing per helper: set()                      # silent, while the serializer drops it

  The measurement recorded in `7e0ecd65` (`key-tracking fires, missing: ['note']`) only reproduces
  from a call site that explicitly PASSES the new field, and no such call site exists or is likely
  to. So the helper adds nothing today (which its docstring concedes) and nothing in the window it
  was added for (which its docstring denies) — and that is worse than being absent, because the
  docstring is an assurance the next reader will trust instead of looking. Fix: the `missing` leg
  reads `declared - body.keys()`, with an explicit exclusion set for fields intentionally kept off
  the wire, plus one test constructing EVERY declared field so the fence has something to drop.
  **(c) CREDIBLE, premortem only — the symmetric hole on `content`, closed for `title` by the very
  reasoning that left this open.** `content` is the largest user-data surface on this DTO, and in
  all eleven constructions across the pair and the round-trip file it is `"<p>saved</p>"` or `'c'`:
  ASCII, single-line, no leading or trailing whitespace, nothing non-BMP. A `mode="wrap"` serializer
  normalizing whitespace on `content` only — the exact shape measured against for `title` — is the
  identity on every asserted content value and ships green. One row with
  `content="  <p>a</p>\n\n  "` or a non-ASCII multiline body, both legs, byte for byte.
  **(d) REMOTE, and the passes disagreed: the split's cross-reference is one-directional.**
  agent-review raised it; premortem downgraded it, and premortem is right — both files load in the
  same pytest session and a green that over-satisfies the RED goes red in the control class in the
  same run regardless of what the RED file says. Cost is a confused reader, not a shipped fault.
  Still worth the one comment line at the foot of `..._wire_shape.py`, since the split was argued
  on legibility grounds and currently only half-delivers it.
  **STEP INCOMPLETE — STAYS `[~]`. Resume here.** red-agent finished all four jobs and its output
  is COMMITTED with this note. `/test-review` was dispatched over it and **died mid-run on a
  session limit**, having reached the point of checking `ruff format --check`. `/refactor` and the
  two review passes never ran at all. Do NOT mark this `[x]` and do NOT advance to green: the
  work unit's gates are unrun, not passed.
  RESUME BY: re-dispatching `/test-review` over the four files below with the five judgment
  questions listed further down, then `/refactor` + `agent-review` + `premortem` over the commit,
  then the advance. The tests themselves are green and the tree is clean — nothing is half-edited.
  WHAT LANDED (rest 102 → **109 passed, 4 skipped**; full backend was 734 → 741/6):
  - `wire_shape_key_fence.py` (66, NEW) — the key assertion moved out of the control file with the
    corrected leg, `declared - body.keys()` instead of `model_fields_set - body.keys()`. Signature
    changed `(request, body, leg)` → `(body, leg)`; `request` is no longer needed once the leg
    stops reading `model_fields_set`. Carries an empty `FIELDS_KEPT_OFF_THE_WIRE` frozenset.
  - `..._wire_shape_blank_control.py` (91, NEW) — job (a), four blank-title methods.
  - `..._wire_shape_control.py` (178) — helper removed, every-declared-field row and the two
    hostile-`content` rows added.
  - `..._wire_shape.py` (93) — job (d), the footer comment naming both live siblings.
  EACH FENCE MEASURED AGAINST THE GREEN IT FORBIDS, in-suite against real `document_dtos.py`, then
  reverted — and the first number is the one that matters:
  - blank-normalizing `field_serializer("title")` (`if v is not None and not v.strip(): return None`):
    **102 passed, 0 failed at HEAD BEFORE this unit** — the preserve-becomes-erasure green shipped
    entirely green. After: `4 failed, 105 passed`, and the four are exactly the new blank methods.
  - `field_serializer("content")` doing `" ".join(v.split())`: 102/0 before; after `2 failed,
    107 passed`, exactly the two hostile-content legs.
  - the corrected key leg catches a dropped defaulted `note` (1 failed) where the old
    `model_fields_set` leg was silent (1 passed) — the defect agent-review and premortem both
    reproduced.
  DECISIONS red-agent made that the unrun review still owes a verdict on — these are the five
  questions to put to `/test-review` on resume:
  1. `wire_shape_key_fence.py` is a NON-`test_`-prefixed module imported by bare sibling name
     (`from wire_shape_key_fence import ...`), relying on pytest prepending the test dir to
     `sys.path` with no `__init__.py`. Is that sound and precedented anywhere in `backend/`? Is the
     basename repo-unique? The backend `pyproject.toml` documents the missing `__init__.py` as
     load-bearing for a namespace-package merge, so this is not a free choice.
  2. `title` is deliberately NOT in `FIELDS_KEPT_OFF_THE_WIRE`: red-agent argues its omission on the
     absent row is a PER-REQUEST condition, not a field-level policy, and that a field-level
     exclusion would reopen the exact hole the fence exists to close. Handled by call-site placement
     instead — the fence is called only from sites that set `title` explicitly, never from the RED
     class whose whole assertion is that `title` is ABSENT. Also judge whether an EMPTY frozenset
     earns its place versus not having the concept at all.
  3. The two hostile-`content` rows set `title=None` EXPLICITLY rather than leaving it absent, so
     the row's subject stays `content` alone and it does not flip from fence to red the moment
     green lands. Sound?
  4. FOUR files now, from one two units ago. Are the seams in the right places, or has this
     fragmented past the point where the pair still reads as a pair?
  5. ruff's isort put `from wire_shape_key_fence import ...` in the FIRST-PARTY block ABOVE
     `from dto.document.document_dtos import ...` in both live files — ruff's own classification via
     `--fix`, not hand-ordered. Stable, or a lint-config smell?
  KNOWN LOOSE END, discovered by test-review just before it died: `ruff format --check` flags a
  file from this unit. Unresolved. Note the prior unit established that `ruff format` already fails
  on three files at HEAD and is therefore NOT an enforced gate — so the question is whether this
  one is new or joins that set. Check before acting.
  **RESUMED AND CLOSED 2026-08-09.** `/test-review` re-ran to completion over the four files:
  clusters A and P clean, Se not applicable, S returned five findings against the shared helper —
  three applied to `wire_shape_key_fence.py`, one rejected, one handed to `/refactor`. 109 passed,
  4 skipped, unchanged; no assertion weakened.
  The applied three, in severity order:
  (i) **Fault masking.** `missing` aborted before `undeclared` ran, so a body that BOTH dropped a
  declared key and carried a spurious one reported one fault where two existed — the same defect the
  control file's own docstring (`..._wire_shape_control.py:47-54`) cites as its reason for splitting
  the JSON leg, re-imported one level down. Both sets are now computed before either asserts and are
  named in one message. Probed directly: dropped-only, spurious-only and both-at-once each fire, and
  the both case now names both.
  (ii) **`FIELDS_KEPT_OFF_THE_WIRE` deleted.** `X - frozenset()` is provably the identity, so no
  assertion could ever observe the symbol; eight lines of comment defended a thing that did nothing.
  The reasoning was kept as prose — reintroduce the constant in the commit that first needs a real
  exclusion, not before.
  (iii) `leg: str` → `Literal["dumped", "dumped JSON"]`, with an honesty note attached, for the
  reason under verdict 1 below.
  REJECTED: replacing `set(SaveDocumentRequestDto.model_fields)` with a frozen literal
  `{"content","title","version"}`. That deletes the helper's only reason to exist — growing with the
  model is precisely what the frozen call-site literals cannot do. Clusters A and S converged on this
  independently.
  HANDED TO `/refactor` (deleting a test is outside test-review's mandate):
  `test_should_carry_every_declared_field_on_the_dumped_body` (control:101-125) is byte-identical to
  `test_should_keep_a_real_title_on_the_dumped_body_byte_for_byte` (control:64-83) in arrange, act,
  whole-body literal and fence call; its only delta, `sorted(body) == [...]` at :121, is strictly
  implied by the dict equality at :117 and can never fail independently.
  THE FIVE VERDICTS:
  1. Bare-sibling import — SOUND and precedented (`login_router_fixtures`, `document_router_fixtures`,
     `gigachat_fixtures` all use the identical flat pattern), basename repo-unique, and the
     `pyproject.toml` namespace note is NOT implicated (it governs the two `statements/` dirs).
     **But it silently defeats mypy, which the question did not anticipate:** `pythonpath` carries
     `adapters/rest/tests` and not `.../dto/document`, so pytest resolves the module top-level as
     `wire_shape_key_fence` while mypy resolves the same file as `dto.document.wire_shape_key_fence`,
     and `ignore_missing_imports = true` swallows the mismatch. `reveal_type` at the call site gives
     `Any`; via the dotted path it gives the real signature. So no signature is checked at any call
     site and the `Literal` added in (iii) is documentation, not enforcement — recorded in the module
     comment rather than left as a promise the type does not keep. Pre-existing, and it hits all
     three precedent fixture modules equally.
  2. `title` correctly OUT of the exclusion set — per-request condition, not field-level policy, and
     call-site placement is the right mechanism. The empty frozenset did not earn its place; see (ii).
  3. Explicit `title=None` on the hostile-content rows — SOUND, and the strongest option: an absent
     title is the one key under active dispute, so a content row depending on it would flip from
     fence to red the instant green lands.
  4. Four files — seams are right. The axis is consistent (RED / fence / blank fence / shared
     assertion), the files share only imports, and the control file has ~22 lines of headroom, so
     the last split was forced by the cap rather than by taste. The real fragmentation smell is the
     duplicate method above, not the file count.
  5. isort ordering is STABLE but the config is incomplete: `ruff check --select I --diff` moves a
     hand-reordered import straight back, classifying `wire_shape_key_fence` as THIRD-party, because
     it is absent from `known-first-party` — where `gigachat_fixtures`, `statements` and
     `refusal_guard` are listed. `login_router_fixtures` and `document_router_fixtures` are missing
     too, so adding this one name alone makes the config MORE inconsistent. Left unpatched; the fix
     is one commit adding all three.
  RUFF FORMAT — NOT NEW, no action. Measured against a clean worktree at `7c744ca7^`: 5 files would
  be reformatted before the unit and the **same five** after (333 → 335 files formatted).
  `..._wire_shape_control.py` was already in that set and both files this unit CREATED are
  format-clean. The prior unit's "not an enforced gate" ruling holds, but its count was stale: it is
  five files, not three. `ruff check` also carries one pre-existing I001 in
  `adapters/db/src/model/document/document_model.py`, present at `7c744ca7^`.
  **ENVIRONMENT WARNING, worth more than the review findings.** test-review's first pass of edits
  was silently REVERTED on disk mid-run — `git diff` showed the file unmodified while `__pycache__`
  had been regenerated — and the working tree carried a change to `progress-frontend.md` that the
  agent did not make. Edits were re-applied and persistence verified by `git diff --stat`, and an
  earlier `109 passed` in that run was measured against the reverted file. This checkout is being
  shared by a parallel session and/or synced by OneDrive; `CLAUDE.md`'s file-ownership rule assumes
  separate `git worktree`s. Any measurement taken here is only as trustworthy as the tree it ran
  against — re-verify before relying on a number from this window.
  `/refactor` then deleted `test_should_carry_every_declared_field_on_the_dumped_body`
  (`..._wire_shape_control.py`), the duplicate test-review handed it — verified before acting: byte
  identical to `test_should_keep_a_real_title_on_the_dumped_body_byte_for_byte` in arrange, act and
  whole-body literal, both ending in the same fence call, and its lone delta `sorted(body) == [...]`
  is strictly entailed by the dict equality above it. The surviving method IS the full-declared-set
  call site, so the key-tracking capability is preserved; the deleted method's rationale was folded
  into the survivor's docstring. Also `body: dict` → `dict[str, object]`. **109 → 108 passed, 4
  skipped**, the −1 being exactly that test.
  `/refactor` additionally FALSIFIED verdict 1's implied remedy: re-spelling the imports dotted as
  `dto.document.wire_shape_key_fence` does NOT make the `Literal` enforced. Applied, then probed
  with a typo'd `"dmped JSON"` — mypy still reports success, because `mypy_path` in
  `backend/pyproject.toml` lists `adapters/rest/src` BEFORE `adapters/rest/tests`, so `dto.document`
  resolves to src, the helper is not found under it, and `ignore_missing_imports` silences the miss
  back into `Any`. Same hole via a longer path. Reverted; the comment now records the measurement
  and names what enforcement would actually cost (a `mypy_path` reorder, or moving the helper).
  BOTH REVIEW PASSES RETURNED **CONCERNS**, converging on the same most-severe finding. Chartered as
  the two rows below, plus one cross-layer hand-off:
  (a) **The fence's entire failure path is unpinned** — agent-review finding 1 and premortem #3,
  reached independently. All live call sites pass bodies where `missing` and `undeclared` are both
  empty, so the helper is a no-op everywhere it runs, and the only evidence the collected-`faults`
  rewrite works is the ad-hoc probe named in the commit message, which lives nowhere in the repo.
  This commit CHANGED that behavior; a revert to sequential asserts, an inverted `if`, or a
  `faults.append` under the wrong branch all leave the suite green with the fence dead. Sharpened by
  the environment warning above: a green count from this checkout is weak evidence, a committed test
  is not.
  (b) **Deleting the empty frozenset made the absent-title exception unenforceable rather than
  merely unobservable** — premortem #2. `declared - body.keys()` now demands `title` on EVERY body
  it inspects, and the sole defence is a comment saying the fence is called only from sites that set
  it. Point it at the absent row once the RED class unskips — the natural consistency move — and it
  goes red on the CORRECT body and green on the erasure body, with green written against it.
  (c) **CROSS-LAYER, not this session's file:** premortem #1 re-raises the frontend producer gap
  already recorded further down this file, with the sharper detail that
  `documentApi.conflict.test.ts:62`'s strict `toEqual` guards only the RETRY leg of a 409 and reads
  as a conflict-protocol test, so the author adding title support edits the literal and it passes.
  The guard belongs on the FIRST PUT in `documentApi.test.ts`. Hand to the frontend session.
  Recorded, not chartered: the commit message says pytest resolves the helper "top-level via
  `pythonpath`" — the file it commits says `prepend` import mode, and `pyproject.toml` agrees with
  the file. Commit messages are this project's only review surface, so the wrong explanation is the
  one a reader hits first. And `serialization_alias` on any field would make that field register as
  BOTH missing and undeclared, producing a doubly-misleading message — harmless today, worth knowing
  before someone reads a real fence failure.)
- [~] red-adapter rest (both review passes on `307ff37c`, converging: **the fence's failure path is
  pinned by nothing, and this commit is what changed it.** `assert_body_keys_track_the_model` runs at
  13 call sites and at every one of them `missing` and `undeclared` are both empty — it is a no-op
  wherever the suite exercises it. The collected-`faults` rewrite that this unit landed, the whole
  point of which is that a body dropping a declared key AND carrying a spurious one names both
  faults rather than one, is evidenced only by an ad-hoc interactive probe recorded in a commit
  message. Reverting to sequential asserts, inverting an `if`, or appending under the wrong branch
  each leaves 108 green with the fence dead — reopening, at zero cost, exactly the masking this unit
  existed to fix. Weight the evidence question: `progress-backend.md`'s environment warning for this
  window records edits silently reverted on disk mid-run, so a green count measured here is weak and
  a committed test is not. Test: `pytest.raises(AssertionError)` over the helper for dropped-only,
  spurious-only, and both-at-once, the last asserting BOTH field names appear in the one message.)
- [ ] green-adapter rest (the fence must fail, and say both things, when it should)
- [ ] red-adapter rest (premortem #2 on `307ff37c`: deleting `FIELDS_KEPT_OFF_THE_WIRE` traded an
  unobservable exception for an UNENFORCEABLE one, and the difference bites at green. The helper's
  `declared - body.keys()` leg now requires `title` on every body it inspects; the only thing
  keeping that correct is a comment saying the fence is called solely from sites that set `title`
  explicitly. Confirmed: all live call sites pass `title=None`, `""`, `"   "` or a real title, and
  none is the absent row. When the RED class in `..._wire_shape.py` unskips, extending the fence to
  it is the natural consistency move — and there the fence goes RED on the correct body (no `title`
  key) and GREEN on the erasure body (`"title": null`). Green for 2.1 is written against these
  fences, so the fence would be asking for the erasure. Guard: make the helper REFUSE the absent row
  outright — `assert "title" in body` with a message naming the RED class — or pin that it raises
  when handed a body with no `title` key. Sequencing: this wants to land BEFORE green.)
- [ ] green-adapter rest (premortem: the fence must refuse the row it cannot judge)
- [ ] green-adapter rest (premortem: absent must survive a DTO round-trip as preserve.
  RED landed at `backend/adapters/rest/tests/dto/document/test_save_document_request_dto_roundtrip.py`
  — a new `tests/dto/` tree, no `__init__.py` and no Statements class, matching the rest-adapter
  convention; the router file was at 197/200 and could not take it. The failing assertion is the
  `reparsed` one: `TitleUpdate(clears=True) != TitleUpdate(clears=False)`. Both sides are pinned
  against the LITERAL `TitleUpdate.preserve()`, not `before == after` — a self-equality is
  satisfiable by a green that erases the distinction in both directions, and Pydantic's
  `BaseModel.__eq__` ignores `model_fields_set` entirely, so `reparsed == request` passes today
  against the very bug. `content` and `version` are pinned too; those two already pass at HEAD and
  are round-trip-fidelity guards, not part of the red. Green owns the `document_dtos.py:47-53`
  docstring: it must be REWRITTEN against the new mechanism, not appended to with a warning, and
  lines 55-59 move with it — red left it untouched deliberately, since the paragraph cannot be
  written correctly until green picks between "stop depending on `model_fields_set`" and "give the
  DTO a serialization-stable spelling of absent".
  **REMOVE THE SKIP MARKER** — `test_save_document_request_dto_roundtrip.py:7`. Both review passes
  named this independently and it was missing from this row's first draft, which is what makes it
  worth spelling in capitals: the row was otherwise detailed enough to read as complete. The RED is
  spelled `@pytest.mark.skip`, which is inert in BOTH directions — silent while the bug is present
  AND after it is fixed — so nothing in the suite demands the marker's removal. Not hypothetical
  here: three RED skip markers from `3b9e5a25` (2026-08-03) are still parked
  (`test_login_lockout_acceptance.py:6`, `test_document_page_settings_read_acceptance.py:6`,
  `test_auto_editor_transition_acceptance.py:31`). `--runxfail` does not reach `mark.skip`, so no
  run mode surfaces it. Consider respelling as `xfail(strict=True)`, which self-clears via XPASS.
  **Green must be READER-side, not writer-side.** The shipped assertion derives its input from the
  code under test (`model_validate(request.model_dump())`) and pins only the COMPOSITION of writer
  and reader. A green that fixes the writer — `model_dump` defaulting to `exclude_unset`, or a
  `@model_serializer` that drops unset fields — turns the test green while `title_update()` still
  reads `model_fields_set` and still erases on every other path: a literal dict from a BFF hop,
  `model_construct`, `model_copy(update=...)`, a hand-rebuilt queue payload. Worse, `model_dump_json()`
  does not route through the Python `model_dump` method in Pydantic v2 — it goes to the Rust
  serializer — so a writer-only green leaves the JSON leg erasing, and JSON is what an offline outbox
  or a Redis save queue actually uses. Both incidents the red's docstring names are JSON ones.
  Guard against the collapse-into-preserve green already exists:
  `test_save_document_title_router.py:136` drives wire `{"title": null}` and asserts `clear()`.)
- [ ] red-adapter rest (premortem CREDIBLE: the erasure path is silent. `logger.` appears ZERO times
  across `backend/adapters/rest/src/router/document/`, `backend/adapters/db/src/access/document/`
  and `backend/usecase/src/document/`; there is no revision or audit table
  (`document_model.py` is the only document table) and `_update_values` overwrites `title` in place.
  So if a title is wiped in production it cannot be reported, counted, reproduced or recovered —
  the only undo is a database restore. The one observability guard in flight is aimed at a branch
  this route CANNOT reach: story 17 queues an `INVALID_TITLE_INTENT` → 422 log on
  `validation_exception_handler`, but `preserve()`/`clear()`/`of()` never produce the
  `__post_init__` contradiction, so that line fires zero times for PUT while the destructive path
  stays mute. Test: a `caplog` assertion that a `clears=True` save records the document id and the
  title it replaced. Sequencing — this wants to land BEFORE the story-17 db arm makes clears real.)
- [ ] green-adapter rest (premortem: a clear must leave a trace that names what it replaced)
- [ ] refactor-usecase (the transitional `str` arm is now dead in production). `SaveDocument.execute`
  still declares `title: TitleUpdate | str | None = None`, and `_title_intent` still maps a raw
  `str` and a bare `None`. The comment at `save_document.py:44-47` calls that spelling TRANSITIONAL
  and owned by adapters-discovery (a) — "the PUT route still hands the raw Pydantic field over".
  As of `green-adapter rest` it does not: the route is the ONLY production caller passing `title=`
  (verified — `document_wiring.py` merely constructs the usecase; nothing else calls `execute` with
  a title), and it now always passes a `TitleUpdate`. Both non-`TitleUpdate` arms are therefore
  reachable from tests only. Narrowing the signature requires editing `save_title_statements.py`
  and the usecase tests that still pass raw strings, which is why this is its own step and not a
  refactor tacked onto a behavior commit. Until it runs, that comment is stale in the other
  direction — it describes a route that no longer exists.
- [ ] red-adapter rest (agent-review: the PUT-404 guard asserts the TEST FIXTURE's wiring, not the
  production app's. `conftest.document_app:29` registers `not_found_exception_handler` itself, so
  commenting out `main.py:155` leaves the ENTIRE backend suite green — 641 passed — while every
  document 404 in production becomes a 500 and autosave retries it forever. Only the acceptance
  suite catches it, on the export route, and it needs a live backend. Either pin the production
  registry in the unit suite or narrow the docstring to what the test actually claims: "the route
  does not swallow `NotFoundException`". Also the nit next to it — the negative control builds
  `a_document(uuid4(), ...)` instead of taking the `owner_id` fixture, contradicting `a_document`'s
  own docstring, which exists to stop that drift.)
- [ ] green-adapter rest (agent-review: the production handler registry, or an honest docstring)
- [ ] red-usecase (premortem CREDIBLE: the replay branch swallows a title intent and answers 200.
  `_explain_miss`'s predicate is `current.content == sanitized and current.version == version + 1`
  — content and version only. A title-only change carries UNCHANGED CONTENT BY DEFINITION, so the
  "identical content" precondition that makes this branch rare for a content edit is the normal
  state for a rename or a clear. Proved against the real `SaveDocument` + fake repo: both a
  `TitleUpdate.of("Новое имя")` and a `TitleUpdate.clear()` at a stale version return 200 with
  `title='Старое имя'` and raise nothing — the editor reverts the field in front of the user, no
  409, nothing logged. The two halves have never met: the replay test
  (`test_save_document_usecase.py:145`) passes no title at all — `save_document_statements.py:64`
  omits the kwarg — and every title test saves at a MATCHING version, so the CAS always hits.
  The deeper gap is that nothing states what SHOULD happen (409, or apply the intent); the replay
  rule was written when title was inert. **Sequencing:** scenarios 4.7/4.8 pin this invariant for
  `page_settings`. When they land green, "the replay rule is guarded" reads as true while the title
  half stays open — the queued work CONCEALS this gap rather than closing it.)
- [ ] green-usecase (premortem: the replay branch must not silently discard a title intent)
- [ ] red-adapter rest (agent-review: PUT's whole-body guard seeds the fixture with the SAME
  content string the request sends, so the `content` key cannot distinguish the stored document
  from the request echoed back. Verified by mutation: adding `dto.content = request.content` to
  the route leaves 91 passed. `DocumentResponseDto.from_domain`'s docstring claims scenario 7.2 is
  structural — "the response cannot show unsanitized content, because it never has access to it" —
  and that is the invariant the mutation breaks. Fix: request `<p>raw</p>`, stored `<p>sanitized</p>`.
  Now TWO call sites, not one: agent-review re-confirmed on 2026-08-05 that
  `test_should_return_200_with_the_stored_document` seeds the same `"<p>saved</p>"` it sends, and
  with a correct green applied `dto.content = request.content` still leaves 95 passed. Fixing the
  first site does close the mutation, so the second is redundancy rather than a surviving hole —
  but its `content` key contributes nothing to the invariant it sits beside. Cover both.)
- [ ] green-adapter rest (agent-review: the content key must prove sanitization, not echo)
- [ ] red-adapter rest (premortem: from-generation's refusal branches are pinned zero times —
  `NotFoundException` → 404, `ValidationException(GENERATION_NOT_COMPLETED)` → 422 with the
  `error_code` the client branches on. `useGeneration` calls this from a poll loop, so a 500
  where a 422 was expected is a retry storm rather than a message. Also: `TestBearerIsRequired`
  claims "every document endpoint" and exercises POST /documents only — parametrize it over the
  write routes rather than adding a fourth near-copy.)
- [ ] green-adapter rest (premortem: refusal branches + auth on the write routes)
- [ ] red-adapter db (premortem: the replay is asserted only against a mock that was told the
  answer. `backend/adapters/db/tests/access/document/` has zero occurrences of `generation_id` —
  nothing asserts a second `save_new` on a used generation raises `ConflictException`, nor that
  `find_by_generation_id` returns the winner and `None` for a foreign owner. That translation is
  what `_recover_existing` rolls back and re-reads on, and a fake raising because the test told
  it to does not test that Postgres does.)
- [ ] green-adapter db (premortem: the generation-id uniqueness translation)
- [ ] green-acceptance

### Scenario 2.2: Stored page settings round-trip unchanged
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.3: A stored object missing a later-added key reads as that key's default

**Constraint carried from 2.1's premortem (2026-08-04) — read before starting.**
`PageSettingsDto.from_domain` (`get_document_response_dto.py`) enumerates exactly nine keys
positionally. `documents_get.yaml` promises the opposite: an object carrying a key this version
does not define is *preserved*. The day `from_stored` gains that tolerance, the read model
silently drops the tenth key — and because the client echoes back what it read, the next PUT
overwrites the preserved object with the truncated one. Preserved in storage, invisible on the
wire, then destroyed. It is unreachable today only because the mapper raises `TypeError` on an
extra key, which is precisely why 2.3/2.4 will not think to revisit the DTO: their brief is the
mapper, and the DTO will look already-done. Also resolve `documents_get.yaml`'s
`additionalProperties: false` against its own "preserved" prose — they contradict.

- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.4: A stored object carrying an undefined key or constant is read, not rejected
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.1 / 1.2: Ownership guards on read, write and export
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: An unknown key inside page settings is rejected
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.2: An unknown sheet size or orientation is rejected
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.3: Numeric bounds are inclusive and rejected one step outside
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.4: Margins that leave no content box are rejected at the exact equality
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.5: Geometry whose content box cannot hold one line is rejected
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.6: Malformed numbers are rejected
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.7: An over-length header or footer is rejected, never truncated
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.8: A rejected request leaves the content byte-identical
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.1: Omitted page settings leave the stored value untouched
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.2: Explicit absence resets the page settings to the default preset
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.3: A supplied object replaces the stored one wholesale
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.4: Only allow-listed keys are persisted
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.5: Header text is normalized and round-trips byte-exact
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.6: A stale version is refused on a page-settings save
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.7: Replaying an identical save applies it once
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.8: A content save and a settings save do not silently drop each other
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.1: An export immediately after a settings save reflects the new geometry
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.2: Manual page breaks are honoured in both formats
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.3: A default-settings document exports exactly as it did before this story
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.4: A partially applicable render fails instead of dropping an element
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.5: An unresolvable document font fails the export rather than substituting
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Integration Scenarios (06_Integration_Tests.md)

### Scenario 1.1: The realised page geometry matches the settings in every target
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.2: Numbers are formatted under an invariant locale
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1: The PDF renderer honours manual breaks, headers and numbering
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.2: The DOCX renderer emits breaks, headers and section geometry
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: A resolvable font renders without touching the network
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.2: An unresolvable font fails the render instead of substituting
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Security Scenarios (05_Security_Tests.md)

### Scenario 1.1: Foreign page settings cannot be read, written, or exported
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1 / 2.2: Mass assignment — allow-listed keys only, server-owned fields unwritable
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: Header markup cannot execute in the editor
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.2: Header text cannot break out of the DOCX header XML
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.3: The page-number placeholder syntax in user text is not interpreted
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.4: Geometry values cannot inject into the generated stylesheet
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.1 / 4.2: Rejections expose no internals; header text does not leak into logs
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.3: DOCX metadata stays redacted after the headers extension
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.1 / 5.2: Endless-pagination geometry and over-limit structure are refused
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Load Scenarios (03_Load_Tests.md)

### Scenario 1.1: Export sustains its rate with page settings applied
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.2: Concurrent renders stay bounded under sustained export load
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Infrastructure Scenarios (04_Infrastructure_Tests.md)

### Scenario 1.1: A missing document font fails the application at boot
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.2: The render path depends on no system-installed face
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1 / 2.2: Page settings survive database unavailability and restart
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: An old instance still serves documents after the column lands
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.2: An old instance's save does not erase page settings
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance
