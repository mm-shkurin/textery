<!-- COPIED FILE. Source of truth: ProductSpecification/stories/18-generate-then-edit/tests/02_UI_Tests.md
     Regenerate with `node scripts/sync-test-cases.mjs` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> **Implementation Order**: Tests are numbered for sequential TDD implementation.
> Start with the flow change (mode modal gone), then the auto-transition, then the
> non-happy async states, then the unsaved-state guard.

# Generate → edit — UI Tests

Selenium against the real stack. The editor surface is story-5's; this story adds the
auto-open-from-generation path and removes the mode-select modal.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.convert@textery.test` / `Qa!Convert2026` |
| Document type | `Доклад` (wire value `доклад`) |
| Topic | `История Москвы`, typed into `[data-testid="topic-input"]`, submitted with `[data-testid="topic-send"]` |
| Type modal | `[data-testid="type-modal"]` — the type picker; there is **no** mode-select ("сгенерировать / чистый лист") step after it |
| Generating state | `[data-testid="generation-generating"]`, panel `[data-testid="chat-panel"]`, heading `Ход генерации` |
| Failure state | error bubble text `Не удалось завершить` plus `[data-testid="error-reset"]` |
| Editor surface | `[data-testid="manual-editor"]`, body `[data-testid="doc-body"]`, breadcrumb `[data-testid="editor-breadcrumb"]` |
| Editor error banner | `[data-testid="doc-error"]` with `[data-testid="doc-reset"]` |
| Generated content | `<h2>Введение</h2><p>Первый абзац.</p>` |
| Poll endpoint | `GET /api/v1/generations/{id}` |
| Conversion endpoint | `POST /api/v1/documents/from-generation` with an `Idempotency-Key` header |
| History | `[data-testid="history-page"]`, rows `[data-testid="history-document-row"]` |

---

## 1. Flow Display

### TC-18-UI-1.1 — Selecting a type goes straight to generation

| Field | Value |
|---|---|
| Description | The mode-select modal is removed by this story; if it survives, the user pays an extra click before every generation and the auto-open path is never entered. |
| Preconditions | Account A signed in and on the create flow; no generation in progress. |
| Test data | Type `Доклад`, topic `История Москвы` |
| Steps | 1. Open the create flow and pick `Доклад` in `[data-testid="type-modal"]`.<br>2. Type `История Москвы` into `[data-testid="topic-input"]` and click `[data-testid="topic-send"]`.<br>3. Read the DOM and the network log. |
| Expected result | `POST /api/v1/generations` is dispatched and `[data-testid="generation-generating"]` appears; no mode-select modal is rendered at any point between the type choice and the generating state. |
| Status | Not run |

### TC-18-UI-1.2 — A generating document shows progress

| Field | Value |
|---|---|
| Description | An LLM call takes tens of seconds; with no progress state the user sees a dead screen and starts over. |
| Preconditions | A generation has been started for account A and the poll is answering `pending`/`in_progress`. |
| Test data | Poll stubbed to `status = in_progress` for 3 consecutive polls |
| Steps | 1. Start a generation for topic `История Москвы`.<br>2. Assert on the DOM while the poll still reports a non-terminal status. |
| Expected result | `[data-testid="generation-generating"]` is present, the panel shows the heading `Ход генерации` and the active writing message with the typing indicator; the editor `[data-testid="manual-editor"]` is not yet mounted. |
| Status | Not run |

---

## 2. Auto-Transition to Editor

### TC-18-UI-2.1 — A completed generation opens automatically in the editor

| Field | Value |
|---|---|
| Description | The story's headline behaviour: the user watches the text being written and is then editing it, with nothing to click in between. |
| Preconditions | A generation started for account A; the poll returns `completed` with content `## Введение\n\nПервый абзац.` on its third response. |
| Test data | Generation id `4d2a8f16-7c53-4e09-b1a7-58e3c0d9b426`; expected editor text `Введение` and `Первый абзац.` |
| Steps | 1. Start the generation and wait for the poll to report `completed`.<br>2. Do not click anything.<br>3. Read the DOM and the network log. |
| Expected result | `POST /api/v1/documents/from-generation` is dispatched automatically; `[data-testid="manual-editor"]` mounts and `[data-testid="doc-body"]` shows `Введение` as a heading and `Первый абзац.`; the generating state is gone; no user click occurred between completion and the editor appearing. |
| Status | Not run |

