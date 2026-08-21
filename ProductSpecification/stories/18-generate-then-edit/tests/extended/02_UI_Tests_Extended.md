> These are additional edge case tests. Implement after core tests pass.

# Generate → edit — UI Tests (Extended)

Selenium against the real stack. The editor surface is story-5's; this story adds the
auto-open-from-generation path and removes the mode-select modal.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.convert@textery.test` / `Qa!Convert2026` |
| Document type | `Доклад` (wire value `доклад`) |
| Topic | `История Москвы`, typed into `[data-testid="topic-input"]`, submitted with `[data-testid="topic-send"]` |
| Generating state | `[data-testid="generation-generating"]`, panel `[data-testid="chat-panel"]`, heading `Ход генерации` |
| Editor surface | `[data-testid="manual-editor"]`, body `[data-testid="doc-body"]`, breadcrumb `[data-testid="editor-breadcrumb"]` |
| Editor error banner | `[data-testid="doc-error"]` with `[data-testid="doc-reset"]` |
| Generated content | `<h2>Введение</h2><p>Первый абзац.</p>` |
| Poll endpoint | `GET /api/v1/generations/{id}` |
| Conversion endpoint | `POST /api/v1/documents/from-generation` with an `Idempotency-Key` header |
| History | `[data-testid="history-page"]`, rows `[data-testid="history-document-row"]` |

## 1. Transition Edge Cases

### TC-18-UI-EXT-1.1 — Out-of-order poll responses bind to the latest

| Field | Value |
|---|---|
| Description | Polls overlap on a slow network. If the editor binds whichever response arrives last rather than the newest one, a delayed earlier poll overwrites the completed result and the user sees stale or empty content. |
| Preconditions | Account A signed in; a generation started for type `Доклад` and topic `История Москвы`; `[data-testid="generation-generating"]` visible; the poll endpoint is stubbed so poll #1 (`status: generating`, no content) is delayed to resolve **after** poll #2 (`status: completed`, content `## Введение\n\nПервый абзац.`). |
| Test data | Poll #2 completes at t=1 s and resolves at t=1.2 s; poll #1 issued at t=0.5 s but resolves at t=1.5 s; expected visible text `Введение` and `Первый абзац.` |
| Steps | 1. Start the generation and wait for the overlapping polls to both resolve (≥ t=2 s).<br>2. Wait for `[data-testid="manual-editor"]` to appear.<br>3. Read the text of `[data-testid="doc-body"]`. |
| Expected result | The editor opens and `[data-testid="doc-body"]` shows `Введение` and `Первый абзац.` — the completed poll's content, not the stale `generating` result; `[data-testid="generation-generating"]` is gone from the DOM and does not reappear after the late poll resolves; `[data-testid="doc-error"]` never appears. |
| Status | Not run |

### TC-18-UI-EXT-1.2 — A retry after a conversion error succeeds without duplicating

| Field | Value |
|---|---|
| Description | A retry that reuses the same idempotency key must open one document; a retry that mints a fresh key creates a second document for one generation, and the user finds two rows in history for a single request. |
| Preconditions | Account A signed in; a generation completed; the first `POST /api/v1/documents/from-generation` is forced to fail (`500`), the second succeeds; account A's history is empty at the start. |
| Test data | First conversion call `500` with `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}`; second call `201 Created`; generated content `<h2>Введение</h2><p>Первый абзац.</p>` |
| Steps | 1. Let the generation complete and the auto-transition fire; wait for `[data-testid="doc-error"]`.<br>2. Click `[data-testid="doc-reset"]` to retry.<br>3. Wait for `[data-testid="manual-editor"]`.<br>4. Navigate to `[data-testid="history-page"]` and count `[data-testid="history-document-row"]`. |
| Expected result | After step 3 exactly one editor is open, `[data-testid="doc-body"]` shows `Введение` and `Первый абзац.`, and `[data-testid="doc-error"]` is gone from the DOM; step 4 shows exactly one `[data-testid="history-document-row"]` — one document, not two. |
| Status | Not run |

## 2. Editor State

### TC-18-UI-EXT-2.1 — Saving clears the unsaved-state guard

| Field | Value |
|---|---|
| Description | The guard that warns on leaving with unsaved edits must be cleared by a successful save; a guard keyed to "the document was ever edited" fires on every navigation afterwards and trains the user to dismiss it. |
| Preconditions | Account A signed in; a generated document is open in `[data-testid="manual-editor"]`; the user has typed an edit into `[data-testid="doc-body"]` so the unsaved-state guard is armed. |
| Test data | Edit text `Добавленный абзац.`; save via the editor's save control; navigation target `[data-testid="history-page"]` |
| Steps | 1. Type `Добавленный абзац.` into `[data-testid="doc-body"]`.<br>2. Save and wait for the save to complete (`PUT /api/v1/documents/{id}` answers `200 OK`).<br>3. Navigate away to the history page.<br>4. Check for a browser `beforeunload` dialog or an in-app unsaved-changes confirmation. |
| Expected result | Navigation completes straight to `[data-testid="history-page"]`; no `beforeunload` dialog is raised and no in-app unsaved-changes confirmation is rendered; reopening the document shows `Добавленный абзац.`, confirming the save that cleared the guard actually persisted. |
| Status | Not run |
