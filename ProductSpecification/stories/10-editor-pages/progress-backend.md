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
- [x] red-adapter rest (both review passes on `307ff37c`, converging: **the fence's failure path is
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
  spurious-only, and both-at-once, the last asserting BOTH field names appear in the one message.
  **LANDED GREEN, honestly — and the mutation table is the whole evidence.** New file
  `test_wire_shape_key_fence.py` (84/200), three methods, no production or helper file changed
  (`git diff --stat backend/` empty; the helper was mutated and restored via `git checkout --` each
  time). The fence is correct at HEAD, so a test over it passes; manufacturing a red would have
  meant asserting something false. Predicted no-failure and got none — the one way it could have
  failed was a message mismatch from pytest's assertion rewriting appending an `assert not [...]`
  explanation to `str(failure.value)`, predicted NOT to apply because rewriting reaches only
  `python_files` plus conftest/plugins and this helper is a bare non-`test_`-prefixed sibling.
  Confirmed by test-review: no `register_assert_rewrite` in project source, no `conftest.py` in
  `dto/document/`.
  Three mutations, each restored after; the count that matters is the SECOND one, how many
  pre-existing tests noticed:
  - **A** — collected `faults` reverted to two sequential asserts: `1 failed, 110 passed`. Only the
    both-at-once row fails, and its message names `['title']` alone with the `; and ['note'] is on
    the body but declared nowhere` clause gone. **All 108 pre-existing tests stay green.**
  - **C** — the undeclared fault appended under the `if missing:` branch: `2 failed, 109 passed`,
    and spurious-only **DID NOT RAISE AT ALL** — the fence goes completely silent on a spurious key
    while the suite reports 109 passed. **All 108 pre-existing stay green.** test-review reproduced
    this one and found the spelling matters: an *unconditional* append inside the branch gives
    `2 failed, 109 passed` as recorded, while a *nested* `if undeclared:` inside `if missing:` gives
    `1 failed, 110 passed` with the same DID-NOT-RAISE. Both are killed, so the guard is stronger
    than claimed — but a reader reproducing the recorded count needs the unconditional spelling.
  - **B** — `if undeclared:` inverted: 13 failed. Not discriminating, already loud.
  No class-level skip marker, deliberately: the marker is class-level, so parking the ONLY test of
  the fence's failure path behind one makes it inert for exactly the red period — which is when the
  green that could trip it gets written. Third time this scenario has faced that trap and acted on it.
  `/test-review` returned **0 violations, 0 edits** across A and P (S and Se not applicable — no
  Statements classes under `backend/adapters/rest/tests`), and re-ran mutations A and C itself
  rather than taking them on report. Its four verdicts:
  1. **Exact equality on `str(failure.value)` is correct, keep it.** The message is authored by the
     code under test and deterministic in every fragment (`sorted()` fixes list order, dict `repr` is
     insertion-ordered, `leg` is a closed `Literal`). Substring assertions on the field names would
     still kill mutation A but would NOT kill a mutation mangling the `'; and '` joiner or dropping
     the `got {body!r}` tail — exact equality strictly dominates. The brittleness is correctly
     priced: this row's subject IS the wording.
     **But the no-rewriting assumption is load-bearing and written down nowhere.** Rename the helper
     to a `test_`-prefixed name, or add `register_assert_rewrite("wire_shape_key_fence")`, and all
     three assertions break at once with a confusing diff. test-review recommended a line in the
     class docstring recording it and did not edit unilaterally, since it is not a detector
     violation. **Open — carry it into the next unit touching this file.**
  2. No skip marker — sound, for the reason above, plus: the file passes because the fence is
     correct, not because it asserts nothing, and the mutation table supplies the falsifiability a
     marker would otherwise stand in for.
  3. Own file — seam right, and the CAP is the weaker half of the argument (162 + 84 = 246 > 200).
     The subject genuinely differs: the four `test_save_document_request_dto_*` files test what the
     DTO writes; this tests the assertion helper they all call, including a branch dead at all 13
     live call sites. The set reads as 4+1 and the naming carries the boundary. One coherence gap
     left open: the control file's docstring maps the earlier splits and has no pointer to this new
     file, so a reader arriving there has no signpost. It has 38 lines of headroom.
  4. Convention matches — bare sibling import, identical spelling to line 3 of both control files,
     no `__init__.py`, no Statements class.
  `/refactor` closed both of test-review's open items and found a third by doing so. Docstring-only,
  111/4 unchanged: (1) the assert-rewrite assumption is now RECORDED in the new file's class
  docstring — probed in an isolated scratchpad rather than in-tree, and with rewriting on the message
  gains a trailing `\nassert not ['a', 'b']`, breaking all three exact equalities at once with a diff
  that reads as a wording change; the docstring names the trigger, the symptom, and directs the fix to
  comparing against the SUFFIXED message rather than loosening to substrings. (2) the control file
  now signposts the fence's own tests. (3) **the "13 call sites across three live files" claim in
  this commit is FALSE** — counting them to write the signpost showed **10 calls across TWO** files
  (control ×6, blank control ×4; the RED file has ZERO, as the helper's own docstring says). 13 is the
  mutation-B failure count transcribed as a call-site count, and reaching 13 means counting the new
  file's own three calls — the ones where `missing`/`undeclared` are NOT empty, contradicting the
  sentence that counts them. It contradicted `..._wire_shape_control.py:37` ("the 10 live calls") in
  the same directory. Corrected in both files; agent-review found it independently. **The wrong number
  survives in this commit's message and in the two prose paragraphs above — read 10/2, not 13/3.**
  All three detector clusters came back clean, with two mechanics candidates rejected under restraint
  (extracting `declared`/`missing`/`undeclared` out of the 14-line helper, and splitting a
  `_collect_faults` off the assert that consumes it — both hide the missing/undeclared symmetry the
  collected-`faults` shape exists to express) and the shared message prefix deliberately NOT hoisted
  to a constant: it is the subject under test, and a constant would compare the helper's format
  string to itself.
  BOTH REVIEW PASSES RETURNED **CONCERNS** again. Chartered as the rows below; the fourth item is
  cross-layer and the fifth is a note for whoever writes the absent-row red:
  (a) **The fixture collides with the helper's own worked example** (agent-review 2). The
  spurious-key row uses `"note"`, and `wire_shape_key_fence.py`'s docstring works its entire reason
  for existing through a measured pydantic run using a field literally named `note`. If that field
  lands, `undeclared` goes empty, the fence does not raise, and the guard over the spurious leg dies
  as `DID NOT RAISE` — in the exact event it was written to survive. Loud, not silent, but it reads
  as "the fence broke" in a commit where attention is on the model change.
  (b) **Nothing pins that the fence is CALLED** (premortem #2). This commit guards the helper's body;
  delete all 10 call sites and the suite is fully green, because the new file imports the helper
  directly and passes standalone. This commit made that cleanup SAFER to make — the helper now has
  its own passing test file, so removing its callers leaves something that still looks guarded, and
  the helper's own docstring concedes "on the CURRENT model it catches nothing the literals miss",
  which is the argument the fence exists to refuse.
  (c) **The three expected messages freeze the declared set as an unwritten constant** (premortem
  #3). Add any fourth field and test 1's `['title']` becomes `['newfield', 'title']` AND test 2 — the
  spurious-only row — grows a `missing` clause it was written never to have, so exact equality fails
  on a row whose whole subject is the other leg. Three cryptic string failures land on a developer
  whose change had nothing to do with the fence, and the path of least resistance is `assert "note"
  in str(...)` — substrings, which by this unit's own test-review finding do NOT kill a mutation that
  mangles the joiner or drops the body tail. The guard degrades to the shape it was written to beat.
  (d) **CROSS-LAYER, frontend session's file** (premortem #1, sharpened): grepping ~60 files across
  `documentApi` / `useDocumentSave` / `ManualEditor.autosave*` finds **zero** assertions over the PUT
  body's KEY SET. The named guard is `Object.keys(body).sort()` equality on a title-untouched save —
  explicitly NOT `not.toHaveProperty('title')`, which passes for `title: undefined` and would pass a
  body built through a spread or a schema-defaulting client that materializes it as `null`.
  (e) **Note for the absent-row red below:** read as a contract, the failure-path tests now state
  `title: null` is the well-formed body and absent `title` is the fault — the invariant inverted.
  That IS the next row, but fixing it must now also rewrite all three exact-equality literals, and
  the new file's docstring carries no pointer to that pending change.)
- [S] green-adapter rest (the fence must fail, and say both things, when it should) — SKIPPED: no
  implementation to write. The fence is correct at HEAD; the red half was the missing guard over
  already-correct code, proven by two mutations that leave the entire pre-existing suite green. A
  green step here would be a no-op commit.
- [x] red-adapter rest (premortem #2 on `307ff37c`: deleting `FIELDS_KEPT_OFF_THE_WIRE` traded an
  unobservable exception for an UNENFORCEABLE one, and the difference bites at green. The helper's
  `declared - body.keys()` leg now requires `title` on every body it inspects; the only thing
  keeping that correct is a comment saying the fence is called solely from sites that set `title`
  explicitly. Confirmed: all live call sites pass `title=None`, `""`, `"   "` or a real title, and
  none is the absent row. When the RED class in `..._wire_shape.py` unskips, extending the fence to
  it is the natural consistency move — and there the fence goes RED on the correct body (no `title`
  key) and GREEN on the erasure body (`"title": null`). Green for 2.1 is written against these
  fences, so the fence would be asking for the erasure. Guard: make the helper REFUSE the absent row
  outright — `assert "title" in body` with a message naming the RED class — or pin that it raises
  when handed a body with no `title` key. Sequencing: this wants to land BEFORE green.
  **LANDED, a REAL red, first run, prediction byte-identical.** `pytest.raises` is SATISFIED — the
  fence does raise — and the test's own exact-equality assertion on the message is what fails,
  because the un-partitioned `missing` leg reports the generic dropped-field fault where the charter
  demands a refusal naming the call site the fence must not be reached from. Predicted and actual
  both: `...['title'] was declared on the model and dropped by the serializer, got {'content':
  '<p>saved</p>', 'version': 1}`. 111 passed, 5 skipped.
  **The charter's own remedy was wrong, and red-agent said so instead of implementing it.**
  `assert "title" in body` would have been the same assertion wearing two names: the fence's ONLY
  observable is `body`, and "the caller handed me the untouched row" and "the serializer dropped
  `title`" produce the IDENTICAL dict. A layered guard fires on exactly the set the `missing` leg
  already fires on and can only ever preempt it. What IS distinguishable is WHICH field is absent —
  `title` is the single declared field whose absence is under dispute (the skipped RED class asserts
  the untouched row must omit it), while nothing anywhere claims a body may omit `content` or
  `version`. So green must PARTITION the `missing` leg, not double it, and the refusal is collected
  into `faults` like any other fault rather than raised ahead of them, so an absent-title-plus-
  spurious-key body still reports both directions in one message.
  **The carried inversion is resolved.** `test_should_name_a_declared_key_the_body_dropped` and the
  both-faults row moved from a dropped `title` onto a dropped `content`. Read as a contract those two
  rows previously stated that `title: null` is the well-formed body and absent `title` is the fault —
  2.1's invariant exactly backwards. Exact equality preserved on every message; the fixtures moved,
  not the strictness, and test-review traced both re-fixtured bodies through the helper to confirm
  the literals are byte-exact. `content` is required, non-defaulted, and claimed by nobody to be
  omittable, so it is the unambiguous fixture for the generic leg.
  `/test-review` found 0 assertion violations, 2 placement, 2 helper-quality — and SPLIT THE FILE,
  which was owed:
  - NEW `test_wire_shape_key_fence_title_refusal.py` (92) — the red row moved out, marker back at
    CLASS level, assertion byte-identical. Method-level was right GIVEN co-location (a class marker
    would have parked the three rows that are the suite's only executed coverage of the fence's
    failure path — all 10 live call sites hit only the do-nothing branch) but it was the one
    method-level marker in the directory. The split dissolves the conflict rather than trading one
    hazard for the other. Seam is SUBJECT, not arithmetic: rows 1-3 are model-agnostic fault
    reporting; row 4 is 2.1-specific, one-field-specific, and the only row naming a sibling class and
    file inside its asserted string.
  - `test_wire_shape_key_fence.py` 192 → **135**, class docstring corrected (it still claimed a
    fourth row) with a pointer to the new file. Doing the split NOW matters: the next chartered unit
    renames the `"note"` fixture key inside frozen equality literals in rows 2 and 3, which is not a
    one-line edit on a file being simultaneously re-cut.
  - `wire_shape_key_fence.py` 95 → 107, two runtime guards: the unenforced `WireLeg` Literal (mypy
    types the callee `Any`; a typo'd `"dmped JSON"` was previously MEASURED as accepted), and an
    empty `declared` set, which would skip both `if`s and pass without examining `body` at all.
  - The skip reason was partial — it named the failure and quoted the wrong output verbatim but
    delivered the consequence as the code mapping only. It now states the erasure itself: no error
    raised, nothing surfaced to the author, prior title retained nowhere, unrecoverable.
  KNOWN AND ACCEPTED: the expected message hardcodes `TestSaveDocumentRequestDtoWireShape` and its
  filename, pinned against the fence's own string rather than the real class, so a rename leaves the
  row green pointing at nothing. Staleness, not looseness, and the right trade — a refusal that does
  not say where the body came from leaves the reader the same puzzle the generic fault left them.
  Documented in the moved row's docstring rather than loosening the pin.
  DEFERRED by test-review, recorded so a later pass does not "correct" them: the `undeclared` leg is
  subsumed by the frozen `body == {...}` at all 10 sites, but removing either side is a WEAKENING and
  is refactor territory; and `model_fields` as a calculated expected is normally a smell but is this
  helper's entire reason to exist.
  **FOR GREEN, from test-review and worth weighing against the partition verdict above:** the skipped
  row prescribes hardcoding a sibling class name inside shared infrastructure called from two other
  files, which contradicts the helper's own module comment (lines 23-29) arguing that CALL-SITE
  PLACEMENT, not field-level policy, carries this condition. Consider having green pass the
  un-judgeable field set IN from the call site rather than baking `title` into the fence.
  `/refactor` applied exactly one change, and it is agent-review finding 2 arriving independently:
  the closed leg set was declared TWICE — as `WireLeg = Literal[...]` and again as a runtime tuple
  in the new guard — so a leg added to the type would have been rejected by the very guard meant to
  police it. Now `assert leg in get_args(WireLeg)`, which is what the guard's own message already
  claimed ("one of the declared WireLeg values"). Behavior probed identical; 111/5 unchanged.
  Both deferred items came back NO ACTION, and the first correction is worth keeping:
  (a) **the `undeclared` leg — the deferral's premise was incomplete.** Subsumption by the frozen
  `body == {...}` holds at the 10 live call sites, but there are **14**, and two of the other four
  exercise `undeclared` directly (`test_wire_shape_key_fence.py:95` pins its message by exact
  equality; `:107` pins the both-faults message). Removing the leg deletes a guard AND its tests
  together, collapses the `'; and '` joiner to dead code, and retroactively makes the collected-
  `faults` design look like ceremony — inviting the revert to sequential asserts that the class
  docstring records as leaving everything green with the fence dead.
  (b) `set(model_fields)` as a calculated expected stays, with two properties any future editor must
  treat as load-bearing: the `assert declared` vacuity guard, and the fact that every live site
  asserts a frozen whole-body literal ALONGSIDE the fence rather than delegating to it. **If a call
  site ever drops its literal and leans on the fence alone, this stops being an acceptable
  calculated expectation and becomes the smell.**
  BOTH REVIEW PASSES RETURNED **CONCERNS**, converging on the same highest-severity finding:
  (a) **The re-fixturing re-encoded the inversion it was meant to remove** — agent-review 1 and
  premortem #3, reached independently and rated top by both. The replacement fixture is
  `{"title": None, "version": 1}` with `['content']` pinned as the ONLY fault, so two LIVE
  (non-skipped) rows now certify by exact equality that a body carrying `title: None` — the erasure
  spelling — is key-set-clean. The old fixture only implied it by omission; the new one states it.
  Nothing forced the choice: `{"title": "kept", "version": 1}` drops `content` just as unambiguously
  and carries no claim about the null spelling. The docstring's own justification ("`content`
  carries no such dispute") argues for dropping `content`, not for spelling the retained `title` as
  `None`. And it survives green silently — after the partition `title` is present in both bodies, so
  the messages stay byte-exact and nothing fails. Chartered below.
  premortem sharpened it into the incident: after green the fence's opinion on `title` is
  **absent → refuse, present-and-null → accept silently** — the erasure spelling is in its ACCEPT
  set. An 11th call site that uses the documented shared guardian and does not ALSO freeze a
  whole-body literal ships `{"title": None, ...}` past a green fence named for this invariant.
  (b) **Both new helper guards are untested, and `/refactor` edited one anyway** (premortem #2). No
  row passes a bad leg; no row asserts either message. The typo'd `"dmped JSON"` was MEASURED as
  accepted and the measurement never became a test — then `/refactor` rewrote that exact assertion
  with nothing standing behind it. Two sub-findings: the leg guard sits BEFORE both fault legs and
  preempts them, so a typo'd leg on a genuinely broken body reports the label instead of the fault,
  unpinned; and `assert declared` is **unreachable by construction** — a pydantic model always has
  `model_fields` — so it is a dead line in a near-cap file. Do not fake a guard for it; say so or
  remove it.
  (c) **The empty-`declared` comment is factually wrong** (agent-review 3), in a commit whose whole
  discipline is that comments are measured claims. With `declared == set()`, `undeclared` becomes
  ALL of `body`'s keys, so the leg fires for any non-empty body. The vacuous pass it describes needs
  `body` to be empty TOO. Fix the comment (or delete the line per (b)).
  (d) **The fence's module comment now contradicts the row committed against it** (agent-review 4).
  Lines 23-29 argue the absent-`title` condition is per-request, that there is deliberately NO
  field-level exclusion set, and that call-site placement carries it. The red row demands the
  opposite: a `title`-specific branch inside shared infrastructure, hardcoding a sibling class name.
  Both ship in the same commit, unreconciled — and the note recorded above for green ("pass the
  un-judgeable field set in from the call site") is only a suggestion in a progress file, while the
  ASSERTED STRING already pins the field-level spelling by exact equality. **Green cannot take the
  call-site route without editing the red row, which is not green's to edit.** The choice was made
  here, not deferred. Green must either accept it or say plainly that the red row is being amended
  and why.
  (e) **Skip-marker exit condition, named here so it is not prose** (premortem #1): the marker is at
  CLASS level in `test_wire_shape_key_fence_title_refusal.py`, and this scenario has sprung the
  inert-marker trap three times. Green's exit condition is written into the row below.)
- [x] green-adapter rest (premortem: the fence must refuse the row it cannot judge.
  **EXIT CONDITION, explicit:** remove the CLASS-LEVEL `@pytest.mark.skip` from
  `test_wire_shape_key_fence_title_refusal.py`, and check the NUMBER — the suite must come back
  **112 passed, 4 skipped**. Nothing fails if green leaves the marker on; the count is the only
  guard, and the marker being class-level means the whole file goes with it. This scenario has hit
  that trap three times.
  Implement the PARTITION, per the red's design verdict: `title` gets a refusal naming the forbidden
  call site, every other declared field keeps the generic dropped-field wording, and the refusal is
  collected into `faults` like any other rather than raised ahead of them — so an absent-title-plus-
  spurious-key body still reports both directions in one message. Weigh test-review's competing
  call-site-parameter design first and record the decision; note agent-review 4 above — taking that
  route means amending the red row's asserted string, which green must do openly if at all.
  While here, close premortem #2's gap in the same pass: one row asserting a typo'd leg label raises
  with its exact message, and a decision on the unreachable `assert declared` line.
  **LANDED. 113 passed, 4 skipped** — the exit condition's number was 112, and the extra one is the
  chartered leg-guard row, which is a genuinely new test rather than a marker lift. Marker removed
  (file 92 → 80, nothing else in it touched). Full backend 683 passed, 68 skipped, 0 failed. No
  production code changed — the fence is test infrastructure.
  PARTITION implemented as the red asserts it: `if "title" in missing` appends the refusal, then
  `dropped = missing - {"title"}` keeps the generic wording, both collected into `faults` alongside
  `undeclared`. The call-site design was weighed and REJECTED, and the reasoning goes past "the red
  pins it": the call-site route moves the WORDING into a parameter, and the wording is this row's
  whole deliverable — every site would then re-spell or import the same one-element fact, and a site
  that forgets it silently gets the generic dropped-field wording back, which is the exact defect the
  partition exists to close. Field-level keeps one declaration and cannot be forgotten.
  The contradicting module comment (lines 23-29) was rewritten rather than left to rot: `title` is
  not EXCLUDED — an exclusion set would make the absent row PASS, silently certifying the erasure —
  it is PARTITIONED; call-site placement still carries the rest; and the call-site alternative is
  recorded as weighed and rejected with the reason above.
  `assert declared` removed with its comment, no fake guard put in its place, and both errors written
  down: `model_fields` is always populated so no reachable input trips it, AND with `declared ==
  set()` the `undeclared` leg fires for any non-empty body, so the vacuous pass the comment described
  also needed an empty `body`.
  Leg guard KEPT ahead of both fault legs, with the reason now in the code: under the other order the
  fault IS reported but attributed to a leg that does not exist — a wrong report, not a partial one,
  sending the reader to the wrong serializer. A typo'd leg is a one-edit caller defect and the fault
  re-reports next run. The comment says explicitly that this is the opposite call from the two legs
  below it. The new row uses a WELL-FORMED body, so with both fault legs quiet the message can only
  come from the guard.
  `/test-coverage rest --focus` — production source **348/357 lines (98%), 16/16 branches (100%)**,
  and the focus filter over `backend/*/src/` returned ZERO files, correctly: nothing production
  changed. All nine uncovered lines are the `raise NotImplementedError("wired by the application
  composition root")` bodies of `Depends()` provider stubs, pre-existing and covered by the
  application tests.
  **The fence helper reads 100% line AND 100% branch — and that number is not evidence.** Every `if`
  gets both outcomes across the five rows, so coverage.py is satisfied, while the partition's risk
  lives in COMBINATIONS, which branch coverage cannot see. Sharpest consequence measured: a mutation
  that raises the refusal AHEAD of `faults` — precisely the shape this green rejected and argues
  against in the helper's own comment — leaves all five rows green. So does moving the leg guard
  below `faults`. Two arms have no test at all (both-missing-at-once; refusal co-occurring with
  `undeclared` — row 4 pins the `'; and '` joiner for dropped+undeclared only) and the leg guard's
  PREEMPTION is unpinned because row 3's body is well-formed. Four steps added below.
  KNOWN, pre-existing, not this unit's: `ruff check backend/adapters/rest` reports one E501 at
  `test_save_document_request_dto_wire_shape_control.py:40` — a long line inside a class docstring,
  confirmed present without this unit's changes. The lint gate stays red until someone rewraps it.
  `/refactor` fixed that E501 (prose rewrap at a sentence boundary; `ruff check
  backend/adapters/rest` now **All checks passed**) and corrected three present-tense claims this
  unit falsified — "the four calls below are the only others" (five now, the fifth in the refusal
  file), "the control file is at 162 of 200" (170), and a split rationale still describing a skip
  marker this unit removed. Both protected orderings untouched; `wire_shape_key_fence.py` has NO
  diff at all. Every changed line is prose — zero executable lines — 113/4 exactly. It ruled NO
  ACTION on the roundtrip file's triplicated three-field assertion, and the reason is worth keeping:
  two of the three sites are inside a class still skip-marked RED, so extracting now would couple the
  one live row to two red rows and a green adjusting one leg's pin would silently move the live row
  too.
  BOTH REVIEW PASSES RETURNED **CONCERNS**. agent-review cleared two things first, recorded so they
  are not re-litigated: the class named in the refusal string exists and does not call the fence, so
  the module comment's "never from the RED class next door" holds; and losing generic drop-detection
  for `title` costs nothing at the 10 live sites, because each asserts `body == {...}` BEFORE calling
  the fence, so a dropped `title` fails on the literal and the refusal is never reached.
  (a) **premortem's finding is one level up from everything chartered so far, and it is the one that
  matters: this whole cluster fences a serializer production never invokes.**
  `SaveDocumentRequestDto` appears in `backend/**/src` exactly twice — its definition, and as an
  INBOUND request parameter at `document_router.py:168` — and `grep -rn "model_dump"
  backend/adapters/rest/src` returns ZERO hits. The DTO is inbound-only. The body that actually
  reaches `title_update()` is written by the FRONTEND, so all five fence rows, all ten live call
  sites and the entire wire_shape cluster can be green while the shipped request body says
  `"title": null`. This commit records the fact ("no production code changed — the fence is test
  infrastructure") and stops short of the consequence. **Read as a whole the charter promises that
  closing (a)-(f) makes 2.1 safe; it does not** — five of the six are about a serializer nothing
  calls. Chartered as a real step below.
  (b) **The leg-guard row's docstring claims coverage this same unit measured as absent**
  (agent-review 1): it says the well-formed body "makes this row pin the guard's preemption too",
  and it does not — with no fault to preempt, moving the guard below `faults` leaves the row green.
  The paragraph above in this very file says so and charters the row that would pin it. That false
  sentence is exactly how a chartered step gets closed as already-done by a reader who trusts a
  docstring over a charter. Strike it in the coverage-red pass below.
  (c) **The rejection reasoning rests on a claim the code does not deliver** (agent-review 2). The
  module comment rejects the call-site design partly on "the field-level spelling keeps one
  declaration and cannot be forgotten", but `"title"` is spelled as a frozen literal at two sites
  beside the model — the same failure mode the helper's own docstring invokes to justify reading
  `model_fields` at run time. Low practical risk (a rename flips the refusal row's exact-equality
  message to the generic wording and fails loudly), but the honest wording is "one declaration, and a
  rename fails the refusal row loudly". Correct the comment.
  (d) Two more stale claims the refactor pass missed while rewriting their neighbours in the same
  docstring: "the absent-`title` body is now the fourth row's subject" (the new row is the fourth in
  THIS file; the absent-title row lives in the refusal file) and "leaves all 108 tests green" (113).
  Note `/refactor` deliberately left the 108 alone as a historical statement — that reading is
  defensible, but it sits ambiguously present-tense next to a claim that IS wrong.
  (e) The leg-label row sits outside its class's declared subject — `TestWireShapeKeyFenceReportsEvery
  Fault` closes "this file stays model-agnostic: fault reporting in both directions", and a leg-label
  refusal is neither direction and never reaches `faults`. Low severity, but the file already split
  once on that seam and this quietly widens it.
  **premortem measured the partition's survivors, confirming the coverage warning empirically** —
  full 16-row directory suite per mutant: refusal `faults.append` moved AFTER dropped+undeclared →
  **16 passed, survives**; refusal suppressed whenever another fault co-occurs → **16 passed,
  survives**; `dropped = missing` (partition removed, double report) → 1 failed, caught. Both
  survivors are exactly the chartered coverage row below, which is therefore the ONLY thing standing
  between the partition and a silent revert — **its wording must stay exact-equality, never
  substring.**
  Rated REMOTE and recorded rather than chartered: the refusal cites a class that is still
  skip-marked, and `title: str | None = None` means `model_dump()` always emits the key, so the
  refusal leg is unreachable from any real serializer output and fires only on hand-written fixtures
  — fold a re-read of the citation into the coverage green once that skip lifts. And a non-dict body
  raises a bare `AttributeError` with no leg label, guarded in practice because all ten live sites
  assert whole-body equality on the line above.)
- [x] red-acceptance (premortem on `f935be3c`, the finding that outranks the whole wire-shape
  cluster: **nothing in the repo drives the real save path end to end, so nothing goes red when the
  erasure ships.** `SaveDocumentRequestDto` is INBOUND-ONLY — two occurrences in `backend/**/src`
  (its definition and the router parameter), zero `model_dump` call sites anywhere in
  `backend/adapters/rest/src`. The serializer this scenario has spent five work units fencing is
  never invoked in production. The producer is `frontend/src/features/generation/api/documentApi.ts`,
  whose `saveDocument(documentId, content, version)` sends `{content, version}` — the safe shape,
  today, by accident of not having a title parameter. The erasure arrives the moment story 10 adds
  title editing to that signature, and NEITHER SIDE of the wire goes red when it does: the router
  rows in `test_save_document_title_router.py:57` pin the server's READING of an absent key but
  hand-write the JSON, so nothing asserts any real producer emits it.
  Test: a content-only save through the actual client against a document with a stored title,
  asserting the stored title survives. That row is the only thing that would catch the frontend
  regression, and it is the row nobody chartered. Sequencing: this is the guard the six chartered
  fence rows do not add up to — do not let 2.1's green-acceptance stand in for it, and do not read
  the fence cluster going green as this being covered.
  **RE-RAISED AND SHARPENED by premortem on `7b0a9c51`, now with the row spelled out and its
  scaffolding measured as already built.** The absent-title path is guarded piecewise and never in
  composition: `test_save_document_title_router.py:57` drives `{"content", "version"}` but against a
  MOCKED usecase and asserts only that `execute` was called with `TitleUpdate.preserve()` — nothing
  below the port runs; `backend/adapters/db/tests/access/document/test_document_storage_title.py:61`
  passes a HAND-CONSTRUCTED `TitleUpdate.preserve()` — nothing above the port runs. Acceptance covers
  the BLANK row full-stack (`document_blank_title_save_statements.py`) and never the ABSENT row: both
  backend `save_document(` call sites pass a title (`document_blank_title_save_statements.py:53`,
  `document_export_filename_statements.py:56`). `title_update()` is the single hinge and its one
  honest exercise is against a mock.
  THE ROW, named: `given_owner_autosaves_content_only_over_a_stored_title` in
  `acceptance/statements/document_blank_title_save_statements.py`, calling `save_document(...)` with
  `title=None`, then reusing the existing `assert_filename_rfc5987_encoded_from_title` step. Nearly
  free — the client already omits the key when `title is None`
  (`acceptance/clients/application/application_client.py:127-129`), the statements class already
  subclasses `DocumentExportFilenameStatements`, and the export header is already documented there as
  the only black-box observation of the stored title that exists.
  premortem rates this BLOCK-adjacent: it and the parked roundtrip RED below are the same incident
  from two sides, and they compound — unparking that RED and fixing the reader WITHOUT first landing
  this end-to-end row means the fix is verified only by tests that were already green while the bug
  was present. Land this first.)
  **LANDED GREEN ON ARRIVAL — and the first mutation SURVIVED, which is the finding.** Predicted no
  failure (client omits the key when `title is None`, so `"title" not in model_fields_set`, so
  `preserve()`; every leg already correct individually, the gap was composition), actual `1 passed`,
  match on all three fields. The obvious mutation — `document_dtos.py:55-56`, absent→`clear()` —
  **survived: 14 passed, 1 skipped**, verified with the mutated line confirmed present inside the
  running container before believing it.
  WHY IT SURVIVED, and this is worth more than the row: **`clear()` is unmapped today.**
  `document_storage.py:_update_values` asks only `carries_a_value()`, which is `False` for `clear()`
  AND for `preserve()`, so an erasure falls into the omit branch and no-ops — self-documented at
  `document_storage.py:167-170` and owned by the routed `adapters-discovery (b)` step. `clear()` and
  `preserve()` are behaviourally the SAME VALUE right now, so no mutation of `title_update()` alone
  can be observed end to end, and any future work that "verifies" the erasure fix through the DTO
  alone is verifying nothing.
  So the honest mutation is the charter's own phrase — the day the erasure ships — BOTH legs at once
  (DTO absent→`clear()` plus a storage leg that actually SETs `title = NULL`): **1 FAILED, 13 passed,
  1 skipped**, the single failure being this row. Every other row survives: they all send the key, so
  none can see an absent-key regression. Reverted, container rebuilt, baseline re-confirmed.
  A FALSE COMMENT WAS LOAD-BEARING, caught by red-agent and confirmed at runtime by `/test-review`
  with a throwaway probe: `document_blank_title_save_statements.py:72-76` claimed the stored title is
  "absent from the API — `DocumentResponseDto` exposes no title field, so no endpoint returns it".
  The PUT save response carries all NINE keys including `title`, populated verbatim. The claim split:
  TRUE that the RE-READ cannot see it (because `GetDocumentResponseDto` is a deliberately separate
  read shape — the comment named the wrong DTO), FALSE that no endpoint returns it (`document_dtos.py:108`
  declares it, `:126` populates it, all three write routes return it). The falsehood was what justified
  observing the title ONLY through a percent-encoded export header, while the step already held a
  response containing the title verbatim and threw it away.
  `/test-review` therefore rewrote the observation channel: new Statements class
  `document_content_only_save_statements.py` (123) with `assert_content_only_save_preserved_the_title()`
  pinning the FULL nine-field save shape — `title` directly and verbatim, plus content, version,
  document_id, document_type, status, generation_id, and the two timestamps by presence. It closed two
  further gaps: the version pin was a load-bearing behaviour assertion buried inside a `given_*` and
  invisible to the test class (which advertised two Then clauses and asserted one), and
  `CONTENT_ONLY_SAVE_CONTENT` was written to the wire and never observed, though its own comment argued
  the distinct body existed so a refused save could not masquerade as success. The split was FORCED:
  asserting in place took the file to 205 of 200. `document_blank_title_save_statements.py` reverted to
  3.2-only scope (116) with the false comment corrected.
  One correction to the recorded evidence, measured rather than inherited: under the two-legged mutation
  the row now fails on the DIRECT title pin (`'title': None` vs the Cyrillic) rather than on the export
  header — it trips earlier and reports the wiped title with no percent-encoding in the way.
  Marker: class-level `@pytest.mark.skip(reason="RED: ...")` per the sibling convention
  (`test_document_page_settings_read_acceptance.py:6`), reason worded to say explicitly it is NOT a
  failure claim. Final: **13 passed, 2 skipped** in `tests/backend/documents/`.
  ENVIRONMENT, again: mid-review `infra-backend-1` was replaced with a container built from an old
  commit carrying no `/export` route at all, failing 13 unrelated tests. Rebuilt via
  `infra/docker-compose.yml`. Not this session's doing — a parallel session is rebuilding into the same
  container names.
  HANDED TO `/refactor`: duplicated arrange between the two `given_*` rows, now across two files (a
  shared `_save_over_the_stored_title(...)` on the common parent collapses it) — left deliberately,
  since extracting into `DocumentExportFilenameStatements` touches 3.1/3.2's committed rows.
  A GENUINE REMAINING GAP, not a deferred assertion: scenario **3.2's** blank-title row can now pin the
  title directly off its own save response too — the same false comment was suppressing that.
  `/test-review` confined itself to this uncommitted row rather than silently restrengthening a
  committed scenario. Also noted, off this row's path: `export_envelope.py:88-92` uses
  `content_disposition is not None and ...startswith("attachment")`, the one loose matcher in the
  inherited kit.)
- [x] green-acceptance (premortem: a content-only save must leave the stored title alone, end to end)
  **Marker removed, nothing else touched** — the only edit was deleting the class-level
  `@pytest.mark.skip` and its now-unused `import pytest` from
  `test_content_only_save_acceptance.py`. No production code, no Statements change; the row was
  chartered GREEN on arrival and arrived green: **14 passed, 1 skipped** in
  `tests/backend/documents/` (was 13 passed, 2 skipped with the marker on).
  **Correction, caught by agent-review on `586e4df7` and verified:** the sentence first written here
  named the remaining skip wrongly. The only skip left in `tests/backend/documents/` is
  `test_document_page_settings_read_acceptance.py:6`, whose reason is a different defect —
  `GET /documents/{id}` carries no `page_settings` field. The parked roundtrip RED over
  `model_fields_set` is a **backend unit** test (`test_save_document_request_dto_roundtrip.py`), not an
  acceptance row, so it was never in this count at all. Line 1090, written by the previous unit, had it
  right by path; this line overwrote a correct claim with a wrong one. Two false comments in three work
  units, both load-bearing for what a resumer does next — the pattern is now itself worth naming.
  Worth restating plainly, because it is what this row's value rests on: a green here proves the
  absent-title path is correct in COMPOSITION today, not that the composition is guarded against the
  erasure work. `clear()` is still unmapped, so `title_update()`'s two no-value branches remain the
  same value end to end; the mutation that would make this row fail needs BOTH legs, and that pair is
  exactly the forecast the `adapters-discovery (b)` work will make real.
  `/refactor` on `65c94c8a` extracted the duplicated ASSERTION mechanics — both statements files
  hand-rolled the same guard (`is not None` → `status_code == 200` → `body or {}`) and the same field
  pin, verbatim in shape, differing only in the noun naming the call. New plain-function module
  `acceptance/statements/document_body_assertions.py` (60), mirroring `setup_assertions.py` /
  `export_envelope.py` rather than sitting on the parent, whose charter is filename derivation.
  `document_content_only_save_statements.py` 123→110, `document_blank_title_save_statements.py`
  116→101. Net **+32 lines** overall and said so honestly: the logic shrank ~28, the shared rationale
  is now documented once. A THIRD copy of the idiom lives at `document_page_settings_read_statements.py:139,167`
  — left alone (different scenario, committed row, 195/200). Verified the extracted assertions still
  FIRE: all four failure modes trip with faithful messages, including the wiped-title case. 13 passed,
  2 skipped unchanged; re-run with the skip stripped via a throwaway plugin gives 14 passed, 1 skipped.
  `/refactor` DECLINED the handed `_save_over_the_stored_title(...)` extraction: the shared arrange is
  already extracted (both rows call `_document_carrying_the_cyrillic_title()` and `_export_as_pdf()`),
  what remains is a two-line pairing whose args differ and whose post-save behaviour diverges, so
  collapsing it needs a 3-param helper threading content/title/response to save ~6 lines while touching
  3.1/3.2's committed rows. Also declined `export_envelope.py`'s loose matcher as out of scope: it
  belongs to `assert_export_attachment`, whose docstring charters the looseness for rows where the
  filename is not part of the scenario, and tightening it would change what two committed 3.x rows
  assert — a behaviour change to someone else's rows inside a RED unit.
- [x] red-acceptance (BOTH review passes on `65c94c8a`, converging as their top finding: **the row's
  ABSENT-key identity rests on one line of shared client code that nothing asserts.**
  `acceptance/clients/application/application_client.py:127-129` builds the payload and omits `title`
  only when it `is not None`; three Statements call it, and no test anywhere pins the body it
  produces. A "simplify" pass writing `payload = {"content": ..., "version": ..., "title": title}` is
  invisible TODAY — because `clear()` is unmapped, both shapes no-op identically — and silently
  converts this row from the absent row into the null row. The statements file names the distinction
  (`document_content_only_save_statements.py:64-66`) in a COMMENT, and this same work unit found a
  load-bearing comment that was simply false. The failure lands at the worst moment: once `clear()`
  maps, the red points at the arm that just shipped, not at the client that drifted three weeks
  earlier. Test: assert `"title" not in payload` for the `title=None` call and `"title" in payload`
  for a titled call.
  SECOND HALF of the same finding, agent-review #1: the explicit-`null` branch of `title_update()` is
  UNREACHABLE from acceptance at all — the client collapses absent and null onto one wire shape, so
  the row that is supposed to be THE composition guard for `title_update()` guards one of its two
  no-value branches. Needs a client affordance for an explicit-null payload (a sentinel distinct from
  `None`) plus a row pinning that null clears and absent does not. Sequence this AFTER
  `adapters-discovery (b)` maps `clear()` — until then the two branches are the same value and the
  row cannot discriminate.)
  **DONE. Only the FIRST half shipped** — the client-payload pin. The second half (the explicit-null
  sentinel) stays chartered and stays sequenced after `adapters-discovery (b)`; it was not touched.
  Two new rows in `test_save_document_payload_shape.py` (77) over a `RecordingApplicationClient` (104),
  driven by `document_save_payload_statements.py` (119). No backend needed and none used: the recorder
  captures the request the client builds before it leaves the process.
  TWO methods, not one, and the asymmetry is the point — each kills a mutation the other survives:
  the chartered `{"content":…, "version":…, "title": title}` simplify trips only the omission row;
  dropping `title` unconditionally trips only the titled row. A single omission assertion is satisfied
  by a client that never sends a title at all, which would surface as failures in the export-filename
  rows three files away.
  NO SKIP MARKER, deliberately, and the reasoning is the one recorded three rows down under "guard the
  RED markers themselves": there is no paired `green-acceptance` for this row, so a marker added here
  would never be removed — exactly the defect that step exists to guard. Same call, same reason, as
  `test_wire_shape_key_fence_leg_guard_preemption.py:51`.
  `/test-review` overruled the recorder's MECHANISM while keeping its layer: "in-package access" to
  `ApplicationClient._client` is not a thing in Python — `_client` is private to the CLASS and
  co-location grants nothing but readability. Now a subclass rebinding `self._client` after
  `super().__init__()`, which is the route the language actually sanctions, and which also deleted the
  `application_client` property and the train wreck it forced on the Statements. The rename coupling
  is real and now asserted: `__init__` checks `hasattr(self, "_client")` with a message naming it.
  It also closed two holes the row would have shipped with. The recorder's `assert self._recorded_bodies`
  was a non-empty check on a value the test fully determines (one `given_*` = one dispatch), so a retry
  or a double dispatch was invisible behind a read of `[-1]` — now `len(requests) == DISPATCHES_PER_SAVE`.
  And `_record` answered every request regardless of method or path while the assertions keyed off
  position, so nothing proved the asserted body belonged to the SAVE — the recorder now carries
  `method`/`path` on a frozen `RecordedRequest` and pins `PUT /api/v1/documents/{id}`, a URL that was
  unasserted anywhere on the client side. The three per-field assertions per method collapsed into one
  whole-body equality (the titled arm had been asserting only `title`'s value, leaving `content` and
  `version` at key-presence, so a client mangling content in the titled path passed); the null-vs-absent
  diagnostic moved into the equality's failure message rather than being lost.
  `@pytest.mark.backend` on a row that needs no backend: UPHELD by `/test-review`. `pytest.ini`
  registers only `backend`/`frontend`, the suite runs `-m backend`, so unmarked the row is collected by
  no standard command — the same silent non-execution a stale skip causes. It deliberately does NOT
  subclass `AbstractBackendTest`, whose docstring promises a real running app; the deviation is
  signposted in the docstring and by the filename dropping the `_acceptance` suffix its siblings carry.
  Suite: **16 passed, 1 skipped** (was 14/1; the +2 are these rows). Mutation evidence re-proven after
  the assertion rewrite, since collapsing to whole-body equality could have moved which row fires.
  `/refactor` on `1228fd65`: ONE change, five declines. Applied — `document_export_fixtures.py`'s
  module docstring enumerated five fixtures while the module registers eight; this commit's third save
  fixture tipped it past self-description. It now enumerates both groups and states on the record WHY
  saves live in an export-named module (save rows set up the stored title the export-filename rows
  assert). 74→83; `conftest.py` untouched at 198. Agent-review flagged the same staleness
  independently as its finding #5 — already closed by the time the verdict arrived.
  DECLINED, each for a reason worth not re-litigating: splitting the three save fixtures into
  `document_save_fixtures.py` is blocked by the CAP, not by taste — the split removes 3 names from
  conftest's imports and adds ~7, a net +4 on a file at 198/200, and this very commit had to strip
  three trailing blank lines to fit one import line; landing it requires splitting `conftest.py`
  itself, which touches every scenario's wiring. Recorded as cap-blocked, to be revisited whenever
  conftest is next split. Renaming `document_export_fixtures.py` → `document_fixtures.py` fixes the
  naming half at zero line cost, but the misnomer PREDATES this commit and the rename invalidates
  every progress note and journey summary citing the path — and this file cites paths heavily; the
  corrected docstring carries the information instead. A `recording_application_client` fixture:
  one consumer, +5 lines, speculative reuse that does not exist. `_assert_body_is(expected, why)`:
  the two method bodies are two statements each and the only varying part is the bespoke failure
  message that IS the load-bearing content. `DRAFT_STATUS` pull-up: the second copy lives in 3.2's
  committed file, the same fence already recorded twice above. Sharing `CONTENT_ON_THE_WIRE` with
  2.1's content constant: declined deliberately — the line-27 comment states the match is intentional
  mimicry, not shared identity, and importing would let a change to 2.1's constant silently retarget
  this row. Full acceptance suite collects clean (112 tests, no import errors); 16 passed, 1 skipped
  unchanged.
- [x] red-acceptance (agent-review #2 and #3 on `65c94c8a`, both about claims the code does not keep.
  (a) `assert_content_only_save_preserved_the_title` compares `{k: body.get(k) for k in expected} ==
  expected` plus a `<=` on the timestamps — two SUBSET checks, while the comment argues "an omitted
  key is an unasserted key" and pins `generation_id` specifically to make the comparison total. A
  TENTH key appearing on the write response — a leaked internal field, a mistakenly widened DTO —
  passes silently. `body.keys() == set(expected) | {"created_at","updated_at"}` is what the comment
  claims. The blank-title sibling has the same shape, so this is a convention, not a slip; fix both.
  **RECONFIRMED INDEPENDENTLY on `586e4df7`: both review passes converged on this same step as their
  top finding, now against the EXTRACTED `assert_document_body`** — `/refactor` moved the two subset
  checks into one place without tightening either, so the looseness is now a single shared decision
  rather than a duplicated one. Premortem's incident makes the cost concrete: this row is, since the
  marker came off, the only black-box guard on the PUT write shape (the blank-title sibling observes
  through `GetDocumentResponseDto`, a different shape), so a leaked `owner_id`/`share_token` on the save
  response ships green.
  THIRD PART, genuinely new (agent-review on `586e4df7`): `MANUAL_DOCUMENT_GENERATION_ID = None`, and
  `body.get(key)` returns `None` for an ABSENT key — so that one pin cannot tell a null value from a
  missing key, and its own comment ("an omitted key is an unasserted key") is false for exactly the
  field it annotates. `generation_id` could vanish from the response entirely and this row stays green.
  The sting is the scenario's own subject: 2.1 exists to distinguish absent from null, and asserts one
  of its fields in a way that conflates them. One fix closes all three parts —
  `assert expected.keys() <= body.keys()` alongside the value comparison, plus the exact key-set
  equality above — and makes the comment true.
  (b) `assert_blank_title_save_persisted_the_document` still carries `# created_at/updated_at are the
  only remaining response fields` — `GetDocumentResponseDto` declares EIGHT keys including
  `page_settings` (`get_document_response_dto.py:65`), which is neither pinned nor mentioned. The
  whole point of the block this commit rewrote was correcting a false comment that had been
  load-bearing; the adjacent falsehood in the same method deserves the same treatment.
  Minor, recorded: `DRAFT_STATUS` is copy-duplicated between the two sibling statement modules with no
  note, unlike `VERSION_AFTER_CONTENT_ONLY_SAVE` whose duplication is deliberately argued.)
  **DONE.** All three parts of (a) and part (b) shipped: `assert_document_body` now compares the key
  set for EQUALITY first (`expected.keys() | TIMESTAMP_FIELDS`) and reads values with `body[key]`, so
  a key pinned to `None` asserts PRESENT-AND-NULL — the absent-vs-null conflation 2.1 exists to
  prevent. `page_settings` is pinned null on the read shape and the false "only remaining response
  fields" comment is gone. RED shown by mutation, not by a green suite: probe A (`generation_id`
  deleted from the DTO — arrived accidentally, the compose file gives the backend no source mount so
  a 39-minute-old image still carried the previous session's deletion) and probe B (`page_settings`
  pin dropped) both went red at `document_body_assertions.py:66` with the predicted message,
  character-identical for B. Replaying both guard versions against probe A's recorded wire body:
  OLD green `True`, NEW green `False`. `/test-review` then found the tightening stopped one field
  short — `TIMESTAMP_FIELDS` were merged into the key union and nothing else, so the stamps were
  key-presence-only, weaker than a non-null check, against a repo standard set two scenarios earlier
  (`document_page_settings_read_statements.py:145-178`). Added `assert_document_timestamps` (window
  bound, `created_at <= updated_at`) and `assert_save_advanced_the_update_stamp` (strict `>`, save
  rows only — the one assertion a short-circuiting green cannot fake). It also removed
  `_assert_setup_save_succeeded` from 3.2's arrange: that save is 3.2's ACT, and reporting it as
  broken setup contradicted the sibling's own stated convention; replaced by
  `_assert_the_save_returned_the_surviving_title` pinning the full 9-key write shape — a PRIVATE
  helper called from inside `assert_blank_title_save_persisted_the_document`, not a step the test
  class names (this line said "named Then step" and agent-review caught it as a false claim about
  the very nesting convention the block argues for). It pins `title` off the save response —
  3.2's central claim previously rested on the export header alone.
  CARRIED, refactor-scope, not folded as steps: `DRAFT_STATUS` is duplicated THREE ways (a third
  site, `document_page_settings_read_statements.py:17`, joined since this block was written); the
  `document_body_assertions.py:12-14` adoption deferral has now survived a cycle and that row still
  duplicates the key-set-equality pair verbatim at its lines 124-142; and
  `_assert_setup_save_succeeded` never pins `title` on the title-bearing setup save it guards.
- [~] red-acceptance (premortem CREDIBLE on `1228fd65`: **the payload guard shipped with a hole one
  value wide, and the value is the one scenario 3.2 owns.** `application_client.py` builds the payload
  with `if title is not None`. The tidy-up that turns it into `if title:` is MORE plausible than the
  dict-literal simplify the row was written to kill, and BOTH new rows survive it: `None` still
  omitted, a Cyrillic title still sent. What changes is `title=""` — the request silently drops from
  `{"title": ""}` to key-absent. Not hypothetical: `document_blank_title_save_statements.py:57-64`
  calls `save_document(..., title=blank_title)` with empty/whitespace-only strings, and 3.2's entire
  premise is that a PRESENT but blank title reads as no-title-intent. Under `if title:` 3.2's request
  becomes byte-identical to 2.1's, so 3.2 stops testing its own premise and starts re-testing 2.1's —
  and stays green, because both shapes preserve. The identical failure class this work unit exists to
  foreclose, one value over, and it lands the moment `clear()` maps. Test: a third row,
  `given_a_save_carrying_a_blank_title()` over `save_document(title="")`, whole-body equality against
  `{**NO_TITLE_INTENT_BODY, "title": ""}`. Nothing in the repo goes RED on
  `if title is not None` → `if title:` today.)
- [ ] red-acceptance (agent-review #1 on `84e47dff`, and the finding is that the pin I just argued
  hardest for discriminates nothing: **`assert_save_advanced_the_update_stamp` cannot detect the
  refusal it was written to detect.** Its docstring claims "a save that never ran cannot move a clock
  it never read" — true only for a document created and saved exactly once. Neither row is that. Both
  arrange through `_document_carrying_the_cyrillic_title` (`document_export_filename_statements.py:57-70`),
  which performs a title-bearing setup save, and `SaveDocument` stamps `updated_at=self.clock.now()`
  on it — so `updated_at > created_at` is already true BEFORE the act save is issued, at all four call
  sites. A green that accepts the setup save and then refuses the act save passes. The discrimination
  is still carried entirely by the `version` and `content` literals the docstring dismisses as
  fakeable. Fix: capture `updated_at` off the SETUP save's response and assert the act save advanced
  past THAT, not past `created_at`. The commit message and this file both currently record a guard
  the code does not provide.)
- [ ] red-acceptance (premortem CREDIBLE #1 on `84e47dff`, converging with agent-review #2 and with
  the carried duplication note: **the shared kit bounds stamps by a wall-clock age heuristic against
  the wrong clock, and it is now on the path of every caller.** `MAX_STAMP_AGE = 2min` /
  `CLOCK_SKEW_TOLERANCE = 5s` compare the CONTAINER's stamp to the RUNNER's `datetime.now(utc)`, and
  `assert_document_timestamps` fires from inside `assert_document_body`, so one Docker Desktop clock
  drift after a laptop sleep reddens every row at once — including pure shape assertions that have
  nothing to say about time — with a message blaming the backend. The blank-title row is the budget
  risk in the other direction: auth arrange, create, title save, blank save, a PDF render+export and
  a GET all sit inside the 2 minutes, so a cold CI runner reports slowness as a shape defect. And the
  window is weak where it matters: a stamp 110s stale — an `updated_at` wrongly copied from creation —
  passes. The repo solved this two scenarios earlier and this commit did not adopt it:
  `document_page_settings_read_statements.py:145-178` records an ARRANGE window around the call and
  bounds against that, immune to absolute offset. No statement module captures such a bound around a
  SAVE. Note the two copies of the key-set-equality pair have now DIVERGED on exactly this — recorded
  window vs. age heuristic — and the weaker copy is the one on the shared path.)
- [ ] red-acceptance (premortem CREDIBLE #3 on `84e47dff`: **a durable constraint on the write path
  shipped as a test assertion, phrased as an accusation.** `assert_save_advanced_the_update_stamp`
  asserts `updated_at > created_at` STRICTLY and its message hard-codes one reading of equality
  ("created but never actually saved"). The obvious efficiency win — `SaveDocument` skipping the
  UPDATE when content and title are unchanged — turns two rows red with a message that diagnoses a
  broken save, so the engineer reverts working code. The constraint "a save always touches the clock,
  even for an identical payload" is arguably correct but is stated nowhere the backend session reads:
  not in this file, not in the API spec, and in no scenario that would go red on the no-op
  optimization for the RIGHT reason. Either pin it as a product claim or stop asserting it strictly.)
- [ ] red-acceptance (agent-review #3 on `84e47dff`, small and mechanical: `assert_document_timestamps`
  runs TWICE per save body — once from `assert_document_body`'s last line, once from
  `assert_save_advanced_the_update_stamp`'s first — against two different `now` values. A body at the
  `MAX_STAMP_AGE` boundary can pass the first and fail the second, pointing the failure at the wrong
  assertion. Folded here rather than dismissed because the fix falls out of the two findings above.)
- [ ] fix the build-provenance hole (premortem CREDIBLE #2 on `84e47dff`, and it is the one to act on
  first because it invalidates evidence rather than producing noise): `infra/docker-compose.yml` gives
  the backend NO source mount, and **this work unit already got bitten** — probe A's RED came from a
  39-minute-old image still carrying the previous session's DTO deletion, not from the checkout. The
  mechanism runs symmetrically: a stale image serving old-but-correct code greens the suite over a
  broken checkout. `git grep` for `build_sha|git_sha|/version|BUILD_` across `backend/adapters/rest`
  and `acceptance` returns NOTHING, so every acceptance verdict in this repo — red and green alike —
  is unattributed to a commit. Cheap fix: one build-identity field on the health route, one assert in
  the suite's entry fixture pinning it to the checkout's HEAD.
- [ ] red-acceptance (BOTH passes on `1228fd65`, same gap class one field over: **the `Authorization`
  header is client-manufactured and unasserted anywhere in the repo.** `RecordedRequest` carries
  `method`/`path`/`body` and the commit's own argument for pinning the save URL — "unasserted anywhere
  on the client side" — applies verbatim to `headers={"Authorization": f"Bearer {access_token}"}`.
  Premotem rates the incident REMOTE (a dropped auth header fails loudly as 401s across every document
  row, not silently), which is why this is its own step rather than folded into the row above: the
  recorder must grow a `headers` field first, and that is a change to a just-committed file.)
- [ ] fix the recorder's two overclaims (agent-review #1 and #2 on `1228fd65`, both in
  `recording_application_client.py`, both the shape this scenario keeps rediscovering).
  (a) `_record` unconditionally does `body=json.loads(request.content)`, but `MockTransport` answers
  EVERY request through this client and the class advertises itself generally, with a public
  `recorded_requests`. The first Statements that reuses it for `get_document` or `export_document` —
  GET, empty body — gets a `JSONDecodeError` raised from inside httpx's transport stack, several
  layers from its cause. Nothing tests a non-PUT through this transport.
  (b) The comment says the stub response "only has to be well-formed enough that the client's own
  parsing and its DTO construction run exactly as they do against the real backend", and then answers
  `httpx.Response(200, json={})`. `{}` is NOT the real save response. Invisible only because
  `SaveDocumentResponseDto` is a bare frozen dataclass that stores `body` without reading it — the day
  `save_document` parses a field out of it (the new `version` for the CAS loop is the obvious
  candidate) the recorder feeds it an empty body and the parity claim is false. Third load-bearing
  comment in this scenario to be measured against the code rather than trusted.)
- [ ] tighten the rename guard (agent-review #3 on `1228fd65`): `assert hasattr(self, "_client")`
  proves an attribute of that NAME exists, not that `save_document` dispatches through it. If
  `ApplicationClient` keeps `_client` but routes document calls through a different transport
  attribute, the assert passes, the recorder rebinds a dead attribute, and the PUT goes to a real
  localhost backend with a bogus id and token. The failure is still loud — but it arrives from
  `len(requests) == DISPATCHES_PER_SAVE` seeing 0, so the inline comment ("Without this, ... every
  request would go to a real localhost backend") credits the wrong guard. Either narrow the comment to
  what the assert proves, or make the assert prove dispatch.
- [ ] make the RED evidence reproducible (agent-review #4 on `1228fd65`, and it applies to every
  green-on-arrival row this scenario has shipped): both new rows pass at HEAD, and the justification is
  a MEASURED MUTATION described in prose in three places — commit body, this file, the class docstring
  — and executable nowhere. No mutation config, no recorded command, nothing that re-verifies it after
  the next edit. The row's own thesis is that a claim surviving only in prose is a claim that rots,
  and its red evidence now survives only in prose. Related to, and probably solvable with, the
  "guard the RED markers themselves" step below.
- [ ] unpark the roundtrip RED (premortem finding 2 on `7b0a9c51`, **re-raised and sharpened by
  premortem on `65c94c8a` into a hard ORDERING CONSTRAINT: this must land BEFORE
  `adapters-discovery (b)` maps the erasure arm.** The moment `SET title = NULL` ships, `clear()`
  becomes destructive — and `document_dtos.py:55` manufactures a spurious `clear()` from an absent
  title under two ordinary spellings, including `SaveDocumentRequestDto(content='c', version=1,
  title=None)`, the field's own declared default and the safest-LOOKING spelling. The one row in the
  repo that goes red on that is switched off. This commit's new guard does NOT backstop it: it covers
  the wire-absent path only and cannot see a DTO reconstructed in-process. Today's dormancy is an
  accident of `clear()` no-opping; the work unit that removes the accident is the next-but-one step,
  and until this row is written nothing sequences them. Incident: a title vanishes on a routine
  content save the user never asked to clear, overwritten with NULL in Postgres, no history row.)
- [ ] guard the RED markers themselves (premortem finding 3 on `65c94c8a`): nothing fails when a
  RED-phase skip outlives its work unit. `test_content_only_save_acceptance.py:6-12` carries a
  class-level skip whose own reason says the row is GREEN on arrival, so it has never been observed
  executing in the suite — only under a hand-applied mutation. The repo carries 7 skip markers, one
  parked over a live production defect, so the pattern is demonstrated rather than hypothetical. The
  suite reports "13 passed, 2 skipped" every run and nobody reads the second number. Note the sibling
  that got this right: `test_wire_shape_key_fence_leg_guard_preemption.py:51` explicitly DECLINES a
  marker on the identical reasoning. Guard: a skip inventory pinned by exact equality, so an
  un-removed marker fails the suite rather than shrinking it.
  (Original charter, unchanged:) `test_save_document_request_dto_roundtrip.py:7` carries a class-level `@pytest.mark.skip`
  over both legs whose reason names a LIVE defect in production code (`document_dtos.py:55` reads
  `model_fields_set`, which neither `model_dump()`/`model_validate()` nor the JSON pair round-trips,
  so an absent title reparses as `clear()` on BOTH legs). This is not a coverage gap — the guard is
  written and switched off, and it is two of this suite's four skips. Re-check its docstring premise
  while unparking: it says "the incident it forecloses is the day someone adds a save queue", and a
  save queue already exists (`acceptance/statements/frontend/generation/manual_editor_save_queue_
  statements.py`). TypeScript, so it does not round-trip this Python DTO and the claim is still
  literally true — but the distance is shorter than when it was written; re-grep, don't inherit.
- [x] red-adapter rest (coverage: refusal co-occurring with the other two faults). The partition's
  arms are pinned INDIVIDUALLY but never in combination, and coverage cannot see the gap:
  `wire_shape_key_fence.py` reports **100% line and 100% branch** (17 stmts, 6 branches) because
  every `if` gets both outcomes across the five rows — combinations are invisible to coverage.py.
  Two arms have no row: (a) the refusal firing TOGETHER with the generic dropped clause — no fixture
  omits `title` and another declared field at once, so nothing pins their ORDER in the message or
  that both survive the partition; (b) the refusal firing together with `undeclared` — row 4 pins
  `'; and '` only for dropped+undeclared, so a mutation that raises the refusal ahead of `faults`
  (the shape this green deliberately rejected) still passes every row. One body closes both:
  `{"__not_a_field__": "x", "version": 1}` → `missing == {"content", "title"}`,
  `undeclared == {"__not_a_field__"}`, message carries refusal + dropped + undeclared with TWO
  `'; and '` joiners, which nothing currently pins. Use `"__not_a_field__"`, not `"note"` — the row
  below already charters that rename. Exact equality, per the class docstring.
  **LANDED GREEN, and the mutation table is what earns it.** The helper was already correct — the gap
  was in the TESTS — so predicting a failure would have been predicting a lie. Predicted no-failure
  with the exact three-clause message; actual, byte-identical, `2 passed`. The two survivors the
  premortem on `f935be3c` measured are now DEAD, both attributable to this row BY NAME, and both
  re-run independently by `/test-review` rather than taken on report:
  - refusal `faults.append` moved AFTER dropped + undeclared: 16 passed → **1 failed, 16 passed**
  - refusal suppressed whenever another fault co-occurs: 16 passed → **1 failed, 16 passed**
  - `dropped = missing` (control): 1 failed → 2 failed
  No skip marker: a marker asserts "this fails now", and marking a row that passed on arrival parks a
  live coverage guard for no red period — and would have suppressed the very kills that earn its
  place. Fourth time this scenario has faced that call.
  PLACEMENT — the refusal file, not the model-agnostic sibling, and test-review found the stronger
  ground: the fixture drops `title`, so the expected message OPENS with the six-line refusal clause
  naming `TestSaveDocumentRequestDtoWireShape` and its file. Putting it in the sibling drags that
  title-specific wording and cross-file class coupling straight back into the file that expelled it.
  The cap forbids the alternative independently — the agnostic file was at **170**, not the 165 this
  charter assumed, so a ~55-line row would have pushed it to ~225.
  `/test-review` found 0 assertion violations and 6 docstring-accuracy ones, all fixed, and it caught
  a lint regression by RE-RUNNING ruff rather than assuming: a corrected line hit 108 chars. The
  substantive one is a fact this scenario has been miscounting — "named and acted on TWICE" was an
  undercount; there are three distinct acted-on instances (`TestSaveDocumentRequestDtoFromALiteralBody`,
  `..._wire_shape_control.py:20`, `..._blank_control.py:14`), and the sibling file saying "three
  times" was right while this one said two.
  THE THREE STALE CLAIMS, resolved: (1) the false preemption claim is STRUCK and replaced with an
  explicit statement that the coverage is a separate chartered step and must not be read as closed;
  (2) the "fourth row's subject" pointer now names the refusal file; (3) "108 tests green" is
  deliberately NOT re-stamped to 114 — the measurement was never taken against a 114-test suite and a
  fresh number implies a fresh mutation run nobody performed. Converted to explicit past tense with
  three disambiguators. test-review's verdict: right call, re-measure rather than re-stamp if that
  evidence is ever needed as current.
  ROT ACCEPTED DELIBERATELY, recorded so nobody "fixes" it: the expected literal hardcodes the
  sibling class name and filename. Interpolating `TestSaveDocumentRequestDtoWireShape.__name__` would
  compute the expected value from the same source the subject reads, passing under ANY rename —
  strictly weaker than the literal. Naming-coupling, not assertion-looseness.
  **CONFIRMED STILL OPEN by both agents independently:** the leg guard can be moved below `faults` and
  the suite stays green (17 passed, 4 skipped under that mutant). Now DOCUMENTED as open, still
  UNCOVERED. That is the next row.)
- [S] green-adapter rest (coverage: refusal co-occurring with the other two faults) — SKIPPED as a
  step in substance: nothing to implement. The helper already emitted the correct three-clause
  message in the correct order; the red half was a coverage guard over already-correct code, proven
  by two mutants that were alive before it and dead after. A green commit here would be a no-op.
- [x] red-adapter rest (coverage: leg guard preempts a genuinely broken body). The guard row ships
  with a WELL-FORMED body, so it pins the reject path but NOT the preemption its own comment
  (lines 100-108) argues for at length: with both fault legs quiet the message could only have come
  from the guard either way. A body that is broken AND carries a typo'd leg —
  `assert_body_keys_track_the_model({"version": 1}, "dmped JSON")` — must raise the leg-label
  message, not a fault message naming a leg that does not exist. Moving the guard below `faults`
  leaves all six current rows of the two sibling files green (four in `test_wire_shape_key_fence.py`,
  two in the title-refusal file) — miscounted as five until `/test-review` counted them.
  **LANDED GREEN ON ARRIVAL, and the mutation is what earns it** — fifth time this scenario has faced
  that call. The guard order was already correct, so predicting a failure would have been predicting
  a lie; predicted no-failure with the exact leg-label message, actual byte-identical, 18 passed /
  4 skipped. No skip marker: a marker asserts "this fails now", and parking a live mutation-killing
  row behind one buys no red period and suppresses the very kill that earns its place.
  THE MUTANT IS DEAD, re-run rather than taken on report: guard moved AFTER `assert not faults` →
  **1 failed, 17 passed, 4 skipped**, and the one failure is the new row. The other 17 — including
  the existing well-formed-body guard row — survive the mutant, which is the empirical proof that
  the gap the charter named was real and that this row alone closes it. Reverted, 18 passed.
  A REAL TRAP, recorded so the next mutation run does not fall in it: "below `faults`" means below
  the `assert not faults`, NOT below the `faults.append` calls. The first attempt moved the guard
  between the appends and the assert and the whole suite stayed green — the legs only BUILD the list
  there, so the guard still ran first. That reads as the new row failing to bite when it is really
  the mutant failing to mutate. Guard-versus-RAISE is the order that matters, not guard-versus-list.
  PLACEMENT — its own file, `test_wire_shape_key_fence_leg_guard_preemption.py` (82 lines). The cap
  forced the timing: the sibling that owns the guard's wording is at **172** of 200, so the row could
  not sit beside the row it extends. The seam is subject independently — the siblings assert WHAT the
  fence says, this asserts WHICH of two things it says when both are armed. Not the refusal file
  either: the fixture omits `title`, but the expected message carries none of the refusal's
  title-specific wording and no cross-file class name, which is the entire point of the row.
- [S] green-adapter rest (coverage: leg guard preempts a genuinely broken body) — SKIPPED as a step
  in substance, on the same reasoning as the identical case one unit above: the guard order was
  already correct, so the red half was a coverage guard over already-correct code and a green commit
  here would be a no-op. Marker corrected from `[ ]` by agent-review on `7b0a9c51`, which caught the
  narrative ("LANDED GREEN ON ARRIVAL") contradicting the marker it left.
  `/refactor` on that commit applied the one finding `/test-review` handed it and MEASURED it first
  rather than taking it on faith: renaming `title` to `heading` on the model and calling the fence
  with a `content`+`version` body emits `['heading'] was declared on the model and dropped by the
  serializer` — the generic dropped-field wording, on the one field the helper's own comment says
  must never be called "dropped", because that wording is what invites a green emitting
  `"title": null`, which `title_update()` maps to `TitleUpdate.clear()`. The refusal branch does not
  fail loudly when it goes stale; it degrades silently into the message it exists to prevent. Closed
  with an import-time guard asserting `"title" in SaveDocumentRequestDto.model_fields`, mirroring the
  leg guard's `get_args(WireLeg)` check — import-time because it is a static fact about the class,
  and with an explicit message because this module is not assert-rewritten. Verified to bite under
  the simulated rename. 115 passed, 4 skipped. `wire_shape_key_fence.py` is now 187/200 — the next
  comment block added to it forces a split, not an insertion.
  DECLINED by `/refactor`: extracting the twice-spelled `"title"` literal into a constant — one guard
  covers both spellings, and the refusal wording is pinned by exact equality in the siblings, so
  interpolation would add a layer between the message and its pin for nothing.
  STANDING FRAGILITY, named by `/refactor` after tripping it: this file family cites siblings by hard
  line number (the new row's `:12` cited "lines 100-108", now 131-139, and was corrected), so every
  insertion into `wire_shape_key_fence.py` silently rots the pointers. Kept the convention — changing
  it is outside a refactor pass — but it costs a fix-up every time.
  agent-review finding 3, RECORDED not chartered: `assert_body_keys_track_the_model(body, "dmped
  JSON")` type-checks today only because of the resolution hole the helper documents at
  `wire_shape_key_fence.py:8-21`. The helper names the fix as a live intention (`mypy_path` reorder,
  or move the helper), and doing it turns this call and the sibling at `test_wire_shape_key_fence.py`
  into `arg-type` errors. This unit took that from one site to two with nothing recording that the
  two rows testing the RUN-TIME guard are exactly the rows that must be exempted. Whoever moves the
  file discovers it as a red mypy run.
  premortem finding 3, RECORDED: the helper's comment claims the leg label catches "a typo **or a
  swapped label**". The run-time guard catches the typo half only — `"dumped"` passed at a JSON call
  site is in `get_args`, sails through, and misnames the leg in the one report anybody reads. The
  swap half is structurally unreachable from inside the helper and rests on call-site review; the
  honest close is a correction to that comment, not a test.
- [ ] red-adapter rest (both review passes on `b1991508`, converging as their top finding: **two LIVE
  rows now certify the erasure body as key-set-clean.** `test_wire_shape_key_fence.py` rows 1 and 3
  use `{"title": None, "version": 1}` (and `+ {"note": "spurious"}`) with `['content']` pinned by
  exact equality as the ONLY fault. Read as a contract — the same reading that condemned the fixtures
  these replaced — a body carrying `title: None` is asserted to be well-formed on the key axis, by
  name, in rows nobody skips. Fix: re-fixture to `{"title": "kept", "version": 1}`, which drops
  `content` just as unambiguously and makes no claim about the null spelling. Cheap and behavior-
  neutral: `title` is present either way, so the pinned messages stay byte-exact and green is
  unaffected. That is exactly why it must be done deliberately — nothing will ever fail to remind
  anyone.
  The load-bearing half is premortem #3, and it outlives the fixture fix: after green the fence's
  opinion on `title` is **absent → refuse, present-and-null → accept silently**. The erasure spelling
  sits in its ACCEPT set, and the 10 live call sites are covered only because each independently
  freezes a whole-body literal — the fence contributes NOTHING to the invariant it is named for.
  So also pin what the fence does when handed the exact erasure body: either it refuses `title: None`
  by name (the fence owns the invariant), or — if key-set-only scope is deliberate, which the
  helper's own docstring implies — a row pinning that the fence is explicitly VALUE-BLIND, with the
  consequence stated: whole-body equality at the call site is the only thing between a title-
  untouched save and `TitleUpdate.clear()`. Sequencing: after the partition green, since the refusal
  branch is what makes the accept set legible.)
- [ ] green-adapter rest (the fence must not certify the erasure body)
- [ ] red-adapter rest (both review passes on `9a7027b2`, three findings that share one root — the
  fence's guards are coupled to the CURRENT shape of `SaveDocumentRequestDto`, and all three break
  on the day someone adds a field. Take them in one unit; splitting them means rewriting the same
  three exact-equality literals three times.
  **(1) The spurious-key fixture uses `"note"` — the exact name the helper reserves as its worked
  example of a future DECLARED field.** `wire_shape_key_fence.py`'s docstring argues its whole
  reason for existing through a measured pydantic run over a field named `note`. If that field is
  ever added, `undeclared` goes empty, the fence does not raise, and
  `test_should_name_a_key_the_body_carries_that_the_model_never_declared` dies as `DID NOT RAISE` —
  losing the spurious-leg guard in the exact event it exists to survive. Loud rather than silent,
  but it reads as "the fence broke" in a commit where attention is on the model change. Rename the
  fixture key to something that can never be a field: `"__not_a_field__"`.
  **(2) All three expected messages freeze the declared set as an unwritten constant.** Add a fourth
  field and test 1's `['title']` becomes `['newfield', 'title']`, AND test 2 — the spurious-ONLY row
  — grows a `missing` clause it was written never to have, so exact equality fails on a row whose
  whole subject is the other leg. Three cryptic string failures land on a developer whose change had
  nothing to do with the fence, and the cheap fix they will reach for is `assert "note" in
  str(failure.value)` — substrings, which by this scenario's own test-review finding do NOT kill a
  mutation mangling the `'; and '` joiner or dropping the `got {body!r}` tail. The guard degrades to
  the shape it was written to beat, permanently. Fix: derive the fault bodies FROM
  `SaveDocumentRequestDto.model_fields` (declared-minus-title, declared-plus-marker) so a model
  change adjusts the fixtures rather than breaking the assertions. Keep exact equality on the
  message — it is the fixtures that should move, not the strictness. If deriving proves to obscure
  the rows, the fallback is one assertion pinning `set(model_fields) == {"content","title","version"}`
  with a message saying UPDATE THE THREE LITERALS BELOW, so the break points at its cause.
  **(3) Nothing pins that the fence is ever CALLED, and `9a7027b2` made deleting the calls SAFER.**
  Remove all 10 `assert_body_keys_track_the_model(...)` lines from the two control files and the
  suite is fully green — `test_wire_shape_key_fence.py` imports the helper directly and passes
  standalone, so the cleanup leaves something that still looks guarded. The helper's own docstring
  concedes "on the CURRENT model it catches nothing the literals miss", which is exactly the
  argument such a cleanup commit would quote. The honest guard is the scenario the fence CLAIMS:
  `pydantic.create_model` over `SaveDocumentRequestDto` with a defaulted extra field plus a
  dict-building `@model_serializer`, asserting the fence fires — converting the docstring's
  measured-once pydantic 2.13.4 probe into a committed test, which is the same gap `9a7027b2` closed
  for the failure path. Note this row also lands the docstring pointer premortem asked for: the
  `['title']`-as-missing literals are PROVISIONAL until the absent-row step above changes what the
  fence considers well-formed.)
- [ ] green-adapter rest (the fence's guards must survive the model growing)
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