### TC-18-UI-2.2 — The auto-transition fires the conversion exactly once

| Field | Value |
|---|---|
| Description | Two polls can both observe `completed` before the first conversion returns; a per-observation dispatch then sends two POSTs and races the backend's constraint on every generation. |
| Preconditions | A generation in flight; the conversion response delayed by ≥ 2 s; the poll interval short enough that a second poll lands inside that window. |
| Test data | Poll responses 3 and 4 both `completed`; conversion delayed `2 s` |
| Steps | 1. Start the generation.<br>2. Let both `completed` polls land while the first conversion is still pending.<br>3. Count requests to `/api/v1/documents/from-generation`. |
| Expected result | Exactly one `POST /api/v1/documents/from-generation` is sent; the editor mounts once; no second document appears in history. |
| Status | Not run |

### TC-18-UI-2.3 — The editor is populated from the conversion response, not a re-read

| Field | Value |
|---|---|
| Description | On a multi-instance backend a `GET` issued right after the conversion can hit an instance that has not seen the write — the user would then watch their text appear and then vanish. |
| Preconditions | The conversion succeeds normally; the document read path is stubbed to serve a stale body. |
| Test data | Conversion response content `<h2>Введение</h2><p>Первый абзац.</p>`; stubbed `GET /api/v1/documents/{id}` returns `<p>Устаревшее содержимое.</p>` |
| Steps | 1. Complete a generation and let the auto-conversion run.<br>2. Read `[data-testid="doc-body"]` once the editor mounts.<br>3. Inspect the network log for a `GET /api/v1/documents/{id}` on this path. |
| Expected result | The editor shows `Введение` and `Первый абзац.` from the conversion response; `Устаревшее содержимое.` is never rendered; no document re-read is issued on the auto-open path. |
| Status | Not run |

---

## 3. Editing

### TC-18-UI-3.1 — The generated document is editable and saves

| Field | Value |
|---|---|
| Description | A generated document that cannot be saved is read-only in practice — the user's edits are lost on the next navigation. |
| Preconditions | A generated document is open in the editor via the auto-transition; its `documentId` and `version` `1` are in hand. |
| Test data | Appended text `Мой собственный абзац.`; save via the editor's save control |
| Steps | 1. Click into `[data-testid="doc-body"]` and type `Мой собственный абзац.`.<br>2. Save.<br>3. Reload the page and reopen the document from history. |
| Expected result | `PUT /api/v1/documents/{id}` is sent with `version` `1` and answers `2xx`; the save status settles to saved with no error banner; after the reload the editor shows both the generated text and `Мой собственный абзац.`. |
| Status | Not run |

---

## 4. Non-Happy Async States

### TC-18-UI-4.1 — A failed generation shows a distinct error, not a perpetual spinner

| Field | Value |
|---|---|
| Description | Without a first-class failure state a `failed` generation renders as the generating spinner forever, and the user waits on work that will never finish. |
| Preconditions | A generation started for account A; the poll returns `status = failed`. |
| Test data | Poll response `{"status": "failed"}`; expected text `Не удалось завершить` |
| Steps | 1. Start a generation and let the poll report `failed`.<br>2. Read the DOM. |
| Expected result | The failure bubble with the text `Не удалось завершить` is shown along with a retry control (`[data-testid="error-reset"]`); `[data-testid="generation-generating"]` is gone; the failure node is visually distinct from the generating state (error styling, not the typing indicator); no conversion request is sent. |
| Status | Not run |

### TC-18-UI-4.2 — A conversion error keeps the text and offers retry

| Field | Value |
|---|---|
| Description | The generated text exists only in this response; if a failed conversion clears the screen, the user loses text the model already produced and must pay for another generation. |
| Preconditions | A generation completes normally; `POST /api/v1/documents/from-generation` is stubbed to answer `500`. |
| Test data | Conversion stubbed `500` `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}`; generated text `Первый абзац.` |
| Steps | 1. Let the generation complete and the auto-conversion fail.<br>2. Read the DOM.<br>3. Remove the stub and click the retry control.<br>4. Read the DOM again. |
| Expected result | An inline error is shown with a retry control; the generated text `Первый абзац.` is still visible; step 3 re-issues exactly one `POST /api/v1/documents/from-generation` and the editor then opens on that same text — nothing was regenerated and nothing was lost. |
| Status | Not run |

