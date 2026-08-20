> These are additional edge case tests. Implement after core tests pass.

# Manual input mode (non-AI document creation) — UI Tests (Extended)

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the visitor) | `qa.manual@textery.test` / `Qa!Manual2026` |
| Document A1 | id `3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3`, `document_type` `реферат`, `content` `""`, `version` `1` |
| Editor route | `/documents/3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3` |
| Toolbar controls | `.me-toolbar-btn` elements; active class `active` |

## 1. Formatting Edge Cases

### TC-05-UI-EXT-1.1 — Toggling a numbered list off returns to plain paragraphs

| Field | Value |
|---|---|
| Description | Un-toggling a list must remove the wrapper node, not just the items. An empty `<ol>` left behind renders as stray indentation the user cannot delete. |
| Preconditions | The editor is open on document A1 with the content `<ol><li>Первый</li><li>Второй</li></ol>` and the whole list selected. |
| Test data | Control: the numbered-list toolbar button; expected content after the toggle `<p>Первый</p><p>Второй</p>` |
| Steps | 1. Select the entire numbered list.<br>2. Click the numbered-list toolbar button to toggle it off.<br>3. Read the editor's `getHTML()`. |
| Expected result | The content is `<p>Первый</p><p>Второй</p>` — both items survive as plain paragraphs; no `<ol>` or `<li>` element remains, and no empty list wrapper is left in the document. |
| Status | Not run |

## 2. Unsaved State

No test-spec scenario asserts a navigate-away/refresh confirm-guard for unsaved editor
content. This is deliberate, not an oversight: the story spec (`05_ManualMode.md`, Core
Requirements) explicitly names unsaved-edit loss on navigation as an **accepted,
temporary posture** in this story — no autosave, no confirm-guard — with that
protection owned by story #10. Adding a warn-before-discard test here would contradict
the spec's own stated scope; that guard belongs in story #10's test-spec once autosave
lands.

## 3. Reopen Edge Cases

### TC-05-UI-EXT-3.1 — Reopening a document that was never saved shows the empty editor, not an error

| Field | Value |
|---|---|
| Description | A client that treats an empty `content` string as a failed fetch shows an error state for a perfectly valid brand-new document, making it look broken before the user has typed a word. |
| Preconditions | Document A1 was created via the mode modal but no save has ever succeeded for it — its stored `content` is `""` at `version` `1`. |
| Test data | Route `/documents/3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3`; `GET /api/v1/documents/{document_id}` answering `200 OK` with `content` `""` |
| Steps | 1. Navigate to the editor route for document A1 in a fresh session.<br>2. Inspect the rendered page. |
| Expected result | The editor renders an empty content area with its placeholder and an enabled toolbar; no error banner, no "не найдено" message and no loading skeleton is shown; the visitor can type immediately. |
| Status | Not run |
