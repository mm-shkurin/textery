# Story 17: Export document to PDF / DOCX — Frontend Progress

Owns: Frontend Scenarios. Narrative/decisions/Spec checklist live in `progress.md`;
`ProductSpecification/stories.md` is the cross-file rollup.

This file tracks **which work units ran**.

## Frontend Scenarios (02_UI_Tests.md)

### Scenario 1.1: The editor offers a PDF and a DOCX export choice
- [x] red-selenium
- [x] red-frontend
- [x] green-frontend
- [S] red-frontend-api — control display is pure local toggle state; no backend call. The export endpoint (GET /documents/{id}/export) is exercised by scenario 5.1 (download).
- [S] green-frontend-api — same reason, no API for control display.
- [x] align-design — no mockup for story 17; styled to editor design tokens + defined the me-toolbar-row flex layout (breadcrumb left / export right). design-review PASS, coverage 100%.
- [x] green-selenium — real Chrome, 2 clean runs; against Vite dev :5273 + backend :8100 (no infra/.env on branch — run needs FRONTEND_PORT=5273 BACKEND_PORT=8100)
- [S] demo — autonomous loop, no interactive viewer; behavior already proven in real Chrome by green-selenium. Run `/demo TestExportControlDisplayAcceptance` manually to watch.

### Scenario 2.1: The export control is disabled while a request is in flight
- [x] red-selenium
- [x] red-frontend
- [x] green-frontend — real in-flight disabled state (not menu-close), released in `.finally()`; `exportDocument` throw-stub pending green-frontend-api. Addressed finding (1) by implementing a genuine disabled lock. Finding (2) release-path sibling test still owed — carry to a strengthening step (see below). **original findings on RED test (23ab6ce):** (1) *vacuous-pass risk (agent-review):* the RED test clicks the same captured `pdfOption` node twice; if green closes the menu on select, the 2nd click hits a detached node and passes with NO lock. Green must implement a real disabled/in-flight state on the control (per scenario title "control is disabled while a request is in flight") and the test must re-query + assert the control is disabled between clicks so the 2nd click reaches a live handler. (2) *lock-never-releases (premortem):* the never-settling mock can't prove release — add a sibling test with a manually-resolvable deferred asserting the control re-enables and a fresh click fires a 2nd `exportDocument` after settle (success AND reject paths; reject overlaps 3.2).
- [x] red-frontend (coverage: guard early-returns when locked or no documentId) — coverage-pinning: guard `if (isExporting || !documentId) return` already exists in prod (green-frontend). 2 tests (locked→call count stays 1 + payload `('doc-1','pdf')`; no-documentId→0 calls). No skip marker (tests pass green, lock the branch). Branches 83.33%→100%. Added `beforeEach(vi.clearAllMocks)` (no global clearMocks on project). test-review strengthened the surviving-call assertion to `toHaveBeenNthCalledWith`.
- [x] green-frontend (coverage: guard early-returns when locked or no documentId) — NO-OP: guard `if (isExporting || !documentId) return` (ExportControl.tsx:28) already shipped in original green-frontend; zero production change. 2/2 guard tests green, suite 132 pass. **Owed follow-ups (non-gating, from agent-review+premortem on dc7df3a):** (a) test 1 vacuously pins the `isExporting` branch — the option button's `disabled={isExporting}` masks the handler guard (jsdom skips onClick on disabled), so deleting `isExporting ||` from the handler leaves test 1 green. Needs a test reaching `handleExport` with isExporting=true bypassing the disabled attr. (b) release-path still uncovered (finding 2) — never-settling mocks never exercise `.finally(setIsExporting(false))`; owed resolvable-deferred sibling (resolve+reject, reject overlaps 3.2).
- [x] red-frontend-api
- [x] green-frontend-api — implemented via shared transport `responseType: 'blob'` (httpClient `performRequest` returns `res.blob()` AFTER the `res.ok` guard); `exportDocument` now `Promise<Blob>` through `send`/`authorizedRequest`, inheriting res.ok→HttpError, 401 renew+replay, and withTimeout. 508/508 pass. Owed non-ok case now COVERED: added an export-level guard test (premortem a227968) asserting exportDocument rejects on a non-ok response and never reads the blob — pins the res.ok-before-blob ordering so a future reorder goes red. 401-renew still relies on the shared transport's own tests (acceptable). Design directive (fulfilled): blob variant added to shared authorized transport, not a bare fetch; signature `Promise<Blob>`.
- [x] align-design — styled the in-flight disabled state (opacity 0.35 + not-allowed + neutralized disabled:hover) matching me-toolbar-btn:disabled. No mockup. design-review PASS.
- [x] red-selenium (determinism strengthening: throttle network + wait for in-flight before 2nd click) — hardened `manual_editor_export_control_statements.py` (128 lines): added `throttle_network`/`clear_network_throttle` (CDP `Network.emulateNetworkConditions`, `_SLOW_LATENCY_MS=2500`) + `wait_for_export_in_flight` (WebDriverWait on `_pdf_option_is_disabled` — proves `disabled`/`aria-disabled=true`, the real `disabled={isExporting}` lock, NOT 3.1's not-yet-existing indicator). `trigger_export_as_pdf_twice` now: throttle→open→click PDF→wait-in-flight→2nd click (dropped)→clear throttle. `==1` unchanged; requestWillBeSent counts the held-open first GET as 1. Test class stays `@pytest.mark.skip` (unskip+live run = green-selenium). Analytical RED: if lock absent, 2nd click hits enabled option→2nd GET→count 2→fails. test-review PASS 0 fixes.
- [~] green-selenium — remove `@pytest.mark.skip` marker only (no Statements/production changes — determinism now baked into the hardened Statements above), run `TestExportControlInFlightAcceptance` in real Chrome against backend :8100 + frontend :5273. If it fails, STOP and report.
- [ ] demo

### Scenario 3.1: An in-flight export shows a progress state
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 3.2: An export error is shown with retry, document unchanged
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 4.1: Exporting with unsaved edits saves or warns first
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 5.1: A successful export delivers a downloaded file
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo
