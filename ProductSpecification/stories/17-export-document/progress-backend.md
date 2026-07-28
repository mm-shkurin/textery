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
- [x] green-adapter rest (export filename) — GREEN (host, mocked usecase): target
  `TestExportFilenameRfc5987` PASSED (header matched the RFC 5987 literal exactly); router/document
  suite 28 passed, full rest suite 76 passed, usecase 172 passed — 0 regression. Export route now
  `from urllib.parse import quote` + `encoded = quote(rendered.filename, safe="")` →
  `Content-Disposition: attachment; filename*=UTF-8''{encoded}` (replacing the hardcoded
  `filename=document.pdf`). `safe=""` percent-encodes control chars too (CR→%0D/LF→%0A) —
  injection-safe by construction (premortem obligation). Regression fixes: (1) `RenderedExport.filename`
  default removed — now a REQUIRED field (ADR); grep confirmed only 3 construction sites (usecase +
  the 2 tests), all supply it. (2) Sc 2.1 test `TestExportDocumentAsPdfResponse` updated — explicit
  `filename="document.pdf"` + assertion `attachment; filename*=UTF-8''document.pdf` (strict). Coverage:
  export encoding line + header + 404 branch 100% (only the known DI-stub NotImplementedError lines
  uncovered, out of scope).
- [x] green-acceptance — GREEN live against the rebuilt backend (BACKEND_PORT=8100): 9 passed, 0
  failed, 0 skipped in `test_export_document_acceptance.py`. Only change: removed the RED
  `@pytest.mark.skip` from `test_export_filename_is_rfc5987_encoded_from_cyrillic_title` (no
  production code touched — the usecase/db/rest greens already carried the behavior). The full
  write→read→encode chain is now proven end to end through real HTTP + real Postgres: save with
  `title="Привет Мир"` persists (DTO + CAS), export derives `"Привет Мир.pdf"` in the usecase, and the
  rest route emits `Content-Disposition: attachment; filename*=UTF-8''%D0%9F%D1%80%D0%B8%D0%B2%D0%B5%D1%82%20%D0%9C%D0%B8%D1%80.pdf`
  exactly. Migration `a3b4c5d6e7f8` applied cleanly on container start (`alembic upgrade head` runs in
  the backend CMD), so the db-suite migration-harness quirk does NOT affect the compose path.
  Scenario 3.1 complete.

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
- [x] red-acceptance — RED confirmed live (BACKEND_PORT=8100): predicted == actual on all 4 cases,
  first run, no loop. New class `TestExportFilenameDefaultWithoutTitle` (2 parametrized tests) +
  statements `given_owner_exports_untitled_document` / `assert_default_filename` /
  `given_owner_saves_a_blank_title_over_a_stored_title_and_exports`.
  TEST 1 (`[pdf]`/`[docx]`) — the spec Gherkin, an ALREADY-GREEN regression guard (not a fabricated
  RED, verified live): a freshly created document (persisted-null title, end to end) exported as
  pdf/docx pins the FULL `Content-Disposition` literal `attachment; filename*=UTF-8''document.pdf` /
  `...document.docx`. This RESOLVES the Sc 2.2 docx-extension carry-forward — Sc 3.1's green already
  sources the extension from `ExportFormat.value`, and the extension is now parsed out of a pinned
  filename token (never `startswith("attachment")`), so it cannot regress. Committed ENABLED per the
  Sc 1.2 / 2.4 precedent.
  TEST 2 (`[empty_title]`/`[whitespace_title]`) — the genuine RED, skip-marked. DECISION on the
  empty-string carry-forward: a blank title (`""` or whitespace-only) carries NO title intent and
  must NOT overwrite a stored one — same semantics as omitting the field, which the CAS `title is
  None` guard already honours. Setup saves title "Привет Мир", then a content-only autosave
  submitting a blank title, then exports; the filename must still be the Cyrillic RFC 5987 literal.
  Actual: `[empty_title]` got `attachment; filename*=UTF-8''document.pdf` (CAS ran `SET title = ''`,
  then `"" or "document"` → default); `[whitespace_title]` got `attachment; filename*=UTF-8''%20%20%20.pdf`
  — whitespace-only doesn't merely wipe the title, it yields a garbage "effectively empty" filename,
  which the spec's *"never empty or null"* clause forbids on its own terms.
  test-review: A5/A7 + A27 + S11×2 fixed — `assert_default_filename` pinned only status +
  disposition, leaving `content_type`/`content`/`body` unasserted (a route returning PDF bytes under
  `document.docx` would have passed); now the full `ExportResponseDto` envelope is compared in one
  frozen-dataclass equality (`ExpectedExportEnvelope`) plus a per-format magic-byte check
  (`%PDF-` / `PK\x03\x04`), and Sc 3.1's `assert_filename_rfc5987_encoded_from_title` converges on
  the same strict helper. 11 passed / 2 skipped / 0 failed.
  ⚠️ FILE-SIZE GATE (blocks Sc 3.3): `document_export_filename_statements.py` is at 193/200 and
  `test_export_document_acceptance.py` at 167/200 — Sc 3.3 must split before it can add.
  ⚠️ HARNESS GOTCHA: `acceptance/clients/application/application_client.py:24` reads
  `os.environ.get("BACKEND_PORT", "8000")` and pytest does NOT auto-load `infra/.env` — a bare
  `pytest` silently targets 8000 and fails every test at connect, which reads as a regression.
  GREEN must: normalize a blank title to None at the save boundary (`title.strip() or None`) so it
  reaches the CAS as None and hits the existing preserve-on-omit branch. `design` decides whether
  that lands in `SaveDocumentRequestDto`, `SaveDocument.execute`, or the domain — red-agent's read is
  the usecase, keeping the rest DTO a dumb transport and the CAS guard on a single `is None`.
