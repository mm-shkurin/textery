<!-- COPIED FILE. Source of truth: ProductSpecification/stories/17-export-document/tests/02_UI_Tests.md
     Regenerate with `node scripts/sync-test-cases.mjs` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> **Implementation Order**: sequential TDD — control display → in-flight lock → states →
> stale-guard → download.

# Export document — UI Tests

Selenium against the real stack. Headless Chrome download dir configured; assert the file
lands, not the render.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.export@textery.test` / `Qa!Export2026` |
| Document A1 | id `7f1c2d84-0b2e-4c31-9a55-2f7b41d0e913`, title `Отчёт по практике`, content `<p>Первый абзац.</p>` |
| Editor URL | the editor surface opened on document A1 |
| Export trigger | `[data-testid="export-control-trigger"]`, visible label `Экспорт` |
| Export menu | `[data-testid="export-menu"]` with `[data-testid="export-option-pdf"]` (`PDF`) and `[data-testid="export-option-docx"]` (`DOCX`) |
| In-flight spinner | `[data-testid="export-spinner"]` |
| Error banner | `[data-testid="export-error"]`, text `Не удалось экспортировать документ`; retry `[data-testid="export-retry"]`, label `Повторить` |
| Export request | `GET /api/v1/documents/{id}/export?format=pdf|docx` |
| Download dir | headless Chrome `download.default_directory`, emptied before each case |

## 1. Control Display

### TC-17-UI-1.1 — The editor offers a PDF and a DOCX export choice

| Field | Value |
|---|---|
| Description | Both formats the endpoint accepts must be reachable from the editor; a menu offering only PDF silently drops half the feature. |
| Preconditions | Account A signed in; document A1 open in the editor; the export menu is closed (not in the DOM). |
| Test data | Document A1; expected labels `PDF` and `DOCX` |
| Steps | 1. Click `[data-testid="export-control-trigger"]`.<br>2. Read the options rendered inside `[data-testid="export-menu"]`. |
| Expected result | The menu is present with `aria-expanded="true"` on the trigger; it contains exactly two `role="menuitem"` buttons, `[data-testid="export-option-pdf"]` reading `PDF` and `[data-testid="export-option-docx"]` reading `DOCX`. |
| Status | Not run |

## 2. In-Flight Safety

### TC-17-UI-2.1 — The export control is disabled while a request is in flight

| Field | Value |
|---|---|
| Description | An impatient double-click must not start a second CPU-heavy render or download the same file twice. |
| Preconditions | Document A1 open; the export response is delayed (≥ 2 s) so the in-flight window can be observed; the network log is captured. |
| Test data | `format=pdf`; second click issued < 500 ms after the first |
| Steps | 1. Open the export menu and click `[data-testid="export-option-pdf"]`.<br>2. While the request is still pending, click `[data-testid="export-option-pdf"]` again.<br>3. Count the requests to `/api/v1/documents/7f1c2d84-0b2e-4c31-9a55-2f7b41d0e913/export?format=pdf`. |
| Expected result | Exactly one export request is sent; during the in-flight window both option buttons carry `disabled` and `aria-disabled="true"`; the lock is released after the response (the buttons are enabled again). |
| Status | Not run |

## 3. States

### TC-17-UI-3.1 — An in-flight export shows a progress state

| Field | Value |
|---|---|
| Description | A CPU-heavy render takes seconds; with no indicator the user believes the click did nothing and clicks again. |
| Preconditions | Document A1 open; the export response is delayed (≥ 2 s). |
| Test data | `format=pdf` |
| Steps | 1. Open the export menu and click `[data-testid="export-option-pdf"]`.<br>2. Assert while the request is pending.<br>3. Assert again after the file has downloaded. |
| Expected result | `[data-testid="export-spinner"]` is present in the DOM while the request is pending and absent after it resolves. |
| Status | Not run |

### TC-17-UI-3.2 — An export error is shown with retry, document unchanged

| Field | Value |
|---|---|
| Description | A failed render must not clear the editor or discard the text; the user needs a visible reason and a way to try again. |
| Preconditions | Document A1 open; the export endpoint is stubbed to answer `500` with the generic error body. |
| Test data | `format=pdf`; expected text `Не удалось экспортировать документ`; retry label `Повторить` |
| Steps | 1. Record the editor's visible content.<br>2. Open the export menu and click `[data-testid="export-option-pdf"]`.<br>3. Wait for the response.<br>4. Re-read the editor's visible content and the download directory. |
| Expected result | `[data-testid="export-error"]` is shown with `role="alert"` and exactly the text `Не удалось экспортировать документ` (never the raw error such as `Failed to fetch`); `[data-testid="export-retry"]` is present with accessible name `Повторить`; the editor content in step 4 equals step 1; no file was written to the download directory. |
| Status | Not run |

## 4. Stale-While-Dirty Guard

### TC-17-UI-4.1 — Exporting with unsaved edits saves or warns first

| Field | Value |
|---|---|
| Description | Export renders the **stored** HTML — exporting a dirty editor would hand the user a file missing the paragraph they just typed, with no sign anything was wrong. |
| Preconditions | Document A1 open with an unsaved edit in the editor (dirty state); the network log is captured. |
| Test data | Typed text `Несохранённый абзац.`; `format=pdf` |
| Steps | 1. Type `Несохранённый абзац.` into the editor and do not save.<br>2. Open the export menu and click `[data-testid="export-option-pdf"]`.<br>3. Read the ordered network log. |
| Expected result | Either a `PUT /api/v1/documents/{A1}` completes **before** the `GET …/export?format=pdf` is dispatched and the downloaded file contains `Несохранённый абзац.`, or the user is warned the export would be stale before any export request is sent. If the save is rejected, no export request is dispatched at all and the save-error banner — not the generic export banner — is what the user sees. |
| Status | Not run |

## 5. Download

### TC-17-UI-5.1 — A successful export delivers a downloaded file

| Field | Value |
|---|---|
| Description | Resolving a blob in JavaScript is not a download; only a real browser writing a real file proves the whole path. |
| Preconditions | Account A signed in; document A1 open; the download directory is empty. |
| Test data | Document A1, `format=pdf`; expected file `document.pdf` |
| Steps | 1. Open the export menu and click `[data-testid="export-option-pdf"]`.<br>2. Wait for the download to finish (no `.crdownload` left).<br>3. List the download directory and read the file's first bytes. |
| Expected result | Exactly one file is written, named `document.pdf`; its size is greater than zero; its first five bytes are `%PDF-`; no error banner is shown. |
| Status | Not run |
