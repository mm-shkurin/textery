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
- [x] green-adapter rest — GREEN: added `"INVALID_FORMAT": 422` to `_ERROR_CODE_STATUS_MAP`
  (exception_handlers.py, 78 lines); no new handler — `validation_exception_handler` already emits
  the canonical `{error_code, message}` body, only the status was defaulting to 400. Error-handling
  tests 11 passed / 0 skipped; full rest adapter suite 73 passed, no regression. Coverage:
  exception_handlers.py 100% (21 stmts, 0 branch), no gaps.
- [x] green-acceptance — GREEN live against the rebuilt backend (BACKEND_PORT=8100): 5 passed
  incl. both format-guard cases `[unsupported_format]` (xml→422) and `[missing_format]` (None→422),
  plus the three Sc 1.1/1.2 regression tests. Enabled the test by removing the RED skip decorator
  (only test change). Baked-image rebuild done per carryover quirk before running.

### Scenario 2.1: A document exports as a valid PDF
- [x] red-acceptance — RED confirmed live (BACKEND_PORT=8100): the export found-path returns the
  DocumentResponseDto JSON placeholder, so `content_type='application/json'` vs expected exact
  `'application/pdf'` (predicted == actual, AssertionError). New class `TestExportDocumentAsPdf`
  delegates to `assert_valid_pdf_attachment` (Statements): strict status 200, exact application/pdf
  content type, `%PDF-` magic-byte signature, attachment Content-Disposition, and `body is None`
  (added per test-review cluster-A: no JSON dict-body may leak on the success path). Skip-marked;
  5 passed / 1 skipped. NOTE: `document_export_statements.py` is now at exactly the 200-line cap —
  any further addition to it must split the file first.
- [x] design — PDF rendering, mirroring the established `HtmlSanitizer` port→adapter precedent
  (usecase Protocol port implemented by a themed adapter under `backend/adapters/`). Decisions
  (all substance pinned by interview 2026-07-25 — WeasyPrint for PDF, backend render, synchronous
  GET returns binary, no polling, `url_fetcher` disabled — so no open fork, no ADR):
  • New usecase port `backend/usecase/src/document/document_renderer.py` — `DocumentRenderer(Protocol)`
    with `render(content: str, export_format: ExportFormat) -> bytes` (unified over the format enum
    to avoid a per-format method explosion; 2.1 implements the pdf branch, 2.2 adds docx).
  • New adapter module `backend/adapters/rendering` with `WeasyPrintPdfRenderer` implementing the
    pdf branch. `url_fetcher` disabled from construction (SSRF-safe by default — Sc 4.1 formally
    asserts it; building it safe now avoids a knowingly-unsafe interim).
  • `ExportDocument.execute` return shape changes: after `ExportFormat.parse` + owner-scoped fetch,
    a found document is rendered; execute returns the rendered bytes + media type (absent/foreign
    still collapse to None → 404, unchanged). 2.1 uses a fixed default filename `document.pdf`
    (title-derived filename is Sc 3.1/3.2 — out of scope here).
  • Rest `/export` returns a binary `Response(content=bytes, media_type="application/pdf",
    headers={"Content-Disposition": "attachment; filename=document.pdf"})` instead of the
    DocumentResponseDto JSON placeholder. In-process synchronous render (forced by the
    no-polling binary-GET contract; render deadline/resource bounds are Sc 4.2/4.5 + Load 2.1).
  • DEPENDENCY green will require: add WeasyPrint to backend requirements + libpango/cairo system
    libs to backend.Dockerfile so the render actually executes (the baked image must be rebuilt for
    green-acceptance). The fail-fast-at-boot guard for missing native libs is owned by Infra 1.1.
- [x] red-usecase — RED confirmed live: `TypeError: ExportDocument.__init__() got an unexpected
  keyword argument 'document_renderer'` on all 7 tests (predicted == actual). Uses a
  `FakeDocumentRenderer` (in document_fakes.py) — no real WeasyPrint. Three cases: (1) happy path
  asserts `result.content == FAKE_RENDERED_PDF` + `result.media_type == "application/pdf"` (exact)
  AND `renderer.calls == [("<p>Привет</p>", ExportFormat.PDF)]` (proves the STORED content is
  rendered under the parsed format); (2) not-found returns None AND `renderer.calls == []` (a
  missing document never reaches render); (3) invalid-format (5 params) raises INVALID_FORMAT
  before fetch/render AND `renderer.calls == []`. docx positive control deferred to Sc 2.2
  red-usecase (asserting a docx media_type here would force 2.2's branch into 2.1's green).
  test-review: no changes — assertions already strict; placement flag (Statements DSL) overruled
  by the document-usecase family's inline direct-fakes convention.
- [x] green-usecase — GREEN at 7 passed (usecase suite 167 passed). New port
  `document_renderer.py` (`DocumentRenderer(Protocol)`, sync `render(content, export_format) ->
  bytes`, mirrors HtmlSanitizer); new frozen result `rendered_export.py`
  (`RenderedExport(content: bytes, media_type: str)`). `ExportDocument` gains the renderer arg;
  execute parses format → owner-scoped fetch (None → None, renderer untouched) → renders
  `document.content` and returns `RenderedExport`; media type from an `ExportFormat`-keyed dict
  (only PDF mapped now — an unmapped format KeyErrors loudly, never a wrong Content-Type; DOCX is
  a one-line add in Sc 2.2). Coverage: all three files 100% line+branch.
  FOLLOW-UP (breaks app construction until closed): `backend/application/src/app/container/
  document_wiring.py` still constructs `ExportDocument(document_repository=...)` without the now-
  required `document_renderer` — deliberately NOT wired here (the WeasyPrint adapter doesn't exist
  yet and may not import on the Windows host). adapters-discovery / green-adapter rendering must
  create the rendering adapter and inject it before the app boots / green-acceptance rebuilds.
