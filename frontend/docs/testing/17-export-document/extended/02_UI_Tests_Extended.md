<!-- COPIED FILE. Source of truth: ProductSpecification/stories/17-export-document/tests/extended/02_UI_Tests_Extended.md
     Regenerate with `node scripts/sync-test-cases.mjs` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Export document — UI Tests (Extended)

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

## 1. Retry

### TC-17-UI-EXT-1.1 — A retry after an export error succeeds

| Field | Value |
|---|---|
| Description | An error banner is only useful if the retry it offers actually works — a control left disabled, or an in-flight lock never released after a failure, strands the user on the error state. |
| Preconditions | Account A signed in; document A1 open in the editor; the download dir is empty; the first export call is forced to fail (backend answers `500` once, then succeeds). |
| Test data | Document A1; first call `500` with `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}`, second call `200 OK` with a PDF; expected file `Отчёт по практике.pdf` |
| Steps | 1. Click `[data-testid="export-control-trigger"]`, then `[data-testid="export-option-pdf"]`.<br>2. Wait for `[data-testid="export-error"]`.<br>3. Click `[data-testid="export-retry"]` (`Повторить`).<br>4. Wait for `[data-testid="export-spinner"]` to disappear and list the download dir. |
| Expected result | After step 2 the banner text is exactly `Не удалось экспортировать документ` and the download dir is still empty; after step 4 the banner and the spinner are gone from the DOM and the download dir holds exactly one file, `Отчёт по практике.pdf`, whose first five bytes are `%PDF-`. |
| Status | Not run |

## 2. Format Choice

### TC-17-UI-EXT-2.1 — Both formats can be exported in one session

| Field | Value |
|---|---|
| Description | The in-flight lock must release after a completed export; if it does not, the second format is unreachable without a page reload and only the first download ever lands. |
| Preconditions | Account A signed in; document A1 open in the editor; the download dir is empty. |
| Test data | Document A1; expected files `Отчёт по практике.pdf` and `Отчёт по практике.docx` |
| Steps | 1. Click `[data-testid="export-control-trigger"]`, then `[data-testid="export-option-pdf"]`; wait for `[data-testid="export-spinner"]` to disappear.<br>2. Click `[data-testid="export-control-trigger"]` again, then `[data-testid="export-option-docx"]`; wait for the spinner to disappear.<br>3. List the download dir. |
| Expected result | The trigger is enabled again before step 2 (not stuck in the in-flight state); the download dir contains exactly two files — `Отчёт по практике.pdf` (first bytes `%PDF-`) and `Отчёт по практике.docx` (first bytes `PK`); `[data-testid="export-error"]` never appears. |
| Status | Not run |
