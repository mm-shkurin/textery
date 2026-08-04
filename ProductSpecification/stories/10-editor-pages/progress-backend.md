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
- [~] red-adapter rest (coverage: PUT response asserts version only, not shape)
- [ ] green-adapter rest (coverage: PUT response asserts version only, not shape)
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