- [x] adapters-discovery (rendering + rest) — Check 1 (ports): rendering — GAP: the new
  `DocumentRenderer` port has NO adapter. Add module `backend/adapters/rendering` with
  `WeasyPrintPdfRenderer` implementing `render(content, ExportFormat.PDF) -> bytes` with WeasyPrint's
  `url_fetcher` disabled (SSRF-safe from construction); wire it into the composition root
  (`backend/application/src/app/container/document_wiring.py`, which currently omits the required
  `document_renderer` arg — see green-usecase follow-up) → red-adapter rendering / green-adapter
  rendering. `DocumentRepository.find_by_id_and_owner` unchanged → [S]. Check 2 (exceptions): [S] for
  2.1 — render-failure / deadline / disclosure exceptions are owned by Sc 4.2/4.3/4.4; the happy
  path raises nothing new. Check 3 (response shape): rest — GAP: `/export` still returns the
  `DocumentResponseDto` JSON placeholder, but the usecase now returns `RenderedExport(content,
  media_type)`; the route must return a binary `fastapi.Response(content=bytes,
  media_type=RenderedExport.media_type, headers={"Content-Disposition": "attachment;
  filename=document.pdf"})` — there is NO binary-Response precedent in the rest layer (only
  JSONResponse) → red-adapter rest / green-adapter rest.
  ⚠️ WINDOWS-HOST CONSTRAINT (confirmed live): `import weasyprint` fails on this host (no
  GTK/pango/cairo), so a host-side pytest cannot even COLLECT the rendering-adapter test (the module
  imports weasyprint at load). DECISION (user, 2026-07-26): **run the rendering-adapter red/green
  tests inside the Linux backend container** (Docker), matching the acceptance pattern — host suites
  stay weasyprint-free. So: add WeasyPrint to backend requirements + libpango/cairo to
  backend.Dockerfile, rebuild the backend image, and execute the rendering-adapter tests via
  `docker compose exec` (or the container's own pytest run) at BOTH red-adapter rendering (confirm
  the real RED in-container) and green-adapter rendering. This is a departure from the usual
  host-run adapter tests, forced by the native dependency.
- [x] red-adapter rendering — RED confirmed live on host: `ModuleNotFoundError: No module named
  'rendering.weasyprint_pdf_renderer'` (predicted == actual). New module `backend/adapters/rendering`
  (src root + tests root registered in backend/pyproject.toml: pytest pythonpath, mypy mypy_path +
  files, isort known-first-party "rendering"); full backend suite still collects (514 tests, exit 0).
  Test `test_weasyprint_pdf_renderer.py` (26 lines) defers the adapter import into the test body (so
  the suite collects clean while weasyprint is absent on the host) and asserts strictly
  `isinstance(result, bytes)` + `result.startswith(b"%PDF-")`. Skip-marked (1 skipped). test-review:
  A/S/P all clean — `%PDF-` prefix is the strict boundable signature (full-body equality impossible;
  WeasyPrint output is non-deterministic), inline asserts match the sibling nh3 adapter-test convention.
  GREEN runs in-container.
- [x] green-adapter rendering — GREEN in-container: `WeasyPrintPdfRenderer.render("<p>Привет</p>",
  ExportFormat.PDF)` produced a real PDF (%PDF- + %%EOF + len>500) — 1 passed in the Linux backend
  container. Adapter `backend/adapters/rendering/src/rendering/weasyprint_pdf_renderer.py`:
  `weasyprint.HTML(string=content, url_fetcher=_blocked_url_fetcher).write_pdf()`; the blocking
  url_fetcher makes it SSRF-safe from construction (never fires on plain HTML; Sc 4.1 covers its
  raise — the one uncovered line, coverage 89%). Added `weasyprint==63.1` to requirements +
  libpango/cairo/harfbuzz/gdk-pixbuf/libffi8/fonts-dejavu-core to backend.Dockerfile AND both CI
  `test` jobs (backend/.github + root .github) so the test runs in the gating env, not a vacuous
  importorskip. Re-added `adapters/rendering/src` to mypy `files`; wired WeasyPrintPdfRenderer into
  `document_wiring.py` via a DEFERRED import (keeps host test-imports weasyprint-free) — this FIXED
  the `document_wiring.py:31` mypy error. Test now uses module-level `pytest.importorskip("weasyprint")`
  (skips only on the bare host; runs in CI/container). mypy on host: 269 files checked, only the
  router:115 error remains (owned by green-adapter rest).
  ⚠️ QUIRK (in-container test runs): the runtime backend image does NOT COPY backend/pyproject.toml,
  so pytest in-container has no `pythonpath` config — a bare `python -m pytest` fails with
  `ModuleNotFoundError: No module named 'document'`. Run in-container tests with explicit
  `PYTHONPATH=domain/src:adapters/rendering/src` (add the other src roots as a given test needs).
  > MUST-DO when creating the adapter src file:
  > (1) re-add `"adapters/rendering/src",` to the mypy `files` list in backend/pyproject.toml (it was
  >     deferred at red-adapter rendering because mypy `files` errors-out on an empty root — see the
  >     comment there); this also FIXES the pending mypy error
  >     `document_wiring.py:31 Missing positional argument "document_renderer"` by wiring the real
  >     WeasyPrintPdfRenderer into the composition root.
  > (2) CI GUARD (premortem, commit 20595ac): the CI `test` job runs on ubuntu WITHOUT libpango/cairo.
  >     Do NOT lift the RED skip into a `skipif(weasyprint-unimportable)` — that makes the render test
  >     skip FOREVER in the only gating env (vacuous green). Instead add the native libs to
  >     backend/.github/workflows/ci.yml (apt-get libpango-1.0-0 libpangocairo-1.0-0 libcairo2 …) so
  >     the test actually RUNS on the runner, and run it in-container locally per the 2026-07-26 decision.
  > (3) the RED test already pins %PDF- + %%EOF trailer + length>500 (strengthened at red-adapter
  >     rendering per premortem) — green must satisfy all three.
- [x] red-adapter rest — RED confirmed live: `AttributeError: 'RenderedExport' object has no
  attribute 'id'` at document_router.py:115 (the route still calls `DocumentResponseDto.from_domain`
  on the RenderedExport) — predicted == actual. New `TestExportDocumentAsPdfResponse` (reuses the
  `export_client` fixture + `mocker.AsyncMock`): a fake usecase returns
  `RenderedExport(b"%PDF-1.7 fake pdf bytes", "application/pdf")`; asserts strict status 200,
  `content-type == "application/pdf"`, `content ==` the exact bytes, and `content-disposition ==
  "attachment; filename=document.pdf"`. Skip-marked (1 passed / 1 skipped). test-review: A/S/P clean,
  no changes. GREEN builds the binary fastapi.Response and FIXES the last pending mypy error
  (document_router.py:115).
  > When green-adapter rest returns the binary Response, it FIXES the pending mypy error
  > `document_router.py:115 Argument 1 to "from_domain" ... incompatible type "RenderedExport"; expected
  > "Document"` — the route must stop calling DocumentResponseDto.from_domain on the RenderedExport and
  > instead build a binary fastapi.Response from its bytes + media_type.