> DESIGN OBLIGATIONS (from the Sc 3.2 red-acceptance review passes over commit ab97072 —
> agent-review CONCERNS ×3 + premortem CREDIBLE ×3, converging on the first three):
> 1. **No way to clear a title (BOTH passes, CREDIBLE).** After the planned green, `None`, `""` and
>    `"   "` all mean "preserve" — and `title: str | None = None` is the only write surface — so NO
>    wire value can remove a stored title. A user who clears the title field sees it come back on
>    reopen and on every export filename. The spec clause that justified the decision
>    (`17_ExportDocument_Notes.md:45` "never empty or null") constrains the FILENAME, not the stored
>    title — wiping to NULL satisfies it too (export falls back to `document.pdf`). `design` MUST put
>    the clearing affordance on record and pin it with a test: either an explicit clear signal (e.g.
>    JSON `null` clears, omitted preserves) or a documented "titles are replaced, never cleared".
> 2. **`title.strip() or None` silently trims legitimate titles (agent-review).** It does two things:
>    blank→None (intended) AND trims every real title (`" Отчёт "` → `"Отчёт"`). Nothing can detect
>    it — Sc 3.1's `"Привет Мир"` has only an internal space, so a trimming and a non-trimming
>    implementation (`if title is not None and not title.strip(): title = None`) are indistinguishable
>    under the whole current suite. Add a leading/trailing-whitespace case asserting either verbatim
>    round-trip or a documented trim.
> 3. **The fix is write-path-only; derivation keeps its falsy-only fallback (premortem).**
>    `export_document.py:46` is `stem = document.title or "document"` — `"   "` is truthy and survives
>    to `%20%20%20.pdf`. Rows written BEFORE the green (today's `SET title = ''` is live), or by a
>    migration/import/admin tool/future create-with-title endpoint, bypass the save boundary and
>    reproduce the incident forever. Make it defense in depth: `strip()` in the derivation too, plus a
>    `whitespace_title_default` case in `test_export_document_usecase.py` (currently only
>    `cyrillic_title_pdf` / `cyrillic_title_docx` / `absent_title_default`).
> 4. **Test 2 can't distinguish "title preserved" from "the whole blank save was a no-op"
>    (agent-review).** The blank save resubmits the SAME `DOCUMENT_CONTENT` and only checks
>    `status_code == 200`, so a green that rejects/short-circuits the entire blank-title save — losing
>    the content update — passes identically. That is the exact regression the test exists to exclude,
>    since the premise is a CONTENT-ONLY autosave. Send distinct content on the blank save and assert
>    it persisted (or that the version advanced to 3). Fix during green.
> 5. **Sequencing (premortem, not a finding):** the skip-marked test documents a LIVE production
>    data-loss path — today any autosave submitting an empty title destroys a stored title, which a
>    frontend mount/hydration race can trigger. Argues against letting this green sit behind other work.
> Title LENGTH bound (premortem CREDIBLE 3) is a restatement of the cap already carried forward to
> Sc 3.6 / Infra 3.1 in c00c2f5 — no new obligation here beyond noting that truncating the filename
> STEM in `ExportDocument` bounds the header regardless of what is stored.
- [x] design — see `decisions/blank-title-semantics-decision.md` (ADR). The title field is
  THREE-STATE, distinguished by what the client SENT, not by the value alone: key absent → preserve;
  `""`/whitespace-only → preserve; `null` → CLEAR (`SET title = NULL`); a real string → store
  VERBATIM. Blank preserves because a blank title is the default shape of "nothing to say about the
  title" (hydration race, partially-initialised form, client that always serialises the field) — a
  wipe must not be the failure mode of an ordinary frontend bug, so clearing gets the shape a client
  cannot send by accident. `null`-vs-absent is distinguishable ONLY via Pydantic `model_fields_set`
  in the route (both collapse to `None`), which is the RFC 7396 merge-patch convention. REJECTED
  `title.strip() or None` (review obligation 2): it silently trims every legitimate title
  (`" Отчёт "` → `"Отчёт"`) and nothing in the suite can detect it — blankness is tested with
  `title.strip() == ""`, the stored value is never rewritten. DEFENSE IN DEPTH (review obligation 3):
  `ExportDocument` derives `stem = (document.title or "").strip() or "document"` INDEPENDENTLY of the
  save boundary, because rows written before this green (today's `SET title = ''` is live) or by a
  migration/import/admin tool bypass the save path and would reproduce `%20%20%20.pdf` forever.
  PORT CHANGE: `title: str | None` can no longer express intent (`None` is now ambiguous between
  preserve and clear) — a domain `TitleUpdate` VO (`preserve()` / `clear()` / `of(value)`) carries
  the three states so Pydantic never reaches the usecase and the CAS maps them explicitly.
  Review obligation 1 (no way to clear a title) is CLOSED by the `null` affordance; obligation 4
  (Test 2 can't tell preserve from whole-save no-op) is scheduled below.
- [x] red-usecase — RED confirmed live on the host: predicted == actual on all 4 cases, first run,
  no loop. 3 failed / 305 passed; after skip-marking, 305 passed / 3 skipped / 0 failed.
  `[empty_title_preserves]` → `AssertionError: expected TitleUpdate(value=None) forwarded to the
  repository, got TitleUpdate(value='')`; `[whitespace_title_preserves]` → same with
  `TitleUpdate(value='   ')` (execute forwards `title` to the port unchanged);
  `[whitespace_title_default]` → `AssertionError: expected filename 'document.pdf' for title '   ',
  got '   .pdf'` (`stem = document.title or "document"`, `"   "` is truthy).
  `[padded_title_verbatim]` PASSED — an already-green guard, kept ENABLED on purpose: it exists so
  GREEN cannot adopt the ADR-rejected `title.strip() or None`.
  New: domain `TitleUpdate` VO (22 lines) with `preserve()` / `of()` and ONE field — the domain-field
  gate REMOVED the `clears` discriminator, since no line in this step reads it; `clear()` arrives
  with its own red step, exactly as the ADR scheduled. New `save_document_statements.py` +
  `test_save_document_title.py`; `SaveStatements` moved out of `test_save_document_usecase.py` (was
  178, over-cap risk). Disabling is per-`pytest.param` `marks=pytest.mark.skip`, NOT a method-level
  skip, so the three already-green derivation cases and the verbatim guard stay enabled.
  test-review: A×4 fixed. The important one — `assert_forwarded_title_update` asserted only
  `title_updates[-1]`, so a usecase that mangled the SETUP title or forwarded twice per `execute`
  passed anyway; it now pins the whole sequence (`[of(STORED_TITLE), expected]`), which also pins the
  call count and makes the `padded_title_verbatim` guard actually load-bearing. Also: a length-only
  `len(saved.content) == 200_000` → full equality, and two `RenderedExport` happy paths that left
  `filename` unasserted → whole-object comparison.
  ⚠️ TYPE-LEVEL RED MARKER: `save_document_statements.py` carries three `# type: ignore[arg-type]`
  (mypy checks the test tree, and rewriting the port signature is a GREEN change, not a RED one).
  GREEN widens `title: str | None` → `TitleUpdate` on BOTH the port and `execute` and deletes them —
  if they survive GREEN, GREEN didn't do the port change.
  ⚠️ PRE-EXISTING, outside this diff: `ruff check .` is red at 5 findings on this branch —
  `adapters/rendering/.../html_docx_renderer.py:32` + `weasyprint_pdf_renderer.py:8,8,34` (ARG001/
  ARG002 on Protocol-conformance params) and `adapters/rest/tests/router/document/
  test_save_document_title_router.py:4` (F401 unused `pytest`, left at Sc 3.1 green-adapter rest).
  ⚠️ PLACEMENT DEBT (reported, deliberately not fixed in a RED review): `test_export_document_usecase.py`
  has NO Statements class at all — fakes, factory, execute and assertions all live in the test class;
  `test_save_document_usecase.py` reaches through `statements.repository` / `statements.usecase`
  instead of DSL steps. Both predate this unit; `/refactor` owns them.
  ⚠️ CAP PRESSURE: `document_fakes.py` 185 and `test_export_document_usecase.py` 183 — the next fake
  or export case crosses 200.
- [x] red-usecase (padded derivation) — RED confirmed live: predicted == actual, first run, no loop.
  `AssertionError: expected filename 'Отчёт.pdf' for title ' Отчёт ', got ' Отчёт .pdf'`
  (`export_document.py:46` derives `stem = document.title or "document"`; `" Отчёт "` is truthy, so
  the padding survives and the extension is appended to the padded stem). One new `pytest.param`
  `[padded_title_stripped]` in the existing derivation parametrization, added through the
  `ExportStatements` DSL seam; per-`pytest.param` skip so the four already-green cases stay enabled.
  305 passed / 4 skipped / 0 failed; mypy clean (151 files, run from `backend/`).
  test-review: NO violations, nothing to fix. Two things it confirmed that make the case non-vacuous:
  the expected filename is a hardcoded literal (a computed `title.strip() + "." + fmt` would have
  mirrored the production rule under test and passed vacuously), and `stored_document` passes `title`
  verbatim into `Document(title=title)` with no strip — had the fake laundered it, the case would
  have been a no-op.
  ⚠️ mypy must run from `backend/` — the per-layer `sys.path` roots live in `backend/pyproject.toml`,
  so running it from the repo root reports 132 spurious `import-not-found` errors.
  ⚠️ PRE-EXISTING, not fixed in a RED unit (would mean editing untouched lines):
  `test_export_document_usecase.py:164` raw inline `assert` in
  `test_every_export_format_resolves_to_a_media_type`; `:37` imports the private `_MEDIA_TYPE` into
  the test class; `export_document_statements.py:46` instantiates `FakeDocumentRepository` inside
  Statements.
  ORIGINAL RATIONALE — INSERTED by the review passes over the red-usecase commit
  (`60ab441`, agent-review CONCERN 2). This diff creates the input and leaves the output unguarded:
  `padded_title_verbatim` guarantees `" Отчёт "` is STORED verbatim, and `whitespace_title_default`
  only pins the all-blank case, so a green that satisfies it with a blankness TEST rather than a
  STRIP (`stem = title if title.strip() else "document"`) passes all four cases and derives
  `" Отчёт .pdf"` → `Content-Disposition: …%20%D0%9E…%20.pdf`. Both decisions are individually
  correct; their intersection is untested. Add the param `(" Отчёт ", "pdf", "Отчёт.pdf")` beside
  `whitespace_title_default` — it must be a RED step, since green may not add tests.
- [x] red-usecase (export leaves the stored title untouched) — REORDERED here from the green step's
  obligation list: both items are TEST changes, and green may not write tests. Both landed as
  ALREADY-GREEN regression guards (predicted no failure, got no failure — Sc 1.2 / 2.4 precedent,
  not a fabricated RED): usecase + domain 305 passed / 4 skipped, acceptance 11 passed / 2 skipped,
  mypy clean. No skip mark added or removed.
  (1) `assert_stored_document_unchanged` on `ExportStatements` — called after `when_exporting` for
  EVERY derivation param (the invariant isn't padded-specific; the padded case is where it becomes
  load-bearing). (2) Sc 3.2 acceptance Test 2 now sends `BLANK_SAVE_CONTENT` — distinct from
  `DOCUMENT_CONTENT` — on the blank-title save, re-reads via `get_document`, and pins that content
  survived, so a green that rejects or short-circuits the whole blank-title save can no longer pass.
  VACUITY PROVEN BY MUTATION (test-review did not take the guard on trust): it injected
  `document.title = ....strip()` into `export_document.py`, the guard went RED
  (`expected None, got ''`), and the file was restored. A constructor strip is caught too — the
  explicit title pin compares against the RAW parametrized title, so a strip that also strips the
  snapshot still fails. ⚠️ The one green this CANNOT catch is a strip in `DocumentModel.to_domain()`
  — the fake has no mapper, so that path is unreachable at this layer; the docstring was narrowed
  rather than left overclaiming. The db-adapter round-trip test is where that one has to be pinned.
  test-review: 7 findings fixed across 4 files. Notably — the guard originally read back through
  `repository.find_by_id_and_owner` (rule 24, storage port in Statements, "NO EXCEPTIONS"); it now
  reads through `GetDocument`. It also re-read a 10-field entity and pinned ONE field; it now
  snapshots every field in the arrange and compares the whole entity, so an export that bumped
  `version` or rewrote `content` fails. `assert_filename_is` pinned 1 of `RenderedExport`'s 3 fields
  across all five params → folded into `assert_export_is`. An `isinstance(version, int)` that passed
  for a version the CAS never incremented → exact literals (2 → 3). The acceptance `get_document`
  asserted NOTHING (a 404/500 collapsed to `None`) → now pins 200 + a full structural comparison.
  ⚠️ NOT FIXABLE IN A TEST REVIEW: the acceptance re-read cannot pin `title` directly —
  `DocumentResponseDto` has NO title field, so no endpoint returns it and the export header is the
  only black-box observation of title survival that exists. (Same read-model gap already recorded
  under `green-acceptance`.)
  ⚠️ FOUND WHILE RUNNING, PRE-EXISTING AND UNRELATED: the full `acceptance/tests/backend` tree has
  5 failures + 2 errors in the GENERATION and OAUTH suites (401 `UNAUTHORIZED` on generation
  endpoints). Nothing in this diff is shared with them, and the export-scoped counts above don't
  cover them — but the acceptance tree is red outside this story.
  ⚠️ CONFIRMED AGAINST THE REAL BACKEND: test-review temporarily lifted the acceptance skip; the new
  content-survival assertion PASSED before the test failed on the genuine RED reason
  (`%20%20%20.pdf`). So today's blank-title save does persist its content and increment the version
  normally — only the title is wiped. Skip marker restored.
  ⚠️ FOLLOW-UPS from the review passes over `f0e6e7d` (agent-review CONCERNS ×4), for whichever step
  next touches these files — none blocks green:
  • The whole-entity guard detects an in-place mutation ONLY because `FakeDocumentRepository.save_new`
    appends the caller's instance and `find_by_id_and_owner` returns that same object. The docstring
    names that premise; NOTHING asserts it. A reasonable future hardening of the shared fake (return
    a copy on read, mirroring a real repo's detached entity) turns the guard permanently green and
    blind, with no failing test anywhere. The mutation proof was a point-in-time one; an identity pin
    (`stored is` the arranged instance, or a test over the fake itself) makes it standing.
  • The explicit raw-title pin is INERT for every param that currently runs — the three live params
    are `"Привет Мир"` ×2 and `None`, where a constructor strip is the identity function. It bites
    only on `"   "` and `" Отчёт "`, both skip-marked. Not a hole (green lifts them), but the
    docstring claims a proof today's suite does not deliver — narrow the wording as the mapper-strip
    claim already was.
  • ~50 lines of new acceptance assertion code are reachable ONLY from the skipped test, so a wrong
    key name or bad constant sits undetected until green. Also, the "whole document is pinned" comment
    overstates: `{k: body.get(k) for k in expected} == expected` is a SUBSET comparison, so a new
    response field — notably `title`, which story-5-extension adds — slips through unpinned, and
    title survival is exactly what this scenario guards.
  • "mypy clean" does NOT cover `acceptance/` — mypy is configured in `backend/pyproject.toml` and
    the acceptance tree is outside type-check scope. Concretely `self._reread_after_blank_save = None`
    was left unannotated where its sibling one line above is `str | None`; under a checker the
    inferred `None` would reject the later DTO assignment.
- [x] red-adapter db (padded title round-trip) — ALREADY-GREEN regression guard confirmed live
  against real Postgres (localhost:5432): predicted PASS, got PASS, first run. 55 passed / 0 failed /
  0 skipped; the new test genuinely RAN (`-rs`: 3 collected, 3 passed, 0 skipped). mypy clean.
  `test_should_round_trip_a_padded_title_byte_identically` saves `" Отчёт "` through the version-CAS
  writer and asserts it reads back byte-identical after `expire_identity_map()` — the seam matters:
  the session is `expire_on_commit=False` and the CAS `RETURNING` caches the row in the identity map,
  so without a genuine SELECT re-hydration the assertion reads off the cached instance and the guard
  is vacuous. No live bug — today's mapper passes `title` through unchanged; the value is that the
  third door is CLOSED BEFORE green is written.
  NON-VACUITY PROVEN BY MUTATION: test-review mutated `DocumentModel.to_domain` to
  `title=self.title.strip()` → 1 failed, 2 passed. Only the padded test died, confirming both that
  the guard bites AND the premise that it is the only test in the repo that can observe a mapper
  strip. Mutation reverted (`git diff` over src/domain/usecase empty).
  ⚠️ ASYMMETRY, recorded rather than papered over: a `.strip()` in `from_domain` would NOT be caught.
  The title on this path is written by the CAS `update().values(...)` dict, which never routes
  through `from_domain` — only the READ side is pinned. The docstring's claim to cover both
  overstated by half and was narrowed.
  test-review: 7 findings fixed. THE REAL ONE — `test_should_preserve_an_existing_title_on_a_content_only_save`
  was satisfiable BY DOING NOTHING: it asserted only `title == "Привет"` after a second content-only
  CAS, but an unchanged title is exactly what a CAS matching ZERO rows leaves behind. It now pins
  `version=3` and the new content, so "the save actually happened" is observable. Also: all three
  tests checked `title` while `content` and `version` — written by the same CAS call — went
  unverified (new `assert_stored_state`); the shared `assert_documents_match` omitted `title`,
  `created_at` and `updated_at`, so it could not have caught a title corruption (now all 10 persisted
  fields); and `save_content_with_title` was byte-identical to `save_content_if_version_matches` plus
  one kwarg, inventing a storage operation that does not exist — collapsed into the real one.
  ⚠️ REVIEW FINDINGS over `ab40007` — agent-review CONCERNS ×3, premortem 2 CREDIBLE, and BOTH
  independently landed the same #1, which is a real hole in THIS unit's collateral changes:
  • `assert_documents_match` was widened 7 → 10 fields with the comment "every persisted field …
    cannot hide behind a subset" — but the claim is FALSE at both (and only) call sites,
    `test_document_storage.py:17` and `:85`. Neither calls `expire_identity_map()`. `save_new` does
    `session.add(DocumentModel.from_domain(document))`, the session is `expire_on_commit=False`, and
    the later `select()` is deduplicated against the identity map, so SQLAlchemy returns the SAME
    instance and `to_domain()` reads back the Python attributes `from_domain` just set. The new
    fields assert `x == x`; the DB's stored bytes are never observed. This is the exact trap the
    padded-title test three files over was written to avoid — the seam was not carried along. FIX:
    `expire_identity_map()` before the read in both tests, then prove it by mutating
    `to_domain` (`title=None` or a fresh `created_at`) and confirming they go RED.
  • That is ALSO where the conceded `from_domain` gap could be closed: `save_new` IS the
    `from_domain` write path, and those two tests are the only ones traversing it write→read. Both
    were touched here and left warm-cached. Premortem rates the insert path CREDIBLE precisely
    because the asymmetry became a NOTE while the other two doors became STEPS — "a recorded
    asymmetry with no step and no test is indistinguishable from an unrecorded one at the moment the
    green is written". Concretely: construct a `Document` with `title=" Отчёт "`, persist via
    `save_new`, expire, assert the padding survived (~5 lines on machinery this unit already built).
    Mitigating today: `Document.create` takes no title, so `from_domain` always carries `title=None`
    and a `.strip()` there would `AttributeError` loudly.
  • `assert_stored_state` docstring claims "the full post-CAS state" but pins 3 of the 4 columns the
    CAS writes — `updated_at` is written by the same `values` dict and is still unverified in all
    three tests, by the helper introduced to close exactly that class of gap. Pin monotonicity
    (`> created_at` / `>` the pre-save value), not an exact literal — the DSL generates it.
  • The collapsed DSL comments `title=None` as "the content-only autosave path", written as durable
    semantics that the accepted ADR INVERTS (`None` becomes clear under `TitleUpdate`). Narrow the
    wording. Guarded — `test_should_preserve_an_existing_title_on_a_content_only_save` now pins
    `version=3`, so a `None → clear()` mismatch goes RED.
  • STALE: discovery guard (b) below still reads "which today covers round-trip and preserve-on-omit
    only" — this unit added a third case.
  ORIGINAL RATIONALE — INSERTED by the premortem over `f0e6e7d` (CREDIBLE,
  and the reason it is a STEP rather than a note): the previous guard closed the two placements a
  green reaches for first — in-place mutation in `ExportDocument`, and `Document.__init__` — and
  left the third open. Squeezing two of three doors shut ROUTES the green toward the survivor:
  `.strip()` on the read side of the mapper (`document_model.py:84`, `title=self.title`), or the
  write side at `:66`. Every read then returns the stripped value, an ordinary autosave is a
  read-modify-write, and the next content-only save PERSISTS the wipe — verbatim the failure the ADR
  forbids. Nothing in the repo can see it, because every title on a real write→read path is
  UNPADDED, so `.strip()` is the identity function everywhere it could be observed: the usecase
  guard's fake has no mapper (acknowledged); `test_should_round_trip_a_saved_title` and
  `test_should_preserve_an_existing_title_on_a_content_only_save` both use `"Привет"`; the
  acceptance filename assertion uses `"Привет Мир"` AND derives the header through the strip anyway;
  and `padded_title_verbatim` pins what reaches the PORT and never re-reads. THE GUARD: save a
  PADDED title (`" Отчёт "`) through the CAS and assert it reads back byte-identical after
  `expire_identity_map()` — in `backend/adapters/db/tests/access/document/test_document_storage_title.py`,
  against real Postgres. It was previously recorded only as an OPTIONAL branch ("and/or") of an
  obligation whose other branch is already satisfied, so it read as discharged; and green may not
  write tests, so without this step green runs with the path open.
- [x] green-usecase — GREEN: usecase+domain 309 passed / 0 skipped / 0 failed; whole `backend/`
  532 passed / 2 skipped / 0 failed (the 2 are pre-existing `importorskip` skips on
  `htmldocx` / `weasyprint`, absent on the host — see carryover); adapters/rest 76 passed,
  adapters/db 55 passed against real Postgres; mypy clean (280 files, run from `backend/`).
  Production: port `DocumentRepository.save_content_if_version_matches` widened
  `title: str | None` → `TitleUpdate | None`; `SaveDocument.execute` takes the VO and maps blank →
  `TitleUpdate.preserve()` via a `strip() == ""` TEST (the stored value is never rewritten, per the
  ADR's rejection of `title.strip() or None`); `ExportDocument` derives
  `stem = (document.title or "").strip() or "document"` with the entity untouched;
  `document_storage.py` unwraps the VO before the CAS `values` dict. All three
  `# type: ignore[arg-type]` RED markers deleted — their disappearance is the proof the port
  signature actually moved (mypy surfaced conformance errors at `document_wiring.py` the moment it
  did). All four RED per-param skip marks deleted and the drop 4 → 0 verified with `-rs`.
  ⚠️ DEVIATION, deliberate and scoped: `SaveDocument.execute` and the db storage accept
  `TitleUpdate | str | None` at those two boundaries only — the domain port itself is
  `TitleUpdate | None`, unpolluted. Both adapter boundaries are pinned by read-only tests that still
  speak `str` (`test_save_document_title_router.py:57` asserts `execute(..., title="Привет Мир")`;
  `document_storage_statements.py:54` forwards a bare `str`), and green may not edit tests —
  but dropping the `str` arm without them ships `AttributeError` on every titled save. No
  `type: ignore` was added in production code. `adapters-discovery` guards (a)/(b) remove the union;
  until then the ADR's "`None` is ambiguous" argument is only half-enforced.
  ⚠️ Discharged earlier, not here: review obligation 4 (acceptance Test 2 sends distinct content)
  and the `assert_stored_document_unchanged` guard both landed in the
  `red-usecase (export leaves the stored title untouched)` step — green wrote no tests.
  test-coverage (usecase --focus): 100% line + branch on all four changed files, but the headline is
  MISLEADING and the agent proved it by mutation — see the inserted `red-adapter db (TitleUpdate
  unwrap)` step below.
  refactor (commit follows this one): 4 refactorings — `TitleUpdate.is_blank()` (the blank rule moved
  onto the VO that owns it), `_update_values` extracted in `document_storage` (which also CONFINES
  the transitional unwrap to one method, so removing the `str` arm is deleting a line rather than
  hunting for it), `_derive_filename` extracted from `ExportDocument.execute`, and a derivable
  `owner_id` parameter dropped from four `save_document_statements` helpers. Two detector findings
  were REJECTED after verification (`rollback_call_count` is live — the detector matched the reads
  against a different `FakeUnitOfWork`; dropping `version: int = 1` is technically correct but the
  default is what makes `test_save_document_usecase.py:111` stale). Also: the PLACEMENT DEBT this
  step inherited from `red-usecase` was ALREADY resolved by earlier refactor commits — the debt note
  was stale. 309 passed usecase+domain, 532/2 backend, 55 db vs Postgres, mypy clean (297 files),
  ruff byte-identical to the pre-existing 5. No file over 179 lines — the cap pressure was overstated.
> REVIEW FINDINGS over `83e4e48` — agent-review CONCERNS ×2, premortem 2 CREDIBLE + 3 REMOTE. BOTH
> passes independently landed the SAME #1, which makes it the finding to act on first:
> • **The port has two encodings of "preserve", and the raw one is what production sends
>   (BOTH passes, CREDIBLE).** `document_repository.py` gained a docstring stating the ADR's premise —
>   "a bare `None` can no longer tell 'preserve' from 'clear'" — while the signature one line above
>   stayed `title: TitleUpdate | None = None`, and `_title_intent` RETURNS a bare `None` for the
>   absent case. So the single most common call in the app (content-only autosave) crosses the port
>   carrying the exact value the port's own docstring declares unusable. The tax is already being
>   paid downstream in both implementors: `document_storage` collapses in two steps (unwrap `.value`,
>   then absorb the raw `None`), and `document_fakes.py:115` double-guards
>   `title is not None and title.value is not None`. THE INCIDENT: the very next step is
>   `green-usecase (clear path)`, whose job is to make something mean `SET title = NULL`. An
>   implementor reading that docstring literally — `None` is not a `TitleUpdate`, therefore it is the
>   non-intent-bearing "clear" — flips the storage branch and EVERY autosave wipes its title. It also
>   collides with scheduled guard (a), which will assert absent → `TitleUpdate.preserve()`: once that
>   lands, one user intent has two representations depending on which caller you came through.
>   FIX (one line today, more expensive per guard that accumulates on top): collapse
>   `None → TitleUpdate.preserve()` inside `_title_intent` and DROP `| None` from the port.
>   MISSING GUARD: nothing pins what a content-only autosave forwards —
>   `save_title_statements.when_autosaving_with_title` always passes an explicit `TitleUpdate.of(...)`,
>   so `assert_forwarded_title_update` never sees the `None` arm; a `_title_intent` returning garbage
>   for `title=None` would not go red anywhere.
> • **The recorded deviation names a removal owner that does not own it (agent-review).** This step's
>   note scopes the `TitleUpdate | str | None` union with "`adapters-discovery` guards (a)/(b) remove
>   the union". Traced as actually written, NEITHER does: (a) only adds two `model_fields_set` route
>   assertions and never mentions the router building a `TitleUpdate` or narrowing `execute`; (b) is
>   scoped to the `SET title = NULL` SQL branch only; and the inserted `red-adapter db (TitleUpdate
>   unwrap)` step explicitly WIDENS the db DSL to `TitleUpdate | str | None` and keeps it. So as
>   recorded the two `str` arms are PERMANENT, and `execute(title="")` remains a legal call meaning
>   "set" — the exact branch this scenario's red was written to close. No guard is possible by
>   construction: a permissive union never fails type-checking. The only guard is a step that names
>   the removal, which is what was absent — now written into (a)/(b) and the db-unwrap green below.
> • **The scenario's own end-to-end guard is still skipped, and is sequenced LAST (premortem,
>   CREDIBLE).** `test_export_document_acceptance.py:141` still carries the Sc 3.2 RED skip. This step
>   verified "4 → 0 skips" over `backend/usecase`, and the `backend/` 532/2 count does NOT include the
>   `acceptance/` tree — so the one skip pinning the actual production data-loss path is precisely the
>   one the verification scope could not see. Combined with the mutation-proven fact that the db
>   unwrap arm is executed by nothing, the shipped state has ZERO executable proof of the round trip
>   through the real route and real Postgres; the usecase test asserts against a fake whose preserve
>   branch this same green wrote. FIX: `green-acceptance` is currently scheduled after the db unwrap,
>   the clear path AND adapters-discovery — pull the unskip forward to immediately after
>   `green-adapter db (TitleUpdate unwrap)`, before the clear-path work.
> • VERIFIED AND HOLDING (premortem traced it end to end): the blank path DOES close today —
>   route forwards raw `""` → `_title_intent` tests `strip() == ""` → `preserve()` → storage omits
>   `title` from the CAS `values`. No `SET title = ''` is reachable from the PUT route. What is not
>   closed is the PROOF, which is the two findings above.
> • REMOTE, already scheduled elsewhere, recorded not re-raised: `TitleUpdate.of("")` is still legal
>   so the storage arm keeps `SET title = ''` alive for any future non-route caller (owned by the
>   `of()` blank-rejection obligation on `red-usecase (clear path)`); a zero-width title still derives
>   `%E2%80%8B.pdf` (owned by Sc 3.6).
> • DECISION GAP, no test possible: rows already wiped to `''` by the live pre-green bug stay wiped,
>   and the new derivation strip MASKS them as `document.pdf` — no error, no recovery, no remediation
>   step anywhere. Flagged for a decision, not a guard.
  ORIGINAL STEP TEXT follows — also FIX the Sc 3.2 acceptance Test 2 (review obligation 4): the blank save
  resubmits the SAME `DOCUMENT_CONTENT` and only checks `status_code == 200`, so a green that
  rejects or short-circuits the whole blank-title save — losing the content update — passes
  identically. Send distinct content on the blank save and assert it persisted (or that the version
  advanced to 3).
  ⚠️ PIN THE OTHER HALF OF THE ADR SENTENCE (both review passes over `6565709`, CREDIBLE). The
  padded-derivation case asserts only `result.filename`, so NOTHING constrains WHERE green puts the
  strip. A green written as `document.title = (document.title or "").strip()` before the derivation —
  or a strip in `DocumentModel.to_domain()`, or in `Document`'s construction — produces `"Отчёт.pdf"`
  and turns ALL five params green. It is undetectable because `Document` is a plain mutable class
  (bare `self.title = title`, no frozen/`__slots__`) and `FakeDocumentRepository.find_by_id_and_owner`
  returns the SAME instance it stored, so the mutation lands in the fake's store and no later step
  reads it back. `padded_title_verbatim` does NOT cover this — it pins what reaches the port on the
  way IN and never re-reads; and `test_should_round_trip_a_saved_title` (the only read-path guard)
  uses `"Привет"` with NO padding, so a strip in the mapper is invisible to it. That is the exact
  data loss the ADR spends a section forbidding ("Stripping here affects the filename only — the
  stored title is untouched"): an ordinary autosave is a read-modify-write, so a read-path strip
  becomes a persisted wipe. Guard: `assert_stored_title_unchanged(" Отчёт ")` on `ExportStatements`,
  called after `when_exporting` in the padded case (cheapest), and/or a PADDED title in the db
  round-trip test. NOTE the two passes disagreed on scope — premortem rates a usecase-level mutation
  REMOTE because `find_by_id_and_owner` returns a detached `to_domain()` object, so the live risk is
  MAPPER/ENTITY placement specifically; agent-review rates the usecase placement live via the fake.
  The guard closes both readings, so it is worth adding either way.
  ⚠️ EXPLICIT, CHECKABLE OBLIGATION (premortem CREDIBLE 2): green MUST delete the four RED per-param
  skip marks — `whitespace_title_default` and `padded_title_stripped` in
  `test_export_document_usecase.py`, plus the two in `test_save_document_title.py` — and confirm the
  skipped count drops from 4 to 0. A skipped param is indistinguishable from a passing one in the
  headline metric: a green that implements the strip and forgets the mark still reports
  "305 passed / 4 skipped / 0 failed". Nothing in the repo asserts a skip baseline, and with six
  skips live the count is not self-policing.
- [x] red-adapter db (TitleUpdate unwrap) — ALREADY-GREEN regression guard confirmed live against
  real Postgres (`infra-postgres-1`, localhost:5432): predicted PASS, got PASS, first run, no loop.
  PREDICTED: none — `_update_values` already unwraps `title.value if isinstance(title, TitleUpdate)`,
  so `of(" Отчёт ")` yields the padded string in the SET list and `preserve()` yields `value=None` →
  the `if new_title is not None` guard omits `title`. ACTUAL: none — 5 passed / 0 failed / 0 skipped
  in the target file (`-rs` confirms both new tests genuinely RAN); full adapters/db 57 passed
  (was 55). COMPARISON: type, message and status all match; zero NOs.
  New: `test_should_write_a_title_carried_by_a_title_update_verbatim` (VO through the version-CAS,
  `commit()` + `expire_identity_map()` before the read-back) and
  `test_should_omit_the_title_from_the_set_list_for_a_preserve_update` (pins the surviving title AND
  the new content AND `version=3`, so "the save never happened" cannot satisfy it — that trap was
  caught in this file once already). `DocumentStorageStatements.save_content_if_version_matches`
  widened to `TitleUpdate | str | None` and forwards it UNLAUNDERED — unwrapping in the DSL would
  make both cases vacuous.
  NON-VACUITY PROVEN BY TWO MUTANTS (each new test killed by at least one): (1) the coverage agent's
  `new_title = None if isinstance(...)` VO-drop → kills the verbatim test only; (2) unconditional
  `values["title"] = new_title` (omit guard removed, preserve becomes a wipe) → kills the new
  preserve test plus the pre-existing one. Production restored and verified byte-identical after each.
  test-review: 2 findings fixed, both proven by mutation rather than asserted. `assert_stored_state`
  claimed "the full post-CAS state" while pinning 3 of the 4 columns the CAS writes — `updated_at`
  was unverified in every test using it; mutant M3 (delete `"updated_at"` from `_update_values`)
  SURVIVED the pre-review suite at 14 passed and was KILLED at 5 failed after the fix. It also pinned
  3 of 10 persisted fields, so an over-broad SET list clobbering `created_at` or resetting `status`
  was invisible; it now builds an expected `Document` from the pre-save original and delegates to
  `assert_documents_match`, which also retires the duplicated assertion logic between the two methods.
  `updated_at` is pinned to the EXACT captured value, not a monotonicity bound — the DSL generates
  that clock, which makes it determinism category 2 (capturable from setup), strictly stronger.
  ⚠️ CORRECTION TO THE RECORD — the review over `ab40007` was WRONG, and this is worth carrying:
  it claimed `test_document_storage.py:17` and `:85` assert `x == x` because they lack
  `expire_identity_map()`. They do not. test-review MEASURED it instead of reasoning: after
  `given_a_saved_document`, `in_identity_map=False` — SQLAlchemy's identity map holds WEAK
  references and `save_new` keeps none (`session.add(DocumentModel.from_domain(document))`, no local
  survives; the CAS likewise drops `model` after `to_domain()`), so the instance is collected and the
  find already issues a real SELECT. Corrupting the row in raw SQL returned the DB's bytes with AND
  without expire; causation was confirmed by holding a strong reference (then, and only then, the
  un-expired read returned the stale value). ALSO: the mutant that prior review proposed
  (`to_domain` returning a wrong `created_at`) CANNOT discriminate — it mutates the mapping function,
  which runs identically on cached and fresh instances, so it kills the pre-fix tests too. That is
  exactly why the finding looked confirmable and wasn't. The staleness mode is real but those tests
  are protected by a CPython refcounting accident, not a guarantee, so the four
  `expire_identity_map()` calls were kept as defense in depth — and every comment first written
  asserting the false mechanism was rewritten, because a comment stating a wrong mechanism is worse
  than no comment.
  ⚠️ NOT FIXED IN A RED REVIEW, recorded for the step that next touches these files:
  `Document.title: str | None` + `assert_stored_state(title=None)` is a null-on-a-VO-field smell whose
  fix is PRODUCTION domain code — and the `SET title = NULL` clear branch lands straight on that
  signature, so adapters-discovery (b) inherits it. A compound `save_and_reread` DSL method would make
  forgetting the expire impossible (genuine hardening, restructures 5 tests) — `/refactor`'s call.
  ~8 raw inline asserts in `test_document_storage.py` are pre-existing and outside the RED diff.
  refactor (commit follows this one): 2 refactorings. `document_storage_statements.py` was at 170/200
  and could not absorb the new assertion helpers — split along the seam the file already had
  (arrange/act vs assert) into a `DocumentStorageAssertions` base that `DocumentStorageStatements`
  INHERITS, so all ~20 `assert_*` call sites and the conftest fixture are untouched (subclass
  precedent from `f103a31`). And all 8 raw inline asserts relocated out of the
  `test_document_storage.py` test class into 4 DSL helpers, each with 2+ callers — grep confirms zero
  raw `assert` left. One deliberate STRENGTHENING flagged rather than smuggled: the foreign-owner
  hijack guard asserted only `content == ""`; `assert_content_and_version` requires both, so it now
  also pins `version=1` — the sharper half, since a hijack write that landed advances the version
  even if it stored identical content. REJECTED the compound `save_and_reread` (test-review had
  declined it too, for a different reason): the five title tests are not the same shape — two do
  save→commit→SECOND save→commit before the expire, and the intent-carrying value differs in each,
  so the compound method would reconstruct the test bodies as an argument list with the one-save
  tests threading `None`s. 57 passed db (baseline, after R1, after R2); 532/2 backend; mypy clean
  (298 files); ruff unchanged at the pre-existing 5.
  ⚠️ PRE-EXISTING, outside this diff, noted by refactor: `verification_code_storage_statements.py`
  is 209 lines — OVER the 200 hard limit.
> REVIEW FINDINGS over `2cacaf7` — agent-review CONCERNS ×2, premortem 1 CREDIBLE + 3 REMOTE.
> The premortem's CREDIBLE is the one that reorders the queue; it is promoted to a STEP below.
> • **THE SAME PATHOLOGY THIS COMMIT CLOSED IS STANDING ONE LAYER UP (premortem, CREDIBLE).**
>   `save_document.py:79` reads `update = TitleUpdate.of(title) if isinstance(title, str) else title`.
>   `document_router.py:140` forwards `title=request.title` — a bare Pydantic `str | None` — so
>   PRODUCTION ALWAYS ARRIVES ON THE `isinstance(title, str)` TRUE ARM, and that arm is executed by no
>   test in the repo: every usecase call site launders it first (`save_title_statements.py:20`/`:32`
>   both wrap in `TitleUpdate.of(...)` before calling `execute`), and grep confirms zero raw-`str`
>   title arguments anywhere in `backend/usecase/tests`. Coverage reads 100% for the identical reason
>   named in this commit's own message: one conditional expression, no branch arc. THE DETONATOR IS
>   THE NEXT STEP: `green-adapter db (TitleUpdate unwrap)` deletes the transitional `str` arm. If the
>   usecase/db half lands before guard (a2) maps the wire shape, a raw `""` falls to `else`
>   UNWRAPPED, reaches `_update_values` as a `str`, fails `isinstance(title, TitleUpdate)`, and
>   `new_title = ""` — NOT None — so the omit guard passes it through and the CAS runs
>   `SET title = ''` over the stored title. Verbatim the incident Scenario 3.2 exists to prevent,
>   reinstated by the step scheduled next, with every suite green: the usecase tests all pass VOs, the
>   two guards landed here all pass `TitleUpdate`s, and the acceptance test that would catch it is
>   skipped. PROMOTED TO A STEP below, ahead of the green.
> • **`_last_updated_at` is recorded for saves the CAS REFUSES (agent-review).** The clock is captured
>   BEFORE the delegate and unconditionally, so `assert_stored_state` would compare a surviving row's
>   real `updated_at` against a timestamp never written — and it fails looking like an adapter
>   durability bug rather than DSL misuse. `assert self._last_updated_at is not None` does not catch
>   it: it proves SOME save ran, not that the LAST one landed. Not hypothetical — the two refused-save
>   tests at `test_document_storage.py:128`/`:152` are exactly that shape, and this diff touched both.
>   FIX (whoever next touches the DSL): capture the clock only when the delegate returns non-`None`,
>   or have `assert_stored_state` take the returned document instead of reading instance state.
> • **The new docstring overclaims in the same way this unit was correcting (agent-review).** It cites
>   a reset `status` as an example of what the whole-`Document` comparison now catches — but
>   `ALLOWED_STATUSES = (DRAFT_STATUS,)` has exactly one member and `ck_documents_status` is built
>   from it, so no SET list can write a different status without the CHECK constraint rejecting the
>   statement first; `document_type` is likewise pinned to `"эссе"` for every test by
>   `given_a_saved_document`. Of the six "must not touch" columns only `id`, `owner_id`,
>   `idempotency_key` and `created_at` discriminate. The `created_at` half is real and worth having —
>   narrow the wording, per this unit's own standard that a docstring claiming more than the code
>   delivers is worse than none.
> • VERIFIED, NOT ASSUMED (agent-review): the `updated_at` exact-value pin is STABLE —
>   `DocumentModel.updated_at` has no `onupdate`, no `server_default`, and grep over
>   `src/migrations/` finds no trigger on the column; it is a Python-side constant round-tripped
>   through `timestamptz` at matching microsecond resolution. Category-2 determinism as claimed.
>   Both new guards were independently confirmed to bite: without the unwrap a `TitleUpdate` dataclass
>   is bound to a `String` column and asyncpg raises; without the omit guard `preserve()` wipes.
> • WATCH ITEM (agent-review, not a finding): `test_should_omit_the_title_from_the_set_list_for_a_
>   preserve_update` has no mutant it ALONE kills today — every mutation killing it also kills the
>   verbatim test or the pre-existing preserve test. It becomes load-bearing only after the `str` arm
>   is deleted and the unwrap is a bare `title.value`, where `title.value or ""` would kill it and
>   nothing else. CONFIRM that discrimination actually materialises during `green-adapter db` rather
>   than assuming it.
  ORIGINAL STEP TEXT — COVERAGE GAP, proven by mutation, NOT the clear path.
  The green widened the CAS to `TitleUpdate | str | None` and unwraps at
  `document_storage.py:121` (`new_title = title.value if isinstance(title, TitleUpdate) else title`).
  No test anywhere passes a `TitleUpdate` to the real storage: `document_storage_statements.py:54`
  still declares `title: str | None`, and every usecase-layer title test runs against
  `document_fakes`. So the `isinstance` TRUE arm — which is the ONLY arm production reaches, since
  `SaveDocument.execute` now always forwards a VO — is executed by nothing, while the tests cover
  the `str` arm that is explicitly TRANSITIONAL and dead in production. The coverage tools cannot
  see this: line/branch coverage on `document_storage.py` reads 100% because a conditional
  expression is one statement with no arc branch. PROOF: replacing the unwrap with
  `new_title = None if isinstance(title, TitleUpdate) else title` — a mutant that silently DROPS
  every title carried by a VO — leaves all 232 db+usecase tests green.
  THE STEP: widen `save_content_if_version_matches` on `DocumentStorageStatements` to accept
  `TitleUpdate | str | None` and pass it through, then add two cases to
  `test_document_storage_title.py` against real Postgres: `TitleUpdate.of(" Отчёт ")` → the padded
  value is written byte-identically (reuse `expire_identity_map()` before the read-back, per the
  padded round-trip already in that file), and `TitleUpdate.preserve()` → `title` is OMITTED from
  the SET list and an existing title survives with the version advanced. Both must go RED against
  the mutant above.
  SCOPE: distinct from adapters-discovery guard (b), which pins the `SET title = NULL` clear branch.
  This step pins the SET and OMIT arms, which are live TODAY. Discovery (b) should add only the NULL
  case on top of the widened DSL this step lands — do not re-derive the DSL change there.
- [x] red-usecase (the raw-str arm of `_title_intent`) — ALREADY-GREEN regression guard confirmed
  live (not a fabricated RED): predicted PASS on unmutated production, got PASS, first run, no loop.
  PREDICTED (unmutated): none — `_title_intent` already lifts a raw `str` via
  `TitleUpdate.of(title) if isinstance(title, str) else title`, so the blank rule applies identically;
  the arm is UNEXECUTED, not unimplemented. ACTUAL: 6 passed / 0 failed / 0 skipped in the target
  file. PREDICTED (kill-mutant `update = title`): `AttributeError: 'str' object has no attribute
  'is_blank'` at `save_document.py` `_title_intent`, all 3 NEW cases ERROR (not assertion-fail —
  `is_blank()` is called before any branch, so blank and padded fail alike), 3 pre-existing VO-arm
  cases stay green. ACTUAL: 3 failed / 3 passed, `AttributeError: 'str' object has no attribute
  'is_blank'` at `save_document.py:80`, failing ids exactly `empty_title_preserves`,
  `whitespace_title_preserves`, `padded_title_verbatim`. COMPARISON: type, message, location and
  status all match on both predictions; zero NOs. Production restored and `6 passed` re-verified.
  New: `save_title_statements.when_autosaving_with_a_wire_title` (raw `str` straight to
  `SaveDocument.execute`, NO `TitleUpdate.of()` wrapper — an ADDITION; `when_autosaving_with_title`
  is untouched and still pins the VO arm) + `test_should_apply_the_same_intent_to_a_raw_wire_string`
  parametrized over `("", "   ", " Отчёт ")`.
  KILL TEST DEMONSTRATED, and the new test is the SOLE killer: the 3 pre-existing VO-arm cases
  survive the mutant. Step completion condition met.
  NO DISABLE MARKER, deliberately — the test is green against real production code and must stay
  enabled; skipping it would reproduce the exact blind spot the step exists to close.
  test-review: 180 passed / 0 failed (`backend/usecase`), 2 in-diff findings fixed, both proven by
  mutation. (1) The case table was copy-pasted verbatim between the two tests — proven a real defect,
  not a style nit: editing ONLY the first table so `"   "` expected `of("   ")` produced 1 failure /
  5 passed, i.e. the suite held two CONTRADICTORY specifications of the same rule and reported it as
  one localized failure. Hoisted to `TITLE_INTENT_CASES` in the Statements with `pytest.param(id=…)`
  so all 6 ids stay byte-identical; the same drift mutation now yields 2 failures, one per arm.
  (2) The test class imported `TitleUpdate` only to build expectations — removed with the table move.
  The two tests were deliberately NOT collapsed behind a `wrap: bool` flag: that reintroduces the very
  conditional the new test exists to pin.
  ⚠️ FOR `green-adapter db` (next): the mutant kills on TYPE (`AttributeError`), not on a silent wrong
  value — stronger than the db step's silent-drop mutant, but it means this guard bites on type, not
  intent. Once that green deletes the transitional `str` arm from the port, `SaveDocument.execute`
  must still lift the wire string itself, or this test converts from green guard to genuine RED at
  exactly that line — the intended tripwire.
  ⚠️ REPORTED, NOT FIXED (pre-existing, outside this diff): check 16 (storage port reached from a
  Statements) fires twice — `save_document_statements.py:21,49,136` (`FakeDocumentRepository` as a
  base-class field for `given_a_document` setup and `_stored` read-back) and
  `save_title_statements.py:61` (`assert_forwarded_title_update` reads `repository.title_updates`).
  The prescribed fix ripples across the whole save suite via the inherited `SaveStatements` base, and
  the second is in tension with this scenario's stated intent — the assertion belongs at the usecase's
  PORT boundary (what `execute` forwards), not at stored state, since preserve-vs-clear SQL is the db
  CAS's contract tested elsewhere. A deliberate design call, not a review side effect.
  ORIGINAL STEP TEXT — PROMOTED FROM A REVIEW FINDING to a step,
  and sequenced AHEAD of the green it protects (premortem over `2cacaf7`, CREDIBLE). `save_document.py:79`
  is `update = TitleUpdate.of(title) if isinstance(title, str) else title`, and the rest route forwards
  a bare Pydantic `str | None`, so production ALWAYS takes the `isinstance` TRUE arm — which no test
  executes, because every usecase call site wraps in `TitleUpdate.of(...)` first. That is the same
  untested-production-arm / covered-dead-arm shape, and the same 100%-coverage blind spot, that the
  db step immediately above was written to close. It must be pinned BEFORE `green-adapter db` deletes
  the transitional `str` arm, because that deletion is what turns it into `SET title = ''` over a
  stored title.
  THE STEP: add a SECOND DSL method to `save_title_statements.py` (e.g. `when_autosaving_with_a_wire_title`)
  that passes the raw `str` straight to `SaveDocument.execute` WITHOUT the `TitleUpdate.of()` wrapper —
  the existing method must keep pinning the VO arm, so this is an addition, not an edit. Parametrize
  the same `("", "   ", " Отчёт ")` cases over it: blank forwards `preserve()`, padded forwards
  `of(" Отчёт ")` verbatim.
  KILL TEST (the step is not done until this is demonstrated): deleting
  `TitleUpdate.of(title) if isinstance(title, str) else` must go RED.
  refactor (commit follows this one): 1 refactoring. `STORED_TITLE_UPDATE = TitleUpdate.of(STORED_TITLE)`
  extracted as a module constant in `save_title_statements.py` — the same fact was stated twice, at the
  `given_a_titled_document` setup call site and inside `expected_sequence`, with nothing linking them
  (the drift shape test-review had just fixed one level up). REJECTED: deriving `owner_id` from
  `document.owner_id` in both `when_autosaving_*` steps (flagged independently by mechanics and design)
  — the parent `SaveStatements.when_saving`/`when_saving_is_refused` take an explicit owner because the
  refusal steps need a FOREIGN one, so dropping it here alone desyncs the two Statements classes for a
  two-line saving. Also rejected collapsing the two `when_autosaving_*`/two test methods (duplication
  cluster returned zero candidates and reached the same verdict unprompted). Runs: 180 usecase baseline,
  6 target, 180 usecase post-change, 537 passed / 2 skipped full `backend/`. The documented mutation was
  RE-RUN after the refactoring rather than trusting the green — still 3 failed / 3 passed with the new
  test the sole killer. Files 83 and 65 lines.
> REVIEW FINDINGS over `6750132` — agent-review CONCERNS (1 material + 2 minor), premortem 1 CREDIBLE
> + 3 REMOTE (all dismissed with their guards named).
> • **THE PIN HAS NO REMOVAL OWNER, AND ITS OWN ⚠️ CONTRADICTS THE STEP THAT OWNS THE ARM'S DELETION
>   (agent-review, MATERIAL).** `save_document.py:41-45` declares the `str` arm TRANSITIONAL and
>   `adapters-discovery (a2)` (below, untouched by this diff) is its named owner: "this is where it gets
>   rewritten and the arm deleted from `SaveDocument.execute` … so this step naming it is the ONLY guard
>   that exists". This commit adds a SECOND, HARDER reason for the arm to exist — 3 parametrized cases
>   calling `execute(..., title=<bare str>)` — and does not update (a2), which will delete the arm and be
>   blindsided by 3 red usecase tests it was never told about. Worse, the ⚠️ this diff ADDS says
>   "`SaveDocument.execute` MUST STILL LIFT the wire string itself", while (a2) says `execute` must stop
>   accepting a raw `str` — opposite standing requirements ~90 lines apart in this file. Line 992 already
>   records a prior review's worry that the two `str` arms are becoming PERMANENT; this commit materially
>   advances that by converting a documented shim into a tested contract. FIX (owner: whoever next edits
>   (a2)): amend (a2) to name `when_autosaving_with_a_wire_title` + its test as part of the union removal,
>   and reconcile the ⚠️ with it.
> • **HOISTING `TITLE_INTENT_CASES` REMOVED THE CROSS-CHECK IT WAS JUSTIFIED BY (agent-review, minor).**
>   Two tables could drift — but they also cross-checked: an expectation wrong in one was visible against
>   the other. With one shared table a wrong expectation is wrong in both arms simultaneously and both
>   tests agree silently. Given the new test's whole premise is "these two arms might diverge", one table
>   means the suite can no longer EXPRESS divergence. Secondary: `test_save_document_title.py` no longer
>   states its own spec — nothing in that file says `""` preserves or `" Отчёт "` is verbatim.
> • **THE COMMIT MESSAGE CREDITS THE GUARD WITH A LAYER IT CANNOT SEE (agent-review, minor).** It says
>   "that deletion lets a raw `""` reach `_update_values` unwrapped and run `SET title = ''`"; the test
>   asserts against `FakeDocumentRepository.title_updates` at the usecase PORT and never reaches
>   `document_storage._update_values`. The guard it does provide (execute never forwards a raw `str`
>   across the port) is the right one; the db-layer `SET title = NULL`/`''` remains owned by guard (b).
> • **EVERY GUARD THIS SCENARIO HAS BUILT SITS STRICTLY INSIDE THE SEAM THAT WOULD BREAK (premortem,
>   CREDIBLE).** The blank string is BORN at `document_router.py:140` (`title=request.title`) off the
>   Pydantic `title: str | None = None`, one layer ABOVE where this unit's guard starts. Grep for
>   `"title": ""` / `title=""` over `acceptance/` and `backend/` returns ZERO hits — nothing in the repo
>   sends a blank title across the REST boundary. `adapters-discovery (a)` is chartered to make the route
>   map the wire shape itself (`model_fields_set`); the moment it lands a mapping like
>   `TitleUpdate.of(request.title)` at the adapter, `_title_intent`'s blank rule is BYPASSED, `""` reaches
>   `_update_values`, `new_title = ""` is not `None`, and the CAS runs `SET title = ''` — while all six
>   `TITLE_INTENT_CASES` still pass (they call `execute` directly, below the mapping) and both db cases
>   still pass (they construct the VO by hand). MISSING GUARD, named: an acceptance test in
>   `acceptance/tests/backend/documents/` — PUT with title `"Привет Мир"`, PUT again with
>   `{"content": …, "version": N, "title": ""}`, GET, assert the title is byte-identical and the version
>   advanced. Minimum substitute if acceptance is out of scope: a case in
>   `test_save_document_title_router.py` asserting a body of `{"title": ""}` reaches
>   `SaveDocument.execute` with `title=""` — that the route FORWARDS blankness rather than resolving it.
>   Worth landing BEFORE `adapters-discovery (a)`, not after.
> • REMOTE, dismissed with guards named (premortem): (1) `preserve()`/clear collapse into one
>   representation — guarded by `test_should_omit_the_title_from_the_set_list_for_a_preserve_update`;
>   note the guard is a DB test, not a domain one, so `adapters-discovery (b)` must not "fix" that test
>   to make clear fit. (2) Padding silently trimmed — the usecase expectation is TAUTOLOGICAL
>   (`TITLE_INTENT_CASES` expects `TitleUpdate.of(" Отчёт ")` while production computes
>   `TitleUpdate.of(title)`, same constructor both sides, so a `.strip()` inside `of()` leaves all six
>   green); guarded one layer down by the db test asserting the literal stored column. (3) Padded title
>   yields an unusable filename — `ExportDocument._derive_filename` already does
>   `(document.title or "").strip() or "document"`.
- [x] green-adapter db (TitleUpdate unwrap) — OWNS THE DB HALF OF THE UNION REMOVAL (assigned by the
  agent-review pass over `83e4e48`, which found the removal had no owner anywhere: (a) never mentions
  it, (b) is scoped to `SET title = NULL`, and the red step above deliberately WIDENS the DSL). Once
  the db DSL speaks `TitleUpdate`, this green MUST delete the `str` arm from
  `document_storage.save_content_if_version_matches` — the refactor confined the unwrap to
  `_update_values`, so it is one line. Leaving it makes
  `save_content_if_version_matches(title="")` a legal call that still executes `SET title = ''`.
  GREEN: db 57 passed / 0 failed / 0 skipped (real Postgres, `infra-postgres-1`); target file 5 passed;
  usecase 180 passed; full `backend/` 537 passed / 2 skipped / 0 failed; mypy clean (281 files, run from
  `backend/` per `pyproject.toml` + `ci.yml:52` — `mypy backend/` from the repo root fails on a duplicate
  -`conftest` module resolution error, which is a pre-existing invocation quirk, not a type error); ruff
  byte-identical to the pre-existing 5. Files 148 and 104 lines.
  `save_content_if_version_matches` and `_update_values` narrowed `TitleUpdate | str | None` →
  `TitleUpdate | None`, so `save_content_if_version_matches(title="")` is no longer a LEGAL CALL and the
  `SET title = ''` path is gone by construction, not by guard. The unwrap collapsed from
  `title.value if isinstance(title, TitleUpdate) else title` to `title.value if title is not None else
  None`. The surviving `| None` is the ABSENT case, still owned by `green-usecase (port narrowing)` below
  — deliberately not touched. Docstring rewritten to state what the code now delivers rather than the
  stale "adapters-discovery (b) will drop the arm" promise.
  ⚠️ ONE TEST-DSL CHANGE, FLAGGED RATHER THAN SMUGGLED: four read-only tests call the DSL with a raw
  `str` title, so with the production `str` arm gone the DSL had to stop forwarding one. The `str` arm is
  kept in `document_storage_statements.py` as a DSL CONVENIENCE ONLY and now lifts
  (`if isinstance(title, str): title = TitleUpdate.of(title)`). No test body, assertion or expected value
  changed and the value crossing the port is byte-identical, so it cannot mask an adapter bug. Removing
  the lift means editing four test call sites — outside a green.
  ✅ WATCH ITEM FROM THE REVIEW OVER `2cacaf7` CONFIRMED BY RUNNING THE MUTANT, NOT BY ARGUMENT:
  `test_should_omit_the_title_from_the_set_list_for_a_preserve_update` had NO mutant it alone killed
  before this step. With the `str` arm gone and the unwrap a bare `.value`, mutant
  `new_title = (title.value or "") if title is not None else None` gives 1 failed / 56 passed — the
  single failure is that test (Postgres returned `'title': ''` against expected `'Привет'`), with the
  verbatim/padded/round-trip tests all surviving. It was a passenger; it is load-bearing now.
  SEQUENCING CONSTRAINT HOLDS: `save_document.py:48/72` still carries `TitleUpdate | str | None` and
  `_title_intent`'s lift, untouched — that usecase-level `str` arm is owned by `adapters-discovery (a2)`
  and pinned by `when_autosaving_with_a_wire_title`. usecase 180 passed proves `execute` still lifts the
  wire string. The only `TitleUpdate | str` unions left in the repo are that usecase pair and the DSL
  convenience arm.
  test-coverage (`backend/adapters/db --focus`): CLEAN, no gap, no steps inserted. 43 stmts / 0 missed /
  2 branches / 0 partial — and that 100% is NOT the evidence: the 2 arcs coverage.py counted belong to
  `if new_title is not None:` (line 146); the conditional expression on line 145 contributed ZERO branch
  arcs, exactly the blind spot that bit this scenario twice. Each arm proven by mutation instead, all
  three reverted and the tree confirmed byte-identical. Arm 1 (`title is not None` → `title.value`):
  mutant `None if title is not None else None` killed by 5 tests, the load-bearing one being
  `test_should_write_a_title_carried_by_a_title_update_verbatim`, which passes `TitleUpdate.of(" Отчёт ")`
  DIRECTLY — so the new DSL lift is a no-op for it and cannot launder the case. Arm 2 (`title is None`):
  mutant `else "MUTANT-ELSE-ARM"` killed by EXACTLY 1 test,
  `test_should_preserve_an_existing_title_on_a_content_only_save`, whose second save omits `title`
  entirely — so the `None` arm has its own dedicated killer rather than riding on the preserve test
  (`preserve()` reaches `new_title is None` through arm 1 via `.value`, a distinguishable path). Bonus:
  mutant `title.value.strip() if title is not None and title.value else None` killed by the padded and
  verbatim tests, so the unwrap is pinned BYTE-IDENTICALLY, not merely non-None — the thing the previous
  two misses in this scenario were about.
  ⚠️ OBSERVATION (not a gap, for whoever next touches these tests): the DSL lift now routes every
  raw-`str` test through `TitleUpdate.of(...)`, so all five title tests hit arm 1. The `TitleUpdate.of`
  and `TitleUpdate.preserve` tests still pass the VO UNLIFTED, so arm 1 keeps an unlaundered witness —
  if those two ever go away, arm 1's only coverage becomes DSL-constructed and the port narrowing loses
  its independent check.
  refactor (commit follows this one): 3 refactorings, all proven by mutation rather than asserted.
  (1) PRESERVE-DETECTION MOVED ONTO THE VO: the adapter was re-deriving what `preserve()` means by
  null-testing the VO's raw field — the exact `str | None` ambiguity `TitleUpdate` exists to remove,
  reconstructed one layer out. New `TitleUpdate.carries_a_value()` next to its `is_blank()` sibling;
  `_update_values` collapsed to `if title is not None and title.carries_a_value()`. Both arms mutated:
  `return True` → 1 failed / 368 passed (the same dedicated killer the green established), `return False`
  → 5 failed / 364 passed. The two `None` tests are NOT redundant — the outer one is the ABSENT case
  owned by the pending `green-usecase (port narrowing)`, left in place.
  (2) DSL TYPE-LIFT REMOVED (the green had flagged it as deliberate; refactor judged the reversal
  better and proved it). Two arguments beyond tidiness: the DSL was the only place in the repo
  advertising a call shape NO production caller can make, so four tests documented a signature that does
  not exist; and `isinstance(title, str)` would silently map a future `title=""` to `TitleUpdate.of("")`,
  re-opening in tests the precise shape the green called "gone by construction". Proof the tests stay
  byte-identical in what they assert: `git diff -U0` on the test file is EXACTLY four hunks, each only
  the `title=` argument (`"Привет"` → `TitleUpdate.of("Привет")` ×3, `" Отчёт "` → `of(" Отчёт ")` ×1) —
  no assertion, expected value, body or setup line changed, and `of(x).value is x`. This also retires the
  green's own ⚠️ OBSERVATION: arm 1's unlaundered witness no longer depends on the two VO tests
  surviving, because all five title tests now pass the VO directly.
  (3) `= None` DEFAULT DROPPED from `TitleUpdate.value` — `TitleUpdate()` was a legal second, unnamed
  door to the preserve state competing with `preserve()`. Nothing constructed it bare (verified).
  Runs: 369 passed baseline and after each of the three (db + domain + usecase, real Postgres);
  537 passed / 2 skipped full `backend/`; mypy clean (298 files); ruff byte-identical to the
  pre-existing 5.
  DECLINED, reported rather than silently deferred: `save_content_if_version_matches` takes
  `content: str` while `DocumentContent` exists in the domain — primitive obsession on a port whose
  SIBLING parameter is now VO-typed. NOT behavior-preserving: `DocumentContent` NFC-normalizes and
  length-caps, so routing content through it changes what gets stored. Needs its own red/green.
  DOCSTRING OVERCLAIM FIXED IN THIS COMMIT (both review passes landed it independently — see below):
  `_update_values` claimed `save_content_if_version_matches(title="")` "cannot reach `SET title = ''`".
  Reworded to state what the code actually delivers — the narrowing removes the SPELLING, not the path.
> REVIEW FINDINGS over `2bb51a5` — agent-review CONCERNS ×2, premortem 3 CREDIBLE (all three NEW; the
> premortem explicitly re-checked and confirmed the standing `6750132` REST-seam CREDIBLE is untouched
> by this commit — `document_router.py:140` still forwards `request.title` raw and the usecase `str` arm
> is intact). NOTE ON SEQUENCING: both passes read `2bb51a5` and therefore did NOT see the refactor,
> which independently removed the DSL lift — that retires agent-review finding 2 and the DSL half of
> premortem 1. The docstring half was fixed in the refactor commit. What remains open is recorded below.
> • **"GONE BY CONSTRUCTION" IS FALSE — `SET title = ''` IS STILL REACHABLE (both passes, CREDIBLE).**
>   MEASURED, not inferred, by running the narrowed `_update_values` directly:
>   `of('')` → title in SET: True `''`; `of('   ')` → True `'   '`; `preserve()` → False; `None` → False.
>   `TitleUpdate.of("")` is a legal, mypy-clean call that writes `''` TODAY, and `of("   ")` writes the
>   value the ADR names as producing `%20%20%20.pdf`. The narrowing removed one SPELLING of the wipe
>   (`str`), not the PATH. The only blank defense in the repo is `SaveDocument._title_intent` one layer
>   up — a GUARD, which is exactly what the docstring claimed to have replaced. Incident: a
>   create-with-title endpoint, an import, or an admin path builds the VO from wire input and calls the
>   CAS directly (the ADR itself names those bypasses), and blank titles overwrite stored ones.
>   MISSING GUARD, still open: no db test constructs a blank `TitleUpdate` — the five title tests are
>   `"Привет"`, content-only omit, `" Отчёт "` padded, `of(" Отчёт ")`, `preserve()`. Name it
>   `test_should_not_wipe_a_stored_title_for_a_blank_title_update`: save `"Привет"`, then save with
>   `TitleUpdate.of("")`, assert `title == "Привет"` and `version == 3`. IT GOES RED TODAY. If the
>   intended contract is instead "the adapter writes `''` and the usecase is the only guard", the fix is
>   the docstring alone — the docstring was reworded that way in the refactor commit, so this now needs
>   a DELIBERATE call: adopt the usecase-only-guard contract, or add the db guard.
> • **`preserve()` AND THE ADR's `clear()` ARE THE SAME OBJECT — MOST SEVERE (premortem, CREDIBLE).**
>   MEASURED: `TitleUpdate.preserve() == TitleUpdate(value=None)` → True. One-field frozen dataclass, so
>   a `clear()` implemented the obvious way has NO free representation left. This commit is what makes it
>   load-bearing: it deleted the `str` arm and blessed the surviving `| None`, and the very next pending
>   work is the clear path (`SET title = NULL`). The failure is EQUALITY-SILENT:
>   `assert_forwarded_title_update` compares by dataclass equality, so a usecase forwarding `preserve()`
>   where `clear()` was meant — or the reverse — passes every existing usecase test. Either every
>   content-only autosave issues `SET title = NULL` (mass wipe on next save), or the clear affordance
>   no-ops and a cleared title returns on reopen forever. MISSING GUARDS, neither of which can pass with
>   the current VO shape: domain `test_should_tell_a_clear_apart_from_a_preserve`
>   (`assert TitleUpdate.clear() != TitleUpdate.preserve()`), and db
>   `test_should_null_the_title_for_a_clear_update` beside the existing preserve/omit test, over the same
>   stored title. THE CLEAR-PATH STEP MUST NOT START until `TitleUpdate` can carry a distinguishable
>   third state (sentinel value, or an explicit intent field). This corroborates the ⚠️ already recorded
>   on the `red-usecase (clear path)` step below, now with a measurement behind it.
> • **THE PENDING `green-usecase (port narrowing)` IS UNFALSIFIABLE AT THE DB LAYER (premortem,
>   CREDIBLE).** MEASURED: `preserve()` and `None` produce BYTE-IDENTICAL SET clauses — `preserve()`
>   reaches `new_title is None` through arm 1 via `.value`, `None` through arm 2. This commit's own
>   coverage note called that "a distinguishable path", but it is distinguishable only to a MUTATION of
>   the arm, never to observable behavior. So "absent forwards `preserve()` instead of a bare `None`" has
>   NO db test that can go RED on it — it would land green having proven nothing. MISSING GUARD: the
>   proof must live where the states are distinguishable — a usecase test pinning the exact forwarded
>   object for the ABSENT case (`title` omitted from `execute`), added as an `absent_preserves` param to
>   `TITLE_INTENT_CASES` / `assert_forwarded_title_update`. `TITLE_INTENT_CASES` has no absent case at
>   all today; the only thing pinning absent is the db
>   `test_should_preserve_an_existing_title_on_a_content_only_save`, which per the measurement above
>   cannot distinguish the two values the step is about. FOLD THIS INTO THE NEXT STEP.
> • RETIRED BY THE REFACTOR, recorded for the audit trail (agent-review finding 2): the DSL `str` arm
>   outlived its justification and type-laundered the narrowed port — a db test's `title="Привет"`
>   type-checked and passed although the equivalent production call would not. Refactor (2) removed it.
- [x] red-usecase (port narrowing: absent forwards `preserve()`, not a bare `None`) — BOTH review
  passes over `83e4e48` landed this independently, and it must precede the clear-path work because
  the clear path is what turns it into a mass wipe. `_title_intent` returns a bare `None` for the
  absent case while the port docstring declares `None` unusable, so `preserve()` and `None` ship as
  synonyms and the most common call in the app carries the ambiguous one. Pin it: `SaveDocument.execute`
  called with NO `title` argument forwards `TitleUpdate.preserve()` across the port — no test covers
  this today (`save_title_statements.when_autosaving_with_title` always passes an explicit
  `TitleUpdate.of(...)`, so the `None` arm is asserted nowhere at either layer).
  RED confirmed live: predicted == actual on every field, first run, no loop.
  PREDICTED: `AssertionError` at `assert_forwarded_title_update` in `save_title_statements.py`
  (`assert self.repository.title_updates == expected_sequence`), message `expected
  [TitleUpdate(value='Привет Мир'), TitleUpdate(value=None)] forwarded to the repository, got
  [TitleUpdate(value='Привет Мир'), None]`, status 1 failed / 6 passed. ACTUAL: `AssertionError` at
  `save_title_statements.py:98` raised from `test_save_document_title.py:94`, message identical
  verbatim, `1 failed, 6 passed in 0.51s`. COMPARISON: type, message, location, status — all YES.
  (Cyrillic rendered as mojibake in the Windows console; that is the terminal codepage, not a value
  difference — the same literal appears on BOTH sides of the comparison and the setup-title element
  matched.) Skip marker on the new method only; usecase 180 passed / 1 skipped.
  New: `when_autosaving_without_a_title` (omits the `title` argument to `execute` ENTIRELY) +
  `test_should_forward_preserve_when_no_title_is_submitted_at_all`. Asserts at the PORT boundary, per
  the premortem over `2bb51a5` — the db layer CANNOT falsify this step (measured: `preserve()` and a
  bare `None` produce byte-identical SET clauses). Equality checked BEFORE predicting:
  `preserve()` is `TitleUpdate(value=None)`, a bare `None` is `NoneType` — not equal, so the assertion
  is genuinely falsifiable (unlike `preserve()` vs `clear()`, which per the standing CREDIBLE ARE equal).
  DEVIATION FROM THE PREMORTEM'S LITERAL SUGGESTION, and test-review independently PROVED the deviation
  correct rather than merely accepting it: the finding asked for an `absent_preserves` param inside
  `TITLE_INTENT_CASES`. That table has TWO consumers, and the second is
  `when_autosaving_with_a_wire_title(..., title: str)`, which forwards the raw string to `execute` —
  absence is the OMISSION of the argument, and no `str` value encodes it. A sentinel row would be
  unexecutable in one consumer and force BOTH parametrized methods to branch on it. A dedicated `when_`
  method + the existing `assert_forwarded_title_update` unchanged satisfies the finding's substance.
  test-review: 180 passed / 0 failed / 1 skipped, 1 finding fixed — and it is a serious one that
  invalidates a guard this scenario had already banked.
  ⚠️ EVERY EXPECTED `TitleUpdate` IN THIS SUITE WAS BUILT FROM THE SAME FACTORIES PRODUCTION CALLS, so
  the assertions compared a factory call to itself — pinning the NAME of the intent and nothing about
  what the intent IS. Proven by two mutations, each of which left the ENTIRE usecase suite green at
  181/181 BEFORE the fix: (1) `preserve()` → `TitleUpdate(value="")`, i.e. the db CAS writes
  `SET title = ''` over a stored title on EVERY autosave — 181 passed before, 4 failed after;
  (2) `of(v)` → `TitleUpdate(v.strip())`, i.e. the exact `title.strip() or None` normalisation the ADR
  REJECTS — 181 passed before, 2 failed after. The second is the sharper one: `padded_title_verbatim`
  exists SPECIFICALLY to catch silent trimming (the module docstring calls it "the guard the ADR's
  rejection of `title.strip() or None` demands") and could not detect the bug it was written for,
  because expected and actual both flowed through the mutated `of()`. That guard was DECORATIVE for the
  two commits it has existed. FIX: expected intents now spelled STRUCTURALLY and owned by the Statements
  module — `PRESERVE_TITLE_UPDATE = TitleUpdate(value=None)`, `TitleUpdate(value=PADDED_TITLE)`. The
  action methods still call `TitleUpdate.of(...)`; that is a real production call site being exercised
  and correctly stays. Placement fixed as a side effect: the test class no longer imports the domain VO
  at all (it was the file's first inline VO construction, against the file's own convention).
  ⚠️ NOTE FOR THE GREEN: the collapse is one line — `if title is None: return None` →
  `return TitleUpdate.preserve()`. The return type can then narrow `TitleUpdate | None` → `TitleUpdate`,
  and the port/fake signatures `title: TitleUpdate | None = None` become over-wide — but tightening
  those is a signature change across the port, the fake AND the db adapter, so it belongs in the green's
  own refactor, not smuggled into the collapse.
  ⚠️ INFRA NOTE: three of the four test-review detector subagents died on API errors (403 / connection
  closed); the reviewer ran the checklist directly rather than report on partial detector output.
- [~] green-usecase (port narrowing) — collapse `None → TitleUpdate.preserve()` in `_title_intent`
  and DROP `| None` from `DocumentRepository.save_content_if_version_matches`, then delete the
  now-dead second collapse step in `document_storage._update_values` and the double guard at
  `document_fakes.py:115` (`title is not None and title.value is not None`).
- [ ] green-acceptance (blank-title round trip) — PULLED FORWARD from the end of the scenario by the
  premortem over `83e4e48`: unskip `test_export_document_acceptance.py:141` (both `empty_title` and
  `whitespace_title` params) HERE, not after the clear path. It is the only test in the repo that
  exercises route → usecase → CAS → Postgres → export header for this scenario, ~50 lines of
  assertion code are reachable only from it, and until it runs the scenario has zero executable proof
  of the round trip — this step's "4 → 0 skips" was verified over `backend/usecase`, a scope that
  cannot see the `acceptance/` tree. Rebuild the baked backend image first (see carryover).
- [ ] red-usecase (clear path) — `null` clears: the ADR's new behavior, which no existing test
  covers. Inserted at design so the clear branch is driven by a test rather than smuggled into a
  green whose tests do not exercise it.
  ⚠️ MUST RESHAPE `TitleUpdate` FIRST — BOTH review passes over `60ab441` landed CREDIBLE on this,
  and it invalidates guards already written. The domain-field gate dropped the `clears`
  discriminator, so the VO ships one field with `preserve() == cls(value=None)`. `clear()` therefore
  has NO representation left: its only possible value is `TitleUpdate(value=None)`, which under
  frozen-dataclass equality IS `preserve()`. Consequences, all live:
  • `save_document_statements.assert_forwarded_title_update` compares by dataclass equality against
    `preserve()`, so a green that routes BLANK titles to `clear()` passes it — the exact
    `SET title = NULL` data loss the ADR forbids.
  • `document_fakes.save_content_if_version_matches` branches on `title.value is not None`, mapping
    clear and preserve to the same "leave the title alone" — the clear path reads green at the
    usecase layer while doing nothing. That predicate is cheap to fix here and expensive to notice
    later.
  • Scheduled guard (a) below demands TWO route assertions because "one alone passes under a
    constant mapping" — but with a single-field VO, BOTH pass under a constant mapping that always
    returns `TitleUpdate(value=None)`. The guard written against constant mappings cannot
    discriminate. Reinstating the discriminator is part of THIS step, and must land before guard (a)
    is authored.
  • No `TitleUpdate` domain test exists anywhere. Add one: `preserve() != clear()`, plus a fake case
    where clear actually nulls the stored title.
  ⚠️ ALSO (premortem CREDIBLE 2): `of()` accepts `""` and `"   "` without objection, so the
  blankness rule lives only in `SaveDocument.execute`. Any other caller — the scheduled rest
  adapter, a create-with-title endpoint, an import — can hand `of("")` straight to the CAS and
  reopen the `SET title = ''` path. This is the ADR's own defense-in-depth argument applied to the
  WRITE side, where it was never made: pin that `of()` with a blank string is rejected or normalises
  to `preserve()`, so the invariant lives on the type rather than on one caller.
- [ ] green-usecase (clear path)
- [ ] adapters-discovery — REQUIRED guards, named by the review passes over the design commit
  (`97e8f53`); discovery must insert all four, none is optional:
  (a) rest route — TWO assertions in `test_save_document_title_router.py`, not one: a body of
  `{"content","version"}` with NO `title` key → `SaveDocument.execute(title=TitleUpdate.preserve())`
  AND `{"title": null}` → `TitleUpdate.clear()`. One alone passes under a constant mapping, and
  `model_fields_set` is the ONLY place absent and null are distinguishable — a route that maps
  `null → preserve` cannot go red anywhere else.
  (a2) OWNS THE REST HALF OF THE UNION REMOVAL (assigned by the agent-review pass over `83e4e48`).
  The route must BUILD a `TitleUpdate` rather than forward a raw `str`; the read-only assertion at
  `test_save_document_title_router.py:57` (`execute(..., title="Привет Мир")`) is the stated reason
  the `str` arm exists, so this is where it gets rewritten and the arm deleted from
  `SaveDocument.execute`. A permissive union never fails type-checking — mypy stays clean whether or
  not the arm is ever removed, so this step naming it is the ONLY guard that exists.
  (b) db CAS — pin the `SET title = NULL` branch in `test_document_storage_title.py`, which today
  covers round-trip and preserve-on-omit only. This is the layer where "clear" is an actual SQL
  statement; a usecase test passing against `document_fakes.py` proves nothing about it, and the
  fake is rewritten by the same green it would be guarding.
  (c) acceptance client — `application_client.py` currently spells absent as `title=None`
  (`if title is not None: payload["title"] = title`), so it CANNOT send explicit null: it collapses
  exactly the two shapes this contract separates. A sentinel is a precondition for any end-to-end
  clear test.
  (d) wire contract — propagate the three-state table to `endpoints.md` and to the PUT
  request-schema `description` in `document_dtos.py` (the OpenAPI surface). Story-5-extension owns
  the title editing UI and will never open this story's `decisions/` folder; those two artifacts are
  what a parallel frontend session actually reads.
- [ ] green-acceptance
> READ-MODEL NOTE (agent-review, verified): `DocumentResponseDto` and `DocumentSummaryDto` carry NO
> `title` field, so the whole three-state contract is unobservable to any client except by exporting
> a document and decoding `Content-Disposition`. Exposing `title` on the read model is
> story-5-extension's to make (it owns the title UI) — but note the coupling: doing so is what turns
> the ADR's conceded residual live, because a client typing its state from a `string | null` read
> DTO holds `null` before hydration.

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
> CARRY-FORWARD (from Sc 3.1 green-acceptance, commit d89f8b8 — agent-review + premortem BOTH
> CREDIBLE, same finding): `title` is unbounded at EVERY layer — `SaveDocumentRequestDto.title` has
> no `max_length`, `DocumentModel.title` is an unbounded `String`, and `SaveDocument.execute`
> validates content length but never title. The Sc 3.1 chain now proves that title reaches a
> RESPONSE HEADER verbatim, and `quote(safe="")` expands each Cyrillic char 1→6 bytes, so a ~20k-char
> title yields a ~120 KB single `Content-Disposition` line — past nginx's default `proxy_buffer_size`
> (4–8 KB) and uvicorn/h11 header caps: the export 502s permanently for that document, self-service
> reachable by any authenticated user. This is a HEADER-SIZE failure, distinct from the aesthetic
> grapheme-truncation this scenario was written for — 3.6 must ALSO pin a named `MAX_TITLE_LENGTH`
> (422 or truncate at the save boundary) plus a rest-layer assertion that the emitted header stays
> under a bounded byte length for a pathological title.
> CARRY-FORWARD (same commit, agent-review CONCERN #2): the export route emits ONLY
> `filename*=UTF-8''…` with no RFC 6266 §4.3 ASCII `filename="…"` fallback, so a non-RFC-5987 client
> saves the file as the URL path segment (`export`). Three statements files now pin whole-header
> equality (`document_export_filename_statements.py`, `document_export_statements.py:168`,
> `document_export_docx_statements.py:61`), so adding the fallback later breaks all three — decide
> explicitly whether the fallback is wanted before those assertions harden further.
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
> CARRY-FORWARD (from Backend Sc 3.1 green-acceptance, commit d89f8b8 — premortem CREDIBLE): the
> migration chain is validated by NOTHING but the deploy itself. `infra/docker/backend.Dockerfile`
> CMD is the only place `alembic upgrade head` ever runs; the db-suite conftest connects to a
> pre-existing stamped database and only truncates it — it never migrates. `a3b4c5d6e7f8`
> (documents.title) is the first migration-added column that is load-bearing for a shipped feature,
> so a mis-chained `down_revision`, a second head after a branch merge, or a model/schema drift
> surfaces first as a crashlooping container or `UndefinedColumn` on every document read. Guard to
> add here: a db-suite test that runs `alembic upgrade head` against an EMPTY database and asserts
> (a) `ScriptDirectory.get_heads()` has exactly one head, and (b) autogenerate against the migrated
> schema produces an empty diff (`alembic check`).
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance
