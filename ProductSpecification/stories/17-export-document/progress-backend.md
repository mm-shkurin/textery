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
- [~] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.3: An unsupported or missing format is refused
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
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