- [x] green-adapter rest — GREEN: `export_document` route now returns a binary
  `fastapi.Response(content=rendered.content, media_type=rendered.media_type,
  headers={"Content-Disposition": "attachment; filename=document.pdf"})` instead of
  `DocumentResponseDto.from_domain` (dropped `response_model=DocumentResponseDto`, return type
  `DocumentResponseDto` → `Response`, result var `document` → `rendered`). Media type threaded
  from `RenderedExport`, not hardcoded. 404 (None) path unchanged. Enabled the RED test by
  removing its `@pytest.mark.skip` (only test change; orphaned `import pytest` also removed for
  ruff). Rest adapter suite 74 passed / 0 failed / 0 skipped; mypy `adapters/rest/src` clean —
  the pending `document_router.py:115` incompatible-type error is FIXED. Coverage: export route
  lines + both branches (4/4) 100%; the 5 uncovered lines are pre-existing DI-provider
  `NotImplementedError` stubs (composition-root pattern, out of scope).
- [x] green-acceptance — GREEN live against the rebuilt backend (BACKEND_PORT=8100): 6 passed
  (was 5 passed / 1 skipped). `test_owner_exports_own_document_as_valid_pdf_attachment` now
  passes — the `/export` route streams a real WeasyPrint PDF (%PDF- magic, application/pdf,
  attachment disposition, `body is None` on the success path). Enabled the test by removing the
  RED skip decorator (only test change). Baked-image rebuild (docker compose up -d --build
  backend) done per carryover quirk before running; container healthy. **Scenario 2.1 COMPLETE.**

### Scenario 2.2: A document exports as a valid DOCX
> CARRY-FORWARD (from Sc 2.1 green-usecase reviews, commit 26c1d66 — agent-review + premortem, both
> CONCERNS CREDIBLE): `ExportFormat.parse` ACCEPTS `docx` (advertised in the INVALID_FORMAT message),
> but the Sc 2.1 `_MEDIA_TYPE` dict maps only PDF and `execute` renders BEFORE the media lookup — so
> `format="docx"` on an owned document currently renders (wasted) then raises an unhandled `KeyError`
> → a 500 for a validation-passing input. No prod exposure (story not deployable until wiring lands),
> but 2.2 MUST close it: red-usecase needs a docx-on-found case, green maps `ExportFormat.DOCX` +
> renders docx, and consider moving the media-type lookup ahead of `render` (fail-fast, no wasted
> render). Do NOT let 2.2 inherit the silent 500 window.
- [x] red-acceptance — RED confirmed live: exporting an owned document as docx returns
  `status_code=500 {error_code:INTERNAL_ERROR}` vs expected 200 wordprocessingml attachment
  (predicted == actual) — this is exactly the carry-forward KeyError window: `docx` passes
  `ExportFormat.parse` but the `_MEDIA_TYPE` dict maps only PDF, so `execute` renders then
  KeyErrors → sanctioned 500. New class `TestExportDocumentAsDocx` delegates to a new
  `DocumentExportDocxStatements` (`given_owner_exports_their_own_document_as_docx()` +
  `assert_valid_docx_attachment`): strict status 200, exact DOCX_CONTENT_TYPE
  (`application/vnd.openxmlformats-officedocument.wordprocessingml.document`), `PK\x03\x04`
  ZIP magic prefix, attachment Content-Disposition, `body is None`. Statements split into a new
  51-line module (base `document_export_statements.py` was at the 200-line cap). Skip-marked;
  6 passed / 1 skipped. test-review: assertions already strict (A/P clean); one S DRY finding
  (docx assert duplicates the base pdf assert) deferred to /refactor — extracting it would push
  the 200-line base over cap. NOTE (pre-existing, out of scope): conftest.py is 258 lines
  (over the 200-cap before this change); red only added a 2-line fixture — worth a future split.
> CARRY-FORWARD (from red-acceptance premortem, commit 9384dee — CONCERNS CREDIBLE): the RED
> DOCX assert pins only `PK\x03\x04` (generic ZIP local-file-header magic). That passes for ANY
> zip — an empty zip, a renamed archive, a docx missing its OOXML parts — so a minimal green
> renderer emitting a bare/corrupt zip would ship green while Word reports "file is corrupt".
> Before green cements the contract, STRENGTHEN `assert_valid_docx_attachment` to open the bytes
> with `zipfile.ZipFile(io.BytesIO(content))` and assert the mandatory OOXML parts are present
> (`[Content_Types].xml` + `word/document.xml` in `namelist()`, and not `BadZipFile`). Content
> fidelity (owner's text survives into the .docx) is a separate concern — no dedicated scenario
> exists in the 2.x sequence; flag as a story-level gap (parallels the Sc 3.4 PDF glyph guard).
> agent-review: PASS. refactor: NO ACTION (DRY docx/pdf assert duplication left as-is — base at
> 200-line cap, extraction would push it over; RED skip must stay).
- [x] design — see `decisions/docx-rendering-decision.md` (ADR). Format-dispatching renderer
  behind the unified `DocumentRenderer` port: PDF→WeasyPrintPdfRenderer, DOCX→new pure-Python
  `HtmlDocxRenderer` (`htmldocx`→`python-docx`, no native binary, no network). Usecase adds
  `ExportFormat.DOCX` to `_MEDIA_TYPE` and moves the media lookup AHEAD of `render()` (fail-fast,
  closes the docx KeyError→500 window). Hazard scan (all 8 groups) folded:
  • red-usecase MUST add a `_MEDIA_TYPE`/dispatcher **exhaustiveness** guard — every `ExportFormat`
    member maps to a media type and the dispatcher handles every member, so a future format can't
    silently 500 (grp4/grp5 unknown-enum / dispatch-exhaustiveness).
  • green-acceptance assert strengthened to OOXML structure ([Content_Types].xml + word/document.xml)
    per the earlier carry-forward (grp1 structural half).
  • DOCX metadata redaction (grp7 UNOWNED, assigned here): `HtmlDocxRenderer` sets neutral
    `core_properties` — no OS username as author, `created`/`modified` from an injected clock, not
    raw server time. red/green-adapter rendering must assert `docProps/core.xml` leaks no server
    identity/time.
  SEAMS handed to downstream scenarios (each must exercise the DOCX path, not only PDF): multibyte
  text round-trip → Sc 3.4; embedded-URL SSRF (no outbound fetch from HtmlDocxRenderer) → Sc 4.1 /
  Security 3.1; render deadline wraps HtmlDocxRenderer → Sc 4.2; input-size cap gates before the
  docx build → Sc 4.5; concurrent-render bound covers docx → Load 2.1; resource/temp-file leak on a
  failing docx render → Infra 2.1; boot-time dep fail-fast (htmldocx/python-docx importable) →
  Infra 1.1; IDOR re-auth → owner-scoped fetch (already covered, Sc 1.1/1.2/Security 1.1). One extra
  UNOWNED gap: DOCX **output-size amplification** (small input → huge in-memory .docx) — assign to
  Sc 4.5 (extend its cap from input to output).
- [x] red-usecase — RED confirmed live (7 passed, 2 skipped). Added to
  test_export_document_usecase.py (92→132 lines): (1) DOCX positive control
  `test_should_render_the_stored_content_and_return_docx_bytes` — found owned doc + format="docx"
  returns `RenderedExport` with `media_type == "application/vnd.openxmlformats-officedocument.
  wordprocessingml.document"` (exact) AND `renderer.calls == [(document.content, ExportFormat.DOCX)]`;
  currently `KeyError: <ExportFormat.DOCX: 'docx'>` at export_document.py:38 (docx unmapped, renders
  then KeyErrors) — predicted == actual. (2) EXHAUSTIVENESS guard
  `test_every_export_format_resolves_to_a_media_type` (hazard grp4/5): `set(ExportFormat) -
  set(_MEDIA_TYPE) == set()`; currently `AssertionError ... unmapped: {ExportFormat.DOCX}` — predicted
  == actual. GREEN: add `ExportFormat.DOCX` to `_MEDIA_TYPE` and move the media lookup ahead of
  `render()` per the ADR. Fail-fast-ordering test #3 OMITTED (not skipped): with only pdf/docx both
  mapped after green, no parseable-but-unmapped format exists, so lookup-before-render is
  un-observable via the public API without contriving an invalid enum member (forbidden); invariant
  pinned by test #2 + the ADR reorder instead. test-review: assertions already strict (A clean; exact
  equality / identity / set-equality); P inline-fakes placement flag dismissed per the document-usecase
  family's established direct-fakes convention (same call as Sc 2.1 red-usecase). Uses FakeDocumentRenderer
  — no real htmldocx/python-docx.
