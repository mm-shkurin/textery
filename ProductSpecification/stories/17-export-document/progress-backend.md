# Story 17: Export document to PDF / DOCX — Backend Progress

Owns: Backend, Integration, Security, Load, and Infrastructure Scenarios (acceptance
steps stay inline per scenario — they aren't a separable layer). Narrative/decisions/Spec
checklist live in `progress.md`; `ProductSpecification/stories.md` is the cross-file rollup.

Implementation order (per 01_API_Tests.md): prerequisite/format guards → happy path →
filename & encoding → safety (SSRF, deadline, disclosure).

## Backend Scenarios (01_API_Tests.md)

### Scenario 1.1: Export of a non-existent document is refused
- [x] red-acceptance
- [x] design — new `ExportDocument(document_repository)` usecase: `execute(document_id, owner_id)`
  does owner-scoped `find_by_id_and_owner`, returns `Document | None` (no rendering this
  scenario). New route `GET /api/v1/documents/{document_id}/export` with typed
  `document_id: UUID` path param + `Depends(get_current_owner_id)`; `None` →
  `NotFoundException` → sanctioned 404. Absent+foreign collapse to None (owner-scoped SQL).
  Hazard scan (all 8 groups): no open GAP — grp1/2/3/8 clear; grp5 IDOR-foreign owned by
  Sc 1.2 + Security 1.1; grp5 unauth/null-owner guarded by reused story-7
  `get_current_owner_id`; grp5/6 malformed/oversize id guarded by typed UUID param; grp7
  exact-404-body already asserted in red-acceptance; grp4 title-migration owned by Infra
  3.1; grp3 read-after-write owned by Sc 3.5; render seams → rendering/4.2/4.5. No ADR
  (single viable approach, guards reuse established patterns).
- [x] red-usecase
- [x] green-usecase
- [x] adapters-discovery (rest) — Check 1 (ports): [S] `DocumentRepository.find_by_id_and_owner`
  already implemented in db adapter (document_storage.py:49, owner-scoped SQL, returns None for
  absent/foreign); exercised by GetDocument — sufficient for the not-found path. Check 2
  (exceptions): [S] `NotFoundException` already mapped to the sanctioned 404 by the document
  router's existing handler (GET /{id} raises it identically). Check 3 (response shape): rest —
  GAP: no `GET /api/v1/documents/{document_id}/export` route exists, so the acceptance test hits
  Starlette's default 404 body instead of the sanctioned shape. Add the route to document_router
  wiring ExportDocument (typed `document_id: UUID`, `Depends(get_current_owner_id)`, None →
  NotFoundException) → red-adapter rest / green-adapter rest.
- [x] red-adapter rest
- [x] green-adapter rest
- [x] green-acceptance

### Scenario 1.2: Export of another account's document is refused indistinguishably
- [x] red-acceptance — enabled regression guard (already GREEN): a foreign existing document
  and a non-existent id both collapse to the sanctioned 404 byte-for-byte. Asserts full-DTO
  equality of both responses against the sanctioned NOT_FOUND literal (status + parsed body +
  raw bytes + both headers).
- [S] design — no new implementation: indistinguishability is already enforced structurally by
  owner-scoped SQL (`find_by_id_and_owner` filters on owner_id).
- [S] red-usecase — owner-scoped None collapse already built + covered by Scenario 1.1.
- [S] green-usecase — same; zero production files modified for 1.2.
- [S] adapters-discovery — no adapter change; `find_by_id_and_owner` + NotFoundException already
  sufficient (see Scenario 1.1 discovery).
- [x] green-acceptance — test enabled and passing (2 passed), no production change needed.

### Scenario 1.3: An unsupported or missing format is refused
- [x] red-acceptance — RED confirmed live (got 200 placeholder vs expected 422). New contract:
  `INVALID_FORMAT → 422`, body `{error_code:INVALID_FORMAT, message:"The format must be pdf or
  docx."}`. GREEN must (1) add INVALID_FORMAT→422 to _ERROR_CODE_STATUS_MAP in
  exception_handlers.py and (2) validate `format` explicitly (raise ValidationException) — NOT a
  FastAPI enum param (that emits {"detail":[...]}). Test-review verified inline (strict assertions,
  clean placement). NOTE: /refactor + agent-review + premortem NOT run — session limit hit; a
  future session must run them over commit before proceeding.
- [x] design — new domain value object `ExportFormat` (backend/domain/src/document/export_format.py):
  members `pdf`/`docx`; classmethod `parse(value: str | None) -> ExportFormat` raising
  `ValidationException(error_code="INVALID_FORMAT", message="The format must be pdf or docx.")`
  for None/empty/unknown (case-sensitive: only lowercase `pdf`/`docx` accepted for now).
  Usecase `ExportDocument.execute` gains a `format` arg and calls `ExportFormat.parse(format)`
  **before** the owner-scoped fetch — a bad format is a 422 that depends only on the string, so
  it discloses nothing about the target document (no IDOR leak: valid-format+foreign still → 404,
  invalid-format+foreign → 422 regardless of existence). Rest route forwards `format` to the
  usecase and adds `"INVALID_FORMAT": 422` to `_ERROR_CODE_STATUS_MAP` in exception_handlers.py;
  the existing `validation_exception_handler` then emits the canonical `{error_code, message}`
  body at 422 — same reuse path as page.py INVALID_LIMIT and current_owner UNAUTHORIZED, no new
  handler. POSITIVE CONTROL (from premortem CONCERNS on f219201): red-usecase and green-acceptance
  must each assert a VALID `pdf`/`docx` export is NOT refused with 422 — otherwise a
  refuse-everything guard passes the negative tests tautologically (same gap class Sc 1.2 hardened
  against in a062c5b). Also cover `format=""` (agent-review CONCERNS) in the parse tests.
  No ADR — single viable approach, guards reuse the established ValidationException→handler pattern.
- [x] red-usecase — RED confirmed live: `TypeError: ExportDocument.execute() got an unexpected
  keyword argument 'format'` on all 6 cases (predicted == actual). 6 parametrized cases:
  negatives `xml`/`None`/`""` each assert `error_code == "INVALID_FORMAT"` + exact message
  "The format must be pdf or docx." run against an EMPTY repo (proves the guard fires before the
  fetch — bad format discloses nothing about existence); positive control `pdf`/`docx` asserts
  `found is document` (identity) — the premortem-mandated valid-format control. Sc 1.1's
  none-refusal test updated to pass `format="pdf"` to survive the signature change. test-review:
  no changes — all assertions already strict (exact-equality / identity, no loose validation).
- [x] green-usecase — GREEN at 8 passed (usecase suite 168 passed). New domain VO
  `backend/domain/src/document/export_format.py` (33 lines): `ExportFormat(Enum)` PDF/DOCX with
  `parse(value)` using exact `cls(value)` — no `.lower()`/`.strip()`, so `"PDF"`/`" pdf "` and
  non-str/None raise `ValidationException(INVALID_FORMAT, "The format must be pdf or docx.")`.
  Usecase `execute` gained `format`, calls `ExportFormat.parse` before `find_by_id_and_owner`.
  Router `/export` now forwards its existing `format` query param to `execute` (required-arg
  regression guard — no new behavior; the 422 status mapping is still the adapters-discovery /
  green-adapter rest concern). Coverage: both files 100% stmts+branch, no gaps.
- [x] adapters-discovery (rest) — Check 1 (ports): [S] `DocumentRepository.find_by_id_and_owner`
  already implemented (document_storage.py) and sufficient — the read path is unchanged from
  Sc 1.1. Check 2 (exceptions): rest — GAP: `ExportFormat.parse` raises
  `ValidationException(error_code="INVALID_FORMAT")`, but `_ERROR_CODE_STATUS_MAP` in
  exception_handlers.py has no `INVALID_FORMAT` entry, so `validation_exception_handler` defaults
  it to 400; the acceptance contract (red-acceptance f219201) demands 422. Add `"INVALID_FORMAT":
  422` alongside the existing INVALID_DOCUMENT_TYPE/INVALID_VERSION 422 entries → red-adapter rest
  / green-adapter rest. Check 3 (response shape): [S] the 422 refusal body `{error_code, message}`
  is already produced by the existing `validation_exception_handler`; the success/binary export
  body is deferred to the rendering scenarios (2.x), out of scope for 1.3's refusal path.
- [x] red-adapter rest — RED confirmed live: `assert 400 == 422` (predicted == actual). New test
  `TestInvalidFormatStatusMapping::test_should_map_invalid_format_to_422` in
  test_document_exception_handlers.py, modeled on `TestUnauthorizedStatusMapping`: a route raises
  `ValidationException(INVALID_FORMAT, "The format must be pdf or docx.")` through the real
  `validation_exception_handler`; asserts strict `status_code == 422` + full parsed body
  `{"error_code":"INVALID_FORMAT","message":"The format must be pdf or docx."}`. Currently 400
  (default) — INVALID_FORMAT absent from the map. test-review: target test already strict, no
  change. (Detector also flagged 3 pre-existing loose `not in` leak-guards elsewhere in the file —
  Security-5.1-owned, untouched by this commit, out of scope.)
- [~] green-adapter rest
- [ ] green-acceptance

### Scenario 2.1: A document exports as a valid PDF
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.2: A document exports as a valid DOCX
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.3: An empty document exports to a valid file
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.4: Export does not mutate the document
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: The filename is derived from the title, encoded for Cyrillic
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.2: A document with no title uses a default filename
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.3: A title with header-breaking characters cannot inject into the header
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.4: Multibyte content renders intact
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.5: A save immediately followed by an export reflects the latest content
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.6: A long multibyte title is truncated on a grapheme boundary
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.1: Embedded external URLs do not cause an outbound request
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.2: A pathological document aborts within the render deadline
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.5: An over-limit document cannot drive an unbounded render
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.3: Error bodies expose no internal detail
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.4: A render failure emits an attributable signal
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Integration Scenarios (06_Integration_Tests.md)

### Scenario 1.1: A document exports to a well-formed PDF and DOCX
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.2: Multibyte content survives the render pipeline
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1: The export reflects the latest saved state end to end
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Security Scenarios (05_Security_Tests.md)

### Scenario 1.1: A foreign or absent document is refused indistinguishably
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1: A title cannot inject into the response headers
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: Embedded URLs cause no outbound request
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.1: An invalid format is rejected, never defaulted
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.1: Render errors leak no internal detail
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Load Scenarios (03_Load_Tests.md)

### Scenario 1.1: The export endpoint sustains the configured request rate
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1: Concurrent renders are bounded, not unbounded
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Infrastructure Scenarios (04_Infrastructure_Tests.md)

### Scenario 1.1: Missing native render libraries fail fast at boot
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.2: An unset render-timeout config fails fast at boot
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.3: The render dependencies pass the vulnerability audit
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1: Repeated exports including failures do not leak resources
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: Old code serves documents after the title column lands
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance
