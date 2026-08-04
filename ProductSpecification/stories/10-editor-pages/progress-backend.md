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
- [~] green-adapter rest (premortem: title absent-vs-null via `model_fields_set`; PUT 404)
  Two constraints from agent-review, both checkable: (i) the rest suite must come back **97 passed,
  0 skipped** (restated from 95/0 — the blank row added two parametrized cases). Four marker SITES,
  not three: the class-level one in `test_save_document_title_router.py` plus three method-level
  ones in `test_save_document_router.py`. Nothing fails if green lifts only three — the guard is
  prose, so check the number. (ii) `document_router.py` is at 179 lines and the mapping adds ~8;
  under the 200 cap but with no room for the `_ERROR_CODE_STATUS_MAP`/log work chartered nearby.
  (iii) `if request.title is None` is the ONLY spelling that passes all four rows — the blank arm
  exists to make that true.
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
