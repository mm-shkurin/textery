> **Implementation Order**: sequential TDD — block schema first (everything stands on it),
> then lists, autosave, title, paste-sanitize, undo/redo, count, tables.

# Story 5 — Editor Extension Tests (points 1–8)

Covers the editor upgrade in `editor-extension.md`. Mostly frontend; the `title` column is
backend (shared with stories 17/18).

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the owner) | `qa.manual@textery.test` / `Qa!Manual2026` |
| Document A1 (block schema) | id `3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3`, `document_type` `реферат`, `version` `2` |
| Document A2 (legacy inline-only) | id `8c4e0a5d-19f7-4b62-8d31-c07a5e94b6f2`, `content` `Первая строка<br>Вторая строка`, saved before the block-schema migration |
| Save request | `PUT /api/v1/documents/{document_id}` with `{"content": …, "title": …, "version": …}` |
| Title limit | 200 Unicode code points, NFC-normalized, trimmed; over-length rejected, never truncated |
| Autosave debounce | 1 s idle after the last keystroke |
| Error body shape | `{"error_code": "<CODE>", "message": "<generic text>"}` |

## 1. Block Schema

### TC-05-EXT-1.1 — Multi-paragraph block content round-trips

| Field | Value |
|---|---|
| Description | The schema upgrade from inline-only to block nodes is the foundation of every other case here; a block that serializes but does not parse back collapses the whole document to one paragraph on reload. |
| Preconditions | Document A1 is open in the upgraded editor. |
| Test data | Content `<h1>Заголовок</h1><h2>Подзаголовок</h2><h3>Раздел</h3><p>Первый абзац.</p><p>Второй абзац.</p>` |
| Steps | 1. Enter that block content in the editor.<br>2. Save the document (`PUT /api/v1/documents/{A1}`).<br>3. Reload the page and re-open document A1. |
| Expected result | Save answers `200 OK`; on reload each block returns as its own semantic element — one `<h1>`, one `<h2>`, one `<h3>` and two separate `<p>` nodes with their original text; no block is merged into another and none is downgraded to plain text. |
| Status | Not run |

### TC-05-EXT-1.2 — An existing inline-only document loads without data loss

| Field | Value |
|---|---|
| Description | Documents written under the old inline-only schema exist in production. A parser that only accepts block nodes silently discards their content on open. |
| Preconditions | Document A2 exists, saved under the pre-migration inline-only schema, and has not been touched since. |
| Test data | Document A2 id `8c4e0a5d-19f7-4b62-8d31-c07a5e94b6f2`, stored content `Первая строка<br>Вторая строка` |
| Steps | 1. Open document A2 in the upgraded editor.<br>2. Inspect the rendered content and the editor's `getHTML()`. |
| Expected result | Both lines render, separated by the line break; no text is dropped and no error state is shown; the editor is editable rather than read-only or blank. |
| Status | Not run |

### TC-05-EXT-1.3 — Inline marks survive co-resident with block nodes

| Field | Value |
|---|---|
| Description | The base round-trip only exercises bare-text blocks. A schema that declares block nodes without re-declaring the inline marks strips bold and links from inside them on the first save. |
| Preconditions | Document A1 is open in the upgraded editor. |
| Test data | Content `<h2>Раздел с <b>жирным</b></h2><p style="text-align:center"><i>курсив</i>, <code>код</code> и <a href="https://textery.test/doc">ссылка</a></p>` |
| Steps | 1. Enter that mixed inline+block content.<br>2. Save the document.<br>3. Reload and re-open document A1. |
| Expected result | On reload every mark is still inside its block node: the `<b>` inside the `<h2>`, and the `<i>`, `<code>`, the `<a href="https://textery.test/doc">` and the centred alignment inside the `<p>` — none stripped, none hoisted out of its block. |
| Status | Not run |

