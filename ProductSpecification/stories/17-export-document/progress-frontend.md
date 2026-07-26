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
- [x] red-selenium (fix: throttle AFTER opening the export control, not before) — reordered `trigger_export_as_pdf_twice` to open→resolve-option→throttle→click→wait-in-flight→2nd-click→clear. **Verified LIVE** (temp-unskip, real Chrome :8100/:5273): `1 passed in 11.39s`, `==1` held, and the premortem disabled-2nd-click landmine did NOT fire — real ChromeDriver dropped the click on the disabled button cleanly (no ElementNotInteractable/Intercepted/Stale). Skip marker re-added (formal unskip = green-selenium). test-review PASS 0 fixes. **green-selenium live run FAILED (a20e2db):** `trigger_export_as_pdf_twice` calls `throttle_network` at line 78 BEFORE `open_export_control` at line 79; under the 2500ms CDP throttle the `export-control-trigger` never becomes visible within the 5s wait → `TimeoutException` on the FIRST menu-open, before any click (NOT the premortem disabled-2nd-click landmine). Sibling 1.1 passes with the same trigger — only difference is 2.1 throttles first. Diagnosis: the export GET fires only on the PDF-option click, so the throttle must be active only for that click — move `throttle_network` to AFTER `open_export_control` (menu-open is a local toggle, no network). Fix: reorder to open→throttle→click→wait→2nd click→clear. Then green-selenium can retry.
- [x] green-selenium — removed `@pytest.mark.skip` from `TestExportControlInFlightAcceptance`; real Chrome (:8100/:5273), **2 clean runs** (9.57s, 9.89s), count==1 both. Version-dependent disabled-2nd-click landmine did NOT fire either run. Also dropped the now-dead `import pytest` (decorator was its only use). Scenario 2.1 acceptance now GREEN + enabled. Prior watch notes retained below for history. **premortem watch (247299e):** the 2nd `pdf_option.click()` lands on a now-disabled `<button>`; jsdom silently drops it but real ChromeDriver may raise `ElementNotInteractable`/`ElementClickIntercepted` (or stale), erroring for the wrong reason instead of proving the lock. If that happens at unskip, the green-selenium fix is to tolerate/assert the disabled 2nd click explicitly (Statements change → belongs to a red-selenium follow-up, not remove-marker-only) — STOP and report rather than forcing it. throttle-leak/timeout/preflight all dismissed (function-scoped driver quits; disabled set synchronously; GET-only count excludes OPTIONS). **premortem 429b5e3 (2nd verified-live pass, still non-gating):** the disabled-2nd-click drop is ChromeDriver-version-dependent and was proven exactly once — RUN green-selenium TWICE (matching 1.1's 2-run convention) to shake out the flake; if either run errors on the 2nd click (`ElementNotInteractable`/`StaleElementReference`), the red-selenium follow-up is to wrap+re-fetch the 2nd click so the drop is asserted by the test, not left to undefined driver behavior. Optional belt-and-suspenders: fold `clear_network_throttle` into a `finally` (currently skipped if the 2nd click raises; blast radius is 1 test since the driver is function-scoped).
- [S] demo — autonomous loop, no interactive viewer; behavior already proven in real Chrome by green-selenium (2 clean runs). Run `/demo TestExportControlInFlightAcceptance` manually to watch.

### Scenario 3.1: An in-flight export shows a progress state
- [x] red-selenium — added `EXPORT_SPINNER=[data-testid='export-spinner']` + `trigger_throttled_pdf_export` + `assert_exporting_indicator_is_shown` (WebDriverWait on visibility, throttle holds GET /export open, open-before-throttle ordering) to `manual_editor_export_control_statements.py` (155 lines). New skipped class `TestExportControlProgressAcceptance`. Analytical RED: indicator not rendered yet → live run would TimeoutException on the visibility wait; green-frontend adds the spinner. test-review PASS 0 fixes. Live run deferred to green-selenium.
- [x] red-frontend — new `ExportControl.progress.test.tsx` (67 lines, `describe.skip`): 3 tests pinning `export-spinner` edges via manually-resolvable deferred — (1) `queryByTestId` null when idle, (2) `getByTestId` visible while in-flight, (3) `waitForElementToBeRemoved` after resolve (success path; reject=3.2). RED confirmed: 2 failed (rising+falling edge, TestingLibraryElementError "Unable to find [data-testid=export-spinner]") + 1 passed (idle-absent), matched prediction exactly. Closes the convergent rising-edge-only gap. test-review PASS 0 fixes.
- [x] green-frontend — added inline `{isExporting && <span data-testid="export-spinner" className="me-export-spinner" aria-hidden />}` as a `.me-export-control` descendant (right after trigger), + `.me-export-spinner`/`me-export-spin` keyframes in ExportControl.css mirroring the `.me-save-spinner` precedent. No new state — reuses `isExporting` (cleared on resolve AND reject via existing `.finally`), so error-path removal is free before 3.2. Removed `describe.skip`. Progress file 3/3 pass; ExportControl 5/5; generation suite 176/176, 0 regressions. ExportControl.tsx 82 lines, .css 96 lines. Followed premortem guidance (inline not portal → jsdom+selenium agree). 2.1 disabled-lock untouched. **Review passes on de21f55 were cut off by a session limit (non-gating, commit stands); refactor was a no-op.** **a11y follow-up (partial agent-review probe):** the spinner is `aria-hidden="true"` with no text, so a screen-reader user gets NO feedback that an export is in progress — for a "progress state" scenario consider `role="status"`/`aria-live="polite"` with an sr-only label, and a `prefers-reduced-motion` guard on the spin keyframes (premortem candidate). Deferred — not required for the minimal green; raise as a polish/red step if desired.
- [S] red-frontend-api — UI scenario 3.1 (progress indicator) is pure client-side state: the spinner rides the existing `exportDocument` in-flight window (gated on `isExporting`), no new frontend-api surface. The export transport is already covered by 2.1's green-frontend-api. (API §3.1 in 01_API_Tests is a backend filename-encoding concern, not this UI layer.) Same rationale as 1.1.
- [S] green-frontend-api — same reason; no API for the progress indicator.
- [x] align-design — no CSS change needed: `.me-export-spinner` already matches the `.me-save-spinner` precedent exactly (14px, 2px border `rgba(17,18,20,0.35)`, `border-top-color:var(--btn-primary-fg)`, 0.7s linear) + editor tokens; only `align-self:center` added (correct for the inline-flex row) and a namespaced `me-export-spin` keyframe. No mockup for story 17. design-review PASS (no placeholder data, no divergent magic values). Coverage: ExportControl.tsx 100% statements/branches/lines — new spinner branch covered both edges; lone uncovered fn is the `.catch(()=>{})` rejection handler, correctly deferred to 3.2.
- [x] green-selenium — removed `@pytest.mark.skip` from `TestExportControlProgressAcceptance` (and the now-dead `import pytest`, its sole user). Real Chrome (:8100/:5273), **2 clean runs** (9.70s, 7.30s), spinner visible in-flight both. No flake/landmine, no chromedriver orphans. Spinner already shipped in green-frontend 3.1 (de21f55), so acceptance passed as-is on unskip.
- [S] demo — autonomous loop, no interactive viewer; behavior already proven in real Chrome by green-selenium (2 clean runs). Run `/demo TestExportControlProgressAcceptance` manually to watch.

### Scenario 3.2: An export error is shown with retry, document unchanged
- [x] red-selenium — new skipped class `TestExportControlErrorAcceptance` + `ExportErrorStatementsMixin` (CDP `Network.setBlockedURLs` on `*/export*` for a deterministic failed GET; `trigger_failed_pdf_export`, `assert_export_error_with_retry_is_shown`, `assert_document_view_is_unchanged`). Split shared `export_control_locators.py` (avoid circular import) — all files <200. Analytical RED (prod `.catch(()=>{})` swallows the reject at ExportControl.tsx:34, no `export-error`/`export-retry` node exists): predicted `TimeoutException` on the `export-error` visibility wait, matched. test-review 3 strict fixes: pinned error text `"Не удалось экспортировать документ"`, retry label `"Повторить"`, and a real content-baseline unchanged assertion (captured before the blocked GET). green-selenium performs the live remove-marker run.
- [~] red-frontend
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