- [x] green-usecase — GREEN (usecase file 9 passed; full usecase suite 169 passed, 0 skipped).
  export_document.py (44 lines): added `ExportFormat.DOCX:
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document"` to `_MEDIA_TYPE`, and
  moved `media_type = _MEDIA_TYPE[export_format]` AHEAD of `render()` (fail-fast, closes the docx
  KeyError→500 window). None→None (404) path unchanged and first. Both RED tests enabled (removed
  skip markers only). Coverage: export_document.py 100% line (18/18) + branch (2/2), no gaps.
- [x] adapters-discovery (rendering) — Check 1 (ports): rendering — GAP: `ExportDocument.document_renderer`
  is wired to the bare `WeasyPrintPdfRenderer`, which only writes PDF and ignores `export_format` — a
  `format=docx` request currently returns PDF bytes under a wordprocessingml Content-Type (premortem on
  0a9ac9a, guarded by the RED acceptance 9384dee). Per the ADR: add a pure-Python `HtmlDocxRenderer`
  (`htmldocx`→`python-docx`, neutral `docProps` core properties + injected clock — hazard grp7 redaction
  guard) implementing the DOCX branch, and a `FormatDispatchingRenderer` implementing `DocumentRenderer`
  that routes PDF→WeasyPrintPdfRenderer, DOCX→HtmlDocxRenderer (raises loudly on an unmapped member);
  wire `FormatDispatchingRenderer` into `document_wiring.py` in place of the bare WeasyPrintPdfRenderer
  → red-adapter rendering / green-adapter rendering. `SqlAlchemyDocumentStorage.find_by_id_and_owner`
  unchanged → [S]. Check 2 (exceptions): [S] — happy path raises nothing new; the docx KeyError→500
  window is closed at the usecase (green-usecase 0a9ac9a); ValidationException(INVALID_FORMAT) already
  mapped (Sc 1.3); render-failure/disclosure owned by Sc 4.3/4.4/5.1. Check 3 (response shape): [S] rest —
  `/export` already returns a binary `Response(content, media_type=rendered.media_type, Content-Disposition
  attachment)` (Sc 2.1 green-adapter rest); `media_type` is threaded from RenderedExport, so the DOCX MIME
  flows through with no rest change. ⚠️ IN-CONTAINER: the rendering adapter + wiring import weasyprint
  (host-unimportable, no Pango/cairo), so run the rendering-adapter red/green tests in the Linux backend
  container per the Sc 2.1 decision; add `htmldocx`+`python-docx` to backend requirements + both CI test
  jobs (pure-Python, no new native libs). green-adapter rendering MUST also assert `docProps/core.xml`
  leaks no server identity/time (neutral author, injected/fixed clock — grp7 unowned GAP assigned here).
- [x] red-adapter rendering — RED confirmed live: `ModuleNotFoundError: No module named
  'rendering.format_dispatching_renderer'` (and `...html_docx_renderer`) via deferred import
  (predicted == actual). Two new test modules (93 + 71 lines): `test_html_docx_renderer.py`
  (`TestHtmlDocxRenderer`) asserts `HtmlDocxRenderer.render("<p>Привет</p>", DOCX)` → `PK\x03\x04`
  bytes, `[Content_Types].xml`+`word/document.xml` in the zip, "Привет" present in word/document.xml
  (multibyte), AND neutral docProps — `dc:creator`/`cp:lastModifiedBy == "Textery"` (exact),
  `dcterms:created`/`modified == FIXED_NOW` from an injected FixedClock (grp7 redaction guard);
  `test_format_dispatching_renderer.py` (`TestFormatDispatchingRenderer`) asserts DOCX→docx renderer
  output, PDF→pdf renderer output, and an unmapped format raises `ValueError` with NEITHER renderer
  called (never silent wrong-format bytes). Conventions: html_docx module uses `importorskip("htmldocx")`
  (pure-Python, runs once green adds the dep); dispatcher test defers the weasyprint import + uses
  in-memory FakeRenderers so the RED is confirmable ON HOST (importorskip would have masked it). Full
  backend suite still collects clean (519 tests, exit 0); committed form 4 skipped. test-review: A/S/P
  all clean — assertions already strict (exact equality on docProps + call-lists; both OOXML parts
  pinned). GREEN runs in-container.
- [x] green-adapter rendering — GREEN in-container: 6 passed / 0 skipped / 0 failed; the two
  `importorskip("htmldocx")`/`("docx")` html_docx tests genuinely RAN (`-rs` showed zero skips —
  vacuous-green trap avoided). New `html_docx_renderer.py` (47): `HtmlDocxRenderer(clock)` parses
  sanitized HTML via `htmldocx` into a `python-docx` Document → BytesIO → bytes; neutral
  core_properties (`author`/`last_modified_by` = "Textery", `created`/`modified` = `clock.now()`) —
  group-07 redaction guard. New `format_dispatching_renderer.py` (30): `FormatDispatchingRenderer(
  pdf_renderer, docx_renderer)` routes on ExportFormat, raises `ValueError` ("format") on unmapped
  member with NEITHER renderer called. Wired `FormatDispatchingRenderer(WeasyPrintPdfRenderer(),
  HtmlDocxRenderer(clock=SystemClock()))` into document_wiring.py (64) via deferred import (host stays
  weasyprint-free); `SystemClock.now()` = `datetime.now(UTC)`. Added `python-docx==1.1.2` +
  `htmldocx==0.0.6` to backend/requirements.txt (pure-Python, no apt). Both CI files install via
  `pip install -r requirements.txt` — pip-only pins picked up with no yaml edit (only weasyprint's
  native libs needed apt). mypy `files` already has adapters/rendering/src; new imports use
  `# type: ignore[import-untyped]` (weasyprint pattern). Coverage: both new files 100% line + branch.
  Removed the `@pytest.mark.skip` from both RED classes (only test change). Baked image rebuilt so
  deps installed before running (carryover quirk).
  QUIRK: container mounts project at /app/backend, so in-container cwd is `cd /app/backend` (not
  `/app` as the Sc 2.1 handoff stated) — correct in next handoff.
- [x] green-acceptance — GREEN live against the rebuilt backend (BACKEND_PORT=8100): 7 passed
  (was 6 passed / 1 skipped). `test_owner_exports_own_document_as_valid_docx_attachment` now passes —
  `/export?format=docx` on an owned document streams a real .docx (200, exact wordprocessingml
  content type, PK\x03\x04, attachment disposition, `body is None`). Enabled the test (removed RED
  skip) AND strengthened `assert_valid_docx_attachment` per the red-acceptance premortem carry-forward:
  opens the bytes with `zipfile.ZipFile` and requires the mandatory OOXML parts `[Content_Types].xml`
  + `word/document.xml` (a bare/renamed zip that Word calls corrupt can no longer ship green; BadZipFile
  → AssertionError). Statements file 69 lines (under cap). Baked image rebuilt before running (carryover
  quirk). **Scenario 2.2 COMPLETE.**

### Scenario 2.3: An empty document exports to a valid file
- [S] red-acceptance — EXISTENCE-CHECK HIT (no valid RED; not faked): empty content is the DEFAULT
  state of every created document — `Document.create()` (domain/document.py:67-77) hardcodes
  `content=""` and the create path (POST /documents) accepts only `document_type`, so a freshly
  created doc IS the empty-content case. Sc 2.1/2.2's happy-path tests already export exactly such a
  document (`_create_document_owned_by` creates with no content; `ExportDocument.execute` renders
  `document.content == ""` directly) and both pass live (BACKEND_PORT=8100: TestExportDocumentAsPdf +
  TestExportDocumentAsDocx = 2 passed). A new empty-doc test would duplicate 2.1/2.2 byte-for-byte —
  forbidden by the existence-check rule. Whitespace-only content (extended §1.2) is a strictly-more
  content case requiring SaveDocument, out of core 2.3 scope.
- [S] design — no domain/usecase/adapter change; render path already handles `content == ""`.
- [S] red-usecase — covered by Sc 2.1/2.2 usecase tests (render of stored content).
- [S] green-usecase — no production change.
- [S] adapters-discovery — no adapter change.
- [S] green-acceptance — nothing to enable; capability already green via 2.1/2.2.

### Scenario 2.4: Export does not mutate the document
- [x] red-acceptance — ALREADY-GREEN regression guard (not a fabricated RED, not a duplicate):
  version-stability across export is asserted by NO existing test (2.1/2.2 assert file validity, 1.x
  refusal), so this is a genuinely new contract. Predicted "test passes — export is a GET with no
  SaveDocument, version stable"; actual == predicted (1 passed live BACKEND_PORT=8100; export suite
  8 passed). Committed ENABLED (a passing guard carries no skip marker). New class
  `TestExportDoesNotMutateDocument` → new `DocumentExportNoMutationStatements` (84 lines; base at
  200-cap): reads via GetDocument, exports pdf, re-reads; `ExportMutationSnapshot` before/after pins
  `version_after == version_before` (exact int) PLUS `content` + `updated_at` exact-equality (a
  mutation touching any of the three cannot slip through). Added `get_document` client method +
  `GetDocumentResponseDto`; registered fixture. test-review inline: assertions strict + non-vacuous
  (GetDocument single-doc body carries content/version/updated_at per document_dtos.py:58-77), Statements
  placement clean. FLAG: conftest.py now 260 lines (over 200-cap; was ~254 pre-existing — fixtures must
  live in conftest, so the +6 lines were unavoidable). Cross-suite conftest split deferred to a
  dedicated refactor, out of this work unit's scope.
- [S] design — no production change: export is a read-only GET (`ExportDocument.execute` does
  `find_by_id_and_owner` + render, no SaveDocument), so non-mutation is a structural property, not
  new behavior to build. Confirmed by premortem PASS on 08720ce (both formats share one read-only
  execute; the domain entity has no last-accessed/export-count field to drift).
- [S] red-usecase — non-mutation needs no usecase behavior; the read-only structure is already
  covered by the Sc 2.1/2.2 usecase tests (execute renders stored content without persisting).
- [S] green-usecase — no production change.
- [S] adapters-discovery — no adapter change; no new port/exception/response shape.
- [S] green-acceptance — the guard is already enabled + green from red-acceptance (08720ce); nothing
  to enable. Save-then-export freshness (a NON-default version) is owned by Sc 3.5 / Integration 2.1.

### Scenario 3.1: The filename is derived from the title, encoded for Cyrillic
> AUTONOMOUS DESIGN DECISION (user-approved to proceed autonomously, 2026-07-27): `title` is a NEW
> `Document` field, landed via an additive migration, SET through the SaveDocument save API (PUT
> /api/v1/documents/{id}), read by export to derive the filename. Cross-story: the `title` column is
> shared with story-5-extension ("whoever lands it first adds it") — this session lands it. The
> `design` step below formalizes the model (domain field + migration + save DTO + RFC 5987 filename
> in the rest route); consider an ADR given the cross-story migration coordination.
- [x] red-acceptance — RED confirmed live (BACKEND_PORT=8100): predicted == actual.
  `test_export_filename_is_rfc5987_encoded_from_cyrillic_title` (class `TestExportFilenameFromCyrillicTitle`)
  → new `DocumentExportFilenameStatements` (74 lines; base at 200-cap): create doc, save it with title
  "Привет Мир" via the save API, export pdf, assert the FULL `Content-Disposition` equals
  `attachment; filename*=UTF-8''%D0%9F%D1%80%D0%B8%D0%B2%D0%B5%D1%82%20%D0%9C%D0%B8%D1%80.pdf`
  (exact equality, literal-pinned RFC 5987 value — no runtime encoding, no tautology). Actual:
  `attachment; filename=document.pdf` (export hardcodes it; document_router.py:~118). SETUP QUIRK
  confirmed live: the title-bearing save returns 200 because `SaveDocumentRequestDto` has Pydantic
  `extra="ignore"` and SILENTLY DROPS the unknown `title` field — so GREEN must add `title` to the
  save DTO + persist it (a dropped title = no filename derivation). Added `save_document` acceptance
  client method (PUT, optional title) + `SaveDocumentResponseDto`; registered fixture. test-review
  inline: assertions strict + exact-equality, placement clean. FLAG: conftest.py now 204 lines
  (over 200-cap; +8 for the new fixture) — /refactor to trim this work unit.