### TC-18-UI-4.3 — A transient poll error shows a distinct error, not a spinner

| Field | Value |
|---|---|
| Description | A dropped poll leaves the client with no status; showing the spinner in that state is indistinguishable from progress, so the user never learns anything went wrong. |
| Preconditions | A generation in flight; one poll request is made to fail at the transport level. |
| Test data | `GET /api/v1/generations/{id}` fails once (network error), then recovers |
| Steps | 1. Start a generation.<br>2. Force the next poll to fail.<br>3. Read the DOM.<br>4. Use the retry control. |
| Expected result | An error state with a retry is shown, visually distinct from the generating state; step 4 resumes polling and the flow continues to the editor once the generation completes. |
| Status | Not run |

### TC-18-UI-4.4 — A generation that never finishes stops at the client deadline

| Field | Value |
|---|---|
| Description | A generation stuck in a non-terminal state would otherwise be polled forever — a spinner with no end and a poll loop hammering the status endpoint. |
| Preconditions | A generation in flight whose poll always answers `in_progress`. |
| Test data | Client poll deadline (e.g. `180 s`); poll always `in_progress` |
| Steps | 1. Start a generation with the poll pinned to `in_progress`.<br>2. Advance past the client deadline.<br>3. Read the DOM and count polls after the deadline. |
| Expected result | The generating state is replaced by an error/retry state at the deadline; no further poll requests are issued after it; the client does not spin indefinitely. |
| Status | Not run |
| Note | The deadline value belongs to story 1's poll ownership — assert against the configured value rather than re-declaring one here. |

---

## 5. Unsaved-State Protection

### TC-18-UI-5.1 — Leaving with unsaved edits is guarded

| Field | Value |
|---|---|
| Description | Auto-open puts the user straight into an editor holding unsaved text; a refresh or a back-click would discard it with no warning. |
| Preconditions | A generated document open in the editor with an unsaved edit (dirty state). |
| Test data | Typed text `Несохранённый абзац.`; then a page refresh and a navigation away |
| Steps | 1. Type `Несохранённый абзац.` into the editor and do not save.<br>2. Trigger a page refresh.<br>3. Dismiss/accept the guard, then attempt an in-app navigation away. |
| Expected result | The browser's beforeunload confirmation appears before the refresh completes; the in-app navigation is likewise guarded; cancelling leaves the editor and the typed text intact. |
| Status | Not run |

---

## 6. Secondary Entry & Navigation

### TC-18-UI-6.1 — A blank document can still be started from scratch

| Field | Value |
|---|---|
| Description | Removing the mode-select modal must not remove the blank-document entry — writing from scratch is still a supported way in. |
| Preconditions | Account A signed in and on the create flow. |
| Test data | The «чистый лист» entry on the create flow |
| Steps | 1. Open the create flow.<br>2. Choose the blank-document entry.<br>3. Read the DOM and the network log. |
| Expected result | `[data-testid="manual-editor"]` mounts with an empty `[data-testid="doc-body"]`; `POST /api/v1/documents` is sent and `POST /api/v1/generations` is not; the created document's `generation_id` is `null`. |
| Status | Not run |

### TC-18-UI-6.2 — The converted document appears in history

| Field | Value |
|---|---|
| Description | History lists documents, and a generated one is a document — listing the generation as well would show the user the same work twice. |
| Preconditions | Account A has completed one generation, let it convert, and saved an edit. |
| Test data | Document title derived from topic `История Москвы`; expected exactly one matching row |
| Steps | 1. Complete the generate → convert → save flow once.<br>2. Open the history page.<br>3. Count `[data-testid="history-document-row"]` entries matching that title. |
| Expected result | `[data-testid="history-page"]` lists exactly one row for the converted document, showing the saved title; no separate generation entry is listed alongside it — no duplicated generation-plus-document pair. |
| Status | Not run |