> Added by ADR `decisions/block-schema-migration-decision.md` (premortem gap #2): the base
> block round-trip (1.1) only exercises bare-text blocks; this pins mixed inline+block content.

## 2. Lists

### TC-05-EXT-2.1 — Bulleted and numbered lists round-trip

| Field | Value |
|---|---|
| Description | Lists are nested block nodes; a schema that flattens them on save returns the items as loose paragraphs with the numbering gone. |
| Preconditions | Document A1 is open in the upgraded editor. |
| Test data | Content `<ul><li>Пункт первый</li><li>Пункт второй</li></ul><ol><li>Шаг один</li><li>Шаг два</li></ol>` |
| Steps | 1. Insert a bulleted list with two items and a numbered list with two items.<br>2. Save the document.<br>3. Reload and re-open document A1. |
| Expected result | On reload the content contains one `<ul>` with two `<li>` and one `<ol>` with two `<li>`, in that order, with the original item text; neither list is flattened to `<p>` nodes and the ordered list still renders 1., 2. |
| Status | Not run |

## 3. Autosave

### TC-05-EXT-3.1 — Edits autosave without an explicit click

| Field | Value |
|---|---|
| Description | Autosave is the whole point of the feature — if the debounce never fires, the user loses everything typed since their last manual save. |
| Preconditions | Document A1 is open with unsaved edits and the `Сохранить` button untouched. |
| Test data | Typed text `Автосохранение работает`; debounce 1 s; expected request `PUT /api/v1/documents/{A1}` |
| Steps | 1. Type the text into the editor.<br>2. Stop typing and wait past the 1 s debounce without clicking anything.<br>3. Observe the network requests and the save indicator. |
| Expected result | Exactly one `PUT /api/v1/documents/{A1}` is issued after the debounce, carrying the typed content and the current `version`; it answers `200 OK`; a saved indicator (`Сохранено`) appears without any click. |
| Status | Not run |

### TC-05-EXT-3.2 — A failed autosave keeps the content and shows the failure

| Field | Value |
|---|---|
| Description | Autosave failures are invisible by nature — the user did not initiate the save. Silently dropping the failure lets them keep typing over content that is not being persisted. |
| Preconditions | Document A1 is open with edits; the save endpoint is stubbed to answer `500 {"error_code": "INTERNAL_ERROR", …}`. |
| Test data | Typed text `Текст, который нельзя потерять`; failing response `500` |
| Steps | 1. Type the text and wait for the autosave to fire.<br>2. Let the `500` arrive.<br>3. Inspect the editor content and the save indicator. |
| Expected result | The editor still contains `Текст, который нельзя потерять` — never cleared or reverted; a failed-save state is visibly shown (not `Сохранено`, not a blank indicator). |
| Status | Not run |

### TC-05-EXT-3.3 — Out-of-order autosave responses reflect the latest edit

| Field | Value |
|---|---|
| Description | Autosave fires often, so overlapping requests are routine; trusting the last response to arrive shows a stale status over a newer edit. |
| Preconditions | Document A1 is open; two autosave responses can be released in a controlled order. |
| Test data | Autosave 1 content `<p>Правка А</p>`; autosave 2 content `<p>Правка Б</p>`; release order: 2's response, then 1's |
| Steps | 1. Trigger autosave 1 and hold its response.<br>2. Edit further and trigger autosave 2.<br>3. Release autosave 2's response, then autosave 1's. |
| Expected result | After both responses resolve, the shown save status corresponds to autosave 2 (`Правка Б`) — the older response does not overwrite it; the editor content is still `Правка Б`. |
| Status | Not run |

### TC-05-EXT-3.4 — A stale autosave is rejected, not a silent overwrite

| Field | Value |
|---|---|
| Description | With autosave running unattended, a second session's edit would be steamrolled on the next debounce tick unless the version guard rejects the stale write and the client reconciles. |
| Preconditions | Document A1 is open in session 1 holding `version` `2`; session 2 has saved the document, advancing it to `version` `3`. |
| Test data | Session 1 autosave body `{"content": "<p>Из первой сессии</p>", "version": 2}`; session 2's stored content `<p>Из второй сессии</p>` |
| Steps | 1. Let session 1's autosave fire with the now-stale `version` `2`.<br>2. Read the response.<br>3. `GET /api/v1/documents/{A1}` and inspect the stored content.<br>4. Observe session 1's UI. |
| Expected result | Step 2 answers `409 Conflict` with `{"error_code": "VERSION_CONFLICT", "message": "The document was modified by another save. Refetch and retry."}`; step 3 shows `<p>Из второй сессии</p>` at `version` `3` — session 2's edit intact; session 1 surfaces the conflict and reconciles (refetch/merge prompt) rather than silently retrying with the stale version. |
| Status | Not run |

## 4. Document Title

### TC-05-EXT-4.1 — A title can be set and round-trips

| Field | Value |
|---|---|
| Description | The title feeds the export filename (story 17); a title that does not persist gives every export the default `document.pdf` name. |
| Preconditions | Document A1 is open in the editor with no title set (`title` is `null`). |
| Test data | Title `Отчёт по практике`; save body `{"content": "<p>Текст</p>", "title": "Отчёт по практике", "version": 2}` |
| Steps | 1. Type the title into the editor's title field.<br>2. Save the document.<br>3. Reload and re-open document A1. |
| Expected result | Save answers `200 OK`; the response and the subsequent `GET` both carry `title` `Отчёт по практике`; on reload the title field shows exactly that string. |
| Status | Not run |

### TC-05-EXT-4.2 — An over-length title is rejected at the boundary

| Field | Value |
|---|---|
| Description | Silently truncating a title renames the user's export without telling them; the boundary must reject as a whole, and must not reject a legitimate title of exactly the limit. |
| Preconditions | Document A1 is open in the editor. |
| Test data | Title of exactly 200 code points, then of exactly 201 code points (both Cyrillic), measured NFC-normalized after trimming |
| Steps | 1. Save with the 200-code-point title.<br>2. Save with the 201-code-point title.<br>3. `GET /api/v1/documents/{A1}` and read the stored `title`. |
| Expected result | Step 1 answers `200 OK` and stores all 200 code points; step 2 is refused with a `4xx` carrying the `{"error_code", "message"}` shape; step 3 shows the stored title is still the 200-code-point value — the 201-code-point one was never truncated to 200 and stored. |
| Status | Not run |

### TC-05-EXT-4.3 — Markup in the title is neutralized

| Field | Value |
|---|---|
| Description | The title reaches the editor HTML, the PDF/DOCX header XML, the `Content-Disposition` filename and the logs. Any markup or control character surviving into storage becomes an injection at one of those four sinks. |
| Preconditions | Document A1 is open in the editor. |
| Test data | Title `Отчёт<script>alert(1)</script>\r\nX-Injected: 1` (with literal CR and LF characters) |
| Steps | 1. Save document A1 with that title.<br>2. `GET /api/v1/documents/{A1}` and read the raw stored `title`.<br>3. Render the title in the editor and inspect the response headers of an export of A1. |
| Expected result | The stored `title` contains no `<script` substring and no raw CR or LF — markup is stripped and control characters removed or escaped; step 3 shows no script executes in the editor and no `X-Injected` header appears in the export response. |
| Status | Not run |

## 5. Paste Sanitize

### TC-05-EXT-5.1 — Pasted rich content is sanitized before entering the document

| Field | Value |
|---|---|
| Description | Pasting from a web page carries the source's markup wholesale; without a paste filter the payload lands in the document model and is saved as legitimate content. |
| Preconditions | Document A1 is open in the editor; the clipboard holds the rich-HTML fixture below. |
| Test data | Clipboard HTML `<p>Вставленный текст</p><script>alert(1)</script><div onclick="steal()">Блок</div><a href="javascript:alert(1)">ссылка</a>` |
| Steps | 1. Paste the clipboard content into the editor.<br>2. Read the editor's `getHTML()` immediately, before any save. |
| Expected result | `Вставленный текст` is present; the document model contains no `<script` element, no `onclick` (or any `on*`) attribute and no `javascript:` href — all three are removed at paste time, not merely at save time. |
| Status | Not run |

### TC-05-EXT-5.2 — The server re-sanitizes on save regardless of the client

| Field | Value |
|---|---|
| Description | The paste filter is a convenience; the server is the boundary. An attacker calls `PUT` directly and never runs the editor at all. |
| Preconditions | Document A1 exists at a known version; the request is issued with an HTTP client, bypassing the editor entirely. |
| Test data | Body `{"content": "<p>Текст</p><script>alert(1)</script><img src=x onerror=alert(1)>", "version": 2}` |
| Steps | 1. `PUT /api/v1/documents/{A1}` with that body.<br>2. `GET /api/v1/documents/{A1}` and read the raw `content`. |
| Expected result | `200 OK`; the stored and returned `content` contains no `<script` substring and no `onerror` attribute — sanitized server-side before persist; `<p>Текст</p>` survives. |
| Status | Not run |

## 6. Undo / Redo

### TC-05-EXT-6.1 — Undo and redo restore block structure

| Field | Value |
|---|---|
| Description | A history stack that records only text transactions restores the characters but not the heading or list nodes, so redo returns a plain paragraph where a structured block was. |
| Preconditions | Document A1 is open with the text `Раздел` and `Пункт` typed as plain paragraphs. |
| Test data | Apply an H3 to `Раздел`, then a bulleted list to `Пункт`; controls: the undo and redo toolbar buttons |
| Steps | 1. Apply the H3 heading, then the bulleted list.<br>2. Click undo twice.<br>3. Click redo twice.<br>4. Inspect the content. |
| Expected result | After step 2 both blocks are back to plain paragraphs; after step 3 the content again contains `<h3>Раздел</h3>` and `<ul><li>Пункт</li></ul>` — the block nodes themselves are restored, not just the inline text. |
| Status | Not run |

## 7. Word / Character Count

### TC-05-EXT-7.1 — The count reflects content in grapheme clusters

| Field | Value |
|---|---|
| Description | Counting UTF-16 code units reports an emoji as 2 and a combining accent as 2 — the user sees a character count that does not match what they can see on screen. |
| Preconditions | Document A1 is open in the editor with the count indicator visible. |
| Test data | Content `é🎓` where `é` is `e` + U+0301 (2 code points) and `🎓` is U+1F393 (1 code point, 2 UTF-16 units) — 2 graphemes total |
| Steps | 1. Enter that content and read the character count.<br>2. Type one further character and read the count again. |
| Expected result | Step 1 reports `2` characters — each of `é` and `🎓` counted once, not 2 or 4 in total; step 2 reports `3` immediately, without requiring a save or a blur. |
| Status | Not run |

## 8. Tables

### TC-05-EXT-8.1 — A table can be inserted and round-trips

| Field | Value |
|---|---|
| Description | A table is the deepest nesting the schema carries; a serializer missing one level returns the cell text as loose paragraphs and the grid is gone. |
| Preconditions | Document A1 is open in the upgraded editor. |
| Test data | A 2×2 table with cells `Показатель`, `Значение`, `Объём`, `120` |
| Steps | 1. Insert a 2×2 table and fill the four cells with that text.<br>2. Save the document.<br>3. Reload and re-open document A1. |
| Expected result | On reload the content contains a `<table>` with two rows of two cells each, carrying `Показатель`, `Значение`, `Объём`, `120` in their original positions; the table is not flattened to paragraphs and no cell text is lost. |
| Status | Not run |