- [x] design — see `decisions/title-filename-decision.md` (ADR). `title` is a NEW nullable
  `Document` field via an ADDITIVE Alembic migration (rolling-deploy safe — Infra 3.1), set through
  the save path: `SaveDocumentRequestDto` gains optional `title`, `SaveDocument.execute` gains
  `title`, and the existing version-CAS `save_content_if_version_matches` persists it in the SAME
  single SQL UPDATE (no read-compare-write). `Document.create` does NOT take title (mass-assignment
  guard, Security 2.1) — a draft is born title=None; title set only via owner-scoped save.
  DERIVATION vs ENCODING split: `ExportDocument.execute` derives a PLAIN filename (title when present
  else default stem "document"; extension from `ExportFormat` — also closes the Sc 2.2 hardcoded-
  document.pdf carry-forward) onto `RenderedExport.filename`; the rest `/export` route RFC 5987-
  percent-encodes it into `Content-Disposition: attachment; filename*=UTF-8''<encoded>` (encoding is
  an HTTP wire concern, kept in the adapter). CROSS-STORY: `documents.title` is shared with
  story-5-extension — adapters-discovery MUST check `migrations/versions/` for an existing title
  revision before adding one (reuse, don't double-add). Seams: default filename → Sc 3.2; CR/LF/quote
  strip → Sc 3.3; grapheme truncation → Sc 3.6; docx extension → Sc 3.2 carry-forward.
- [x] red-usecase — RED confirmed live: `AttributeError: 'RenderedExport' object has no attribute
  'filename'` on all 3 cases (predicted == actual); 9 passed / 3 skipped after skip-mark. New
  parametrized `test_should_derive_the_plain_filename_from_the_title`: title "Привет Мир" + pdf →
  `result.filename == "Привет Мир.pdf"`; + docx → `"Привет Мир.docx"` (pins the format-driven
  extension); title None + pdf → `"document.pdf"` (default stem, so green can't regress it). Asserts
  the PLAIN unicode filename — RFC 5987 encoding is NOT tested here (rest concern per ADR). Extended
  `stored_document` fake to accept `title` (attaches it; the domain field lands in green). test-review
  inline: exact-equality assertions, clean placement; test file 161 lines, document_fakes 178 (under
  cap). GREEN must: add `filename: str` to RenderedExport; add `title: str | None` to
  `Document.__init__`/`reconstitute` (NOT create); derive stem (title-or-"document") + `.pdf`/`.docx`
  extension in `ExportDocument.execute`.
- [x] green-usecase — GREEN: 304 passed (usecase + domain suites), 0 failed; 3 formerly-skipped
  filename cases pass. `RenderedExport` gained `filename: str` (default "document.pdf" so the Sc 2.1
  rest test's 2-positional `RenderedExport(content, media_type)` still compiles — the usecase always
  supplies the real value; remove the default when green-adapter rest updates that construction).
  `Document.__init__`/`reconstitute` gained `title: str | None = None` (create() untouched —
  mass-assignment guard); default None keeps all callers valid. `ExportDocument.execute`:
  `stem = document.title or "document"` (handles None AND empty), `filename = f"{stem}.{export_format.value}"`
  — extension IS the enum value, so it cannot drift from the media dispatch (closes Sc 2.2
  hardcoded-document.pdf carry-forward). No RFC 5987 encoding (rest concern). Whitespace-only stem
  passes through → Sc 3.2 owns that. `stored_document` fake now threads title through the constructor.
  Coverage: export_document.py + rendered_export.py 100% line+branch; document.py 96% (line 103
  reconstitute return — pre-existing gap, covered in the db adapter suite). Files ≤200 (document 116,
  export_document 52, rendered_export 19).
- [x] adapters-discovery (db + rest) — Check 1 (ports): db — GAP. The write→read title flow is
  unsupported end to end: `DocumentModel` has no `title` column, `to_domain`/`from_domain` don't
  thread it, `SqlAlchemyDocumentStorage.save_content_if_version_matches` doesn't persist it, and the
  `DocumentRepository.save_content_if_version_matches` port + `SaveDocument.execute` don't accept it —
  so a saved title never round-trips to the export read. No existing `title` Alembic revision
  (`grep title migrations/versions` empty), so THIS session adds the additive nullable column.
  ⚠️ CORRECTED HEAD (2026-07-27, verified live via revision-graph walk): the real Alembic head is
  `1a2b3c4d5e6f` (oauth_rate_limits), NOT `b2c3d4e5f6a7` as the ADR/this line first claimed —
  `b2c3d4e5f6a7` is a mid-chain revision. The additive title migration's `down_revision` MUST be
  `1a2b3c4d5e6f`. Check 2 (exceptions): [S] — no new domain exception (a null/absent title is a
  default filename, not an error). Check 3 (response shape): rest — GAP ×2: (a) the save endpoint
  `SaveDocumentRequestDto` has no `title` (Pydantic `extra=ignore` drops it) and the PUT route doesn't
  forward it to `execute`; (b) the export route hardcodes `Content-Disposition: attachment;
  filename=document.pdf` (document_router.py:118) and ignores `rendered.filename` — it must thread it
  and RFC 5987-percent-encode (`filename*=UTF-8''<quote(filename, safe='')>`; `.`/unreserved stay
  literal, space→%20, Cyrillic→%XX, matching the red literal). Inserted steps below.
- [x] red-adapter db (title round-trip) — RED confirmed LIVE against real Postgres (localhost:5432):
  `TypeError: SqlAlchemyDocumentStorage.save_content_if_version_matches() got an unexpected keyword
  argument 'title'` (predicted == actual). New `TestTitlePersistence::test_should_round_trip_a_saved_title`
  + statements `save_content_with_title`: save content WITH title="Привет" through the version-CAS
  writer, read back via `find_by_id_and_owner`, assert `fetched.title == "Привет"` (exact,
  write-here-read-there). 9 passed / 1 skipped. test-review inline: strict equality, DSL in statements
  (test 170 lines, statements 103 — under cap). None/default case deliberately omitted (already green —
  title-less doc reads back None today). GREEN: nullable `title` column on DocumentModel + additive
  Alembic migration (down_revision b2c3d4e5f6a7); from_domain/to_domain thread it; port +
  SaveDocument.execute + storage CAS gain `title`. HARDENED (folded review findings): (1) premortem
  data-loss guard — added `test_should_preserve_an_existing_title_on_a_content_only_save`: after a
  title is set, a later content-only save (title omitted) must NOT wipe it — so GREEN must OMIT title
  from the CAS `.values()` when it is None, never `SET title = NULL` unconditionally. (2) agent-review
  same-session-echo — `expire_identity_map()` (session is `expire_on_commit=False`) forces a genuine
  SELECT re-hydration, not the cached RETURNING instance. Split `TestTitlePersistence` into
  `test_document_storage_title.py` (base was at the 200-cap). Both tests skip-marked (2 skipped).
- [x] green-adapter db (title round-trip) — GREEN against real Postgres: 2 target passed (both
  genuinely RAN, not skipped), full db suite 54 passed, usecase suite 172 passed. New additive
  nullable `title` column via migration `a3b4c5d6e7f8_add_title_column_to_documents.py`
  (`down_revision = "1a2b3c4d5e6f"` — the VERIFIED real head; ADR/discovery originally misstated
  it as `b2c3d4e5f6a7`, which is mid-chain). `DocumentModel.title` nullable + threaded through
  from_domain/to_domain; `title: str | None = None` added to the port
  `DocumentRepository.save_content_if_version_matches`, `SaveDocument.execute`, and the storage CAS.
  DATA-LOSS GUARD (premortem, pinned by test #2): storage builds `.values()` conditionally —
  `title` included ONLY when not None, so a content-only autosave never `SET title = NULL`.
  Both guard branches 100% covered (coverage-agent: document_storage.py + document_model.py 100%
  line+branch). Test-double conformance: `document_fakes.py` fake repo gained the same `title`
  param (fixed 7 usecase tests that broke on the signature change — not an assertion change).
  ⚠️ MIGRATION-HARNESS QUIRK (flag for next session): the db-test conftest does NOT run
  `alembic upgrade head` — the test DB is a persistent stamped schema. green-agent applied the new
  revision manually so it's proven to apply cleanly on top of `1a2b3c4d5e6f`. A fresh/CI test DB
  must be migrated to head before this suite runs, or `title` won't exist and the round-trip fails.
- [x] red-adapter rest (save title) — RED confirmed live (host, mocked usecase, no Postgres/weasyprint):
  predicted == actual. New `test_save_document_title_router.py` (`TestSaveDocumentTitleRoute`, 63 lines):
  PUT a save with `title="Привет Мир"` in the JSON body, assert the mocked `SaveDocument.execute` was
  `assert_awaited_once_with(..., title="Привет Мир")`. Actual: `AssertionError: expected await not
  found` — Expected includes `title='Привет Мир'`, Actual omits it (`Right contains 1 more item:
  {'title': 'Привет Мир'}`) — the route reads only content/version and `SaveDocumentRequestDto`
  (`extra="ignore"`) drops the unknown title. Skip-marked. test-review: A/S/P clean, no fixes —
  full-kwarg exact equality with the distinctive Cyrillic sentinel (no vacuous green). New file (not
  extending test_document_router.py at 189 lines) to stay ≤200. GREEN: add `title: str | None = None`
  to `SaveDocumentRequestDto` + forward `title=request.title` in the PUT route.
- [x] green-adapter rest (save title) — GREEN (host, mocked usecase): target
  `test_should_forward_the_title_to_the_save_usecase` PASSED (genuinely ran); router/document suite
  27 passed, full rest suite 75 passed, 0 regression. `SaveDocumentRequestDto` gained optional
  `title: str | None = None` (default None — a required field would 422 every current client/autosave
  that sends no title; plain `str`, since Pydantic v2 lax mode already 422s a non-string title). PUT
  `/{id}` route forwards `title=request.title`. REGRESSION FIX (premortem obligation): forwarding
  changed the actual execute-call signature, so the two existing save-route tests in
  test_document_router.py that pin exact `execute` kwargs (`test_should_return_200_with_the_stored_document`
  + `test_should_ignore_server_owned_fields_in_the_save_body`) were updated to include `title=None`
  (title-absent forwards None) — exact-kwarg pinning preserved, no assertion weakening. Coverage: DTO +
  route 100% on changed lines/branches (both title-present and title-absent paths exercised).
- [x] red-adapter rest (export filename) — RED confirmed live (host, mocked usecase): predicted ==
  actual. New class `TestExportFilenameRfc5987` in test_export_document_router.py (89 lines): mock
  usecase returns `RenderedExport(..., filename="Привет Мир.pdf")`; asserts FULL header exact
  `content-disposition == "attachment; filename*=UTF-8''%D0%9F%D1%80%D0%B8%D0%B2%D0%B5%D1%82%20%D0%9C%D0%B8%D1%80.pdf"`.
  Actual: `attachment; filename=document.pdf` (route hardcodes it, document_router.py:118, ignores
  `rendered.filename`). test-review: A/S/P clean — encoding verified byte-for-byte against "Привет
  Мир.pdf" UTF-8; literal-pinned (no runtime re-encode = no tautology). Pre-existing Sc 2.1 test at
  line 54 (`content-disposition == "attachment; filename=document.pdf"` for a default-filename
  RenderedExport) left UNTOUCHED — green must update it.
  > GREEN must: (1) RFC 5987 percent-encode `rendered.filename` into
  >   `Content-Disposition: attachment; filename*=UTF-8''<quote(filename, safe='')>` (`.`/unreserved
  >   literal, space→%20, Cyrillic→%XX) — encoding lives in the rest adapter per ADR. (2) UPDATE the
  >   existing Sc 2.1 test (line 54): a default-filename `RenderedExport` now yields
  >   `attachment; filename*=UTF-8''document.pdf` — either update that assertion or give the test an
  >   explicit filename; and REMOVE the now-redundant `RenderedExport.filename = "document.pdf"`
  >   default (ADR) so every construction supplies it. (3) This FIXES the still-RED Sc 3.1 acceptance
  >   AND the Sc 2.2 docx-`.pdf` mislabel carry-forward.
- [~] green-adapter rest (export filename)
- [ ] green-acceptance

### Scenario 3.2: A document with no title uses a default filename
> CARRY-FORWARD (from Sc 2.2 green-acceptance premortem, commit 5e00082 — CONCERNS CREDIBLE): the
> rest route hardcodes `Content-Disposition: attachment; filename=document.pdf` for EVERY export
> (document_router.py:~118), so a `format=docx` download currently ships valid wordprocessingml bytes
> under a `.pdf` name — Windows/Word opens it as a corrupt PDF. Sc 2.1/2.2 left the filename out of
> scope (deferred here + 3.1), but no DOCX-aware test asserts the extension, so it is unguarded. When
> 3.1/3.2 derive the filename, the extension MUST follow the export format (`.docx` for docx, `.pdf`
> for pdf), and red-acceptance MUST assert the docx `Content-Disposition` filename ends in `.docx`
> (parse the `filename=` token, not just `startswith("attachment")` as the 2.2 assert does).
> NOTE (from Sc 3.1 red-usecase review): Sc 3.1 already pins the `title=None → "document.pdf"` default
> at the usecase layer. Sc 3.2 should NOT re-pin that exact case — cover what 3.1 doesn't: empty-string
> vs whitespace-only title, and the persisted-null path end-to-end (acceptance).
> CARRY-FORWARD (from Sc 3.1 green-adapter rest premortem, commit c678cce — CONCERNS CREDIBLE, data
> loss): the db CAS preserve-on-omit guard fires only on `title is None`. An empty-string `title=""`
> is NOT None, so it PASSES the guard and executes `SET title = ''`, silently OVERWRITING a
> previously-stored title — the exact wipe the None-guard was built to prevent, one branch over. No
> test at any layer pins `title=""` behavior. Sc 3.2 must decide + pin the empty-string semantics:
> either reject/normalize `""`→None at the save boundary (so it can't overwrite), or make it a
> deliberate documented overwrite. Also unbounded: the `documents.title` column is `String()` with no
> length cap and no usecase validation (contrast content's MAX_CONTENT_LENGTH) — a title length bound
> is owned by Sc 3.6 (grapheme truncation) or the save-validation contract.
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.3: A title with header-breaking characters cannot inject into the header
> CARRY-FORWARD (from Sc 3.1 red-adapter rest export-filename premortem, commit f0dabd6 — CONCERNS
> CREDIBLE): the Sc 3.1 export-filename RED pins ONLY a well-behaved Cyrillic title, so it does not
> force a control-char-safe encoder — a naive "encode only bytes>127" green would pass it yet leave a
> raw `\r\n` in the header. The Sc 3.1 green is directed to use `quote(filename, safe='')` (encodes CR
> `%0D`/LF too — injection-safe by construction), but nothing at the REST layer ASSERTS it. Sc 3.3
> must add a **rest-layer** injection test (mock usecase returns `RenderedExport(filename="a\r\nb.pdf")`
> → assert the emitted `Content-Disposition` contains NO literal CR/LF), NOT only the ADR's
> usecase-strip test — so the encode correctness is defense-in-depth, not trusted-by-construction and
> never checked. Also note the ADR chose `filename*`-only (no legacy plain `filename=` fallback) — a
> deliberate RFC 6266 trade-off, ancient clients get the URL-segment name; not a defect.
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.4: Multibyte content renders intact
> CARRY-FORWARD (from Sc 2.1 green-adapter rendering premortem, commit c9c9a4d): the render test
> pins STRUCTURE only (%PDF- / %%EOF / len>500). Tofu boxes (□□□) are still glyphs and still
> kilobytes, so a font-coverage regression (e.g. fonts-dejavu-core dropped/renamed in one of the
> three apt lists) would ship green. This scenario must assert the ACTUAL Cyrillic glyphs survive —
> extract text/font info from the rendered PDF (e.g. pypdf) and assert the input text is present as
> embedded glyphs, not just that a PDF came back. Structure-only is not enough for a Russian product.
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
> CARRY-FORWARD (from Sc 2.2 green-adapter rendering reviews, commit 47c1adc — agent-review CONCERNS
> + premortem BLOCK, both CREDIBLE, independently confirmed against htmldocx 0.0.6 source): the DOCX
> path has a LATENT SSRF the PDF path does not. `HtmlDocxRenderer` builds `HtmlToDocx()` with default
> options where `images=True`, so `handle_img` calls `urllib.request.urlopen(src)` for any
> `<img src="http://…">` in the stored content — a server-side fetch of attacker-chosen URLs (e.g.
> `169.254.169.254` metadata) during export, no allowlist, no timeout. It is only NON-live today
> because the nh3 sanitizer's `_ALLOWED_TAGS` excludes `img`, stripping images before storage — a
> guard in a DIFFERENT adapter module. Add `img` to that allowlist and the DOCX path silently gains
> the hole while the PDF path (disabled `url_fetcher`) stays safe. Two defects to close here:
>   (1) Disable image/URL resolution at the htmldocx boundary explicitly (e.g. `HtmlToDocx()` with
>       image handling off), mirroring the PDF renderer's local `_blocked_url_fetcher` — DOCX
>       SSRF-safety must not depend on a cross-module allowlist. Add a DOCX adapter test feeding
>       `<img src="http://…">` and asserting NO outbound fetch (patch/assert urlopen never called).
>       Note: WeasyPrint suite ALSO lacks a live SSRF test exercising `_blocked_url_fetcher` — add one
>       for the PDF path too so 4.1 covers both engines, not just prose.
>   (2) FALSE DOCSTRING shipped in 47c1adc: `html_docx_renderer.py` claims "SSRF-safe by construction
>       (the parser resolves no external URLs)" — inaccurate for htmldocx's default config. Also the
>       redaction comment overstates python-docx's default (it sets creator="python-docx", a literal,
>       NOT an OS username — redaction is still good hygiene, but correct the rationale). Fix both
>       comments when 4.1 hardens the path.
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
> CARRY-FORWARD (from Sc 2.1 green-usecase reviews, commit 26c1d66 — agent-review + premortem):
> the `DocumentRenderer.render` port is SYNCHRONOUS and called directly inside the `async def
> execute`. Once the real WeasyPrint adapter lands (CPU-bound), a render pegs the event-loop thread
> and stalls co-tenant endpoints on that instance for the render's duration. This load scenario must
> assert export concurrency does not stall an unrelated endpoint, and the fix (offload the sync
> render, e.g. `asyncio.to_thread`/`run_in_executor`, plus a concurrency bound) belongs here / Sc 4.2.
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
