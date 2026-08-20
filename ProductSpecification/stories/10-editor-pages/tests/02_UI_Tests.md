> **Implementation Order**: sequential TDD — measuring state → sheet display → counter →
> manual break → settings panel → validation feedback → failure handling → navigation.

# Editor pages — UI Tests

Screen: the document editor at `/documents/{id}`, its page-setup panel and its page rail.
Backing contract: `PUT /api/v1/documents/{id}` with `page_settings`.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.pages@textery.test` / `Qa!Pages2026` |
| Document A1 (unconfigured, 1 page) | id `9d4b1e7a-3c62-4f08-b5d1-8e2a70c4f159`, title `Курсовая работа`, `page_settings` `null` |
| Document A2 (configured) | id `c31f8a05-6d47-4b92-8e10-2f5c9d7b3a64`, settings `S1` |
| Document A8 (3 pages, generated) | id `3b7e60f4-2c19-4d5a-91b8-cf40a2e75d16`, `volume_pages` requested `5`, laid out to `3` |
| Settings `S1` | A5, landscape, margins 35/15/25/40 mm, `font_size_pt` 11, `line_height` 1.15, header `Кафедра ИВТ`, footer `Текстери`, numbering on, first page skipped `false` |
| Default preset | A4, portrait, margins 20/15/20/30 mm, 14 pt, line height 1.5, numbering on, first page skipped `true` |
| Document font | bundled Liberation Serif webfont, readiness via `document.fonts.ready` |
| Counter text | `стр. N из M` in the editor status bar |
| Volume comparison text | `запрошено 5 стр.` next to the counter |
| Measuring state text | `Расчёт страниц…` on a skeleton sheet |
| Font-timeout text | `Не удалось загрузить шрифт документа` with a `Повторить` action |
| Save-failure banner | `Не удалось сохранить параметры страницы` with a `Повторить` action |
| Dirty-navigation guard | the browser's native `beforeunload` confirmation |

## 1. Pre-layout State

### TC-10-UI-1.1 — Pagination waits for the document font

| Field | Value |
|---|---|
| Description | Measuring against a fallback face produces a page count that changes under the user a moment later; the layout must not start before the real metrics exist. |
| Preconditions | Account A signed in; the webfont response for Liberation Serif is stalled by the test harness so `document.fonts.ready` has not resolved. |
| Test data | Document A8 (3 pages); font request held open for the duration of the assertion |
| Steps | 1. Open `/documents/3b7e60f4-2c19-4d5a-91b8-cf40a2e75d16`.<br>2. Read the editor canvas and the status bar while the font is still stalled. |
| Expected result | The measuring state is shown: the skeleton sheet with the text `Расчёт страниц…`; the status bar shows no `стр. N из M` counter at all; no error banner and no empty-document placeholder is present — the three states are visually distinct DOM nodes. |
| Status | Not run |

### TC-10-UI-1.2 — The page count appears only once the font has resolved

| Field | Value |
|---|---|
| Description | A count that first appears and then silently corrects itself is the symptom of measuring twice, once on the wrong face. |
| Preconditions | Document A8 open with the font request still stalled (as in TC-10-UI-1.1). |
| Test data | Document A8, expected final count `стр. 1 из 3` |
| Steps | 1. Open document A8 with the font stalled.<br>2. Release the font response.<br>3. Record the status-bar text every 100 ms for 3 s after the sheets appear. |
| Expected result | After step 2 the sheets are laid out and the status bar shows `стр. 1 из 3`; the recorded values in step 3 are all `стр. 1 из 3` — the total never changes on its own after the first render, and no intermediate count was shown before the font resolved. |
| Status | Not run |

### TC-10-UI-1.3 — A font that never loads reaches a defined outcome, not a permanent spinner

| Field | Value |
|---|---|
| Description | Without a finite deadline the measuring state is indistinguishable from a hung editor, and the user has nothing to act on. |
| Preconditions | Document A8 open; the webfont request is failed by the harness (never resolves). |
| Test data | Font load deadline `5 s`; expected outcome text `Не удалось загрузить шрифт документа` |
| Steps | 1. Open document A8 with the font request never resolving.<br>2. Wait until the load deadline has passed.<br>3. Read the editor canvas. |
| Expected result | Within 1 s of the deadline the `Расчёт страниц…` skeleton is replaced by the named state `Не удалось загрузить шрифт документа` with a `Повторить` control; the measuring state is gone; the editor is not left spinning indefinitely. |
| Status | Not run |

---

## 2. Sheet Display

### TC-10-UI-2.1 — Content is laid out on discrete sheets

| Field | Value |
|---|---|
| Description | The whole story is that the editor stops being an endless scroll — sheets with gaps, and a block that does not fit continuing rather than being clipped. |
| Preconditions | Account A signed in; document A8 is longer than one page at the default preset. |
| Test data | Document A8 (3 pages); sheet element selector `[data-testid="page-sheet"]`; expected gap ≥ 16 px |
| Steps | 1. Open `/documents/3b7e60f4-2c19-4d5a-91b8-cf40a2e75d16` and wait for the counter.<br>2. Count the sheet elements and measure the vertical distance between consecutive sheet boxes.<br>3. Find the paragraph that spans the page-1/page-2 boundary and read its text on both sheets. |
| Expected result | 3 sheet elements are present; the gap between consecutive sheets is ≥ 16 px of page background, visible between them; the spanning paragraph's text is continued on sheet 2 with no characters lost or duplicated at the boundary. |
| Status | Not run |

### TC-10-UI-2.2 — The first page carries no number by default, later pages do

| Field | Value |
|---|---|
| Description | The default preset is ГОСТ behaviour: the title page counts as page 1 but prints no folio. Numbering every page from 1 is the plausible wrong default. |
| Preconditions | Document A8 open with `page_settings` `null` (default preset: numbering on, first page skipped). |
| Test data | Document A8, 3 pages; folio element selector `[data-testid="page-folio"]` |
| Steps | 1. Open document A8 and wait for the layout.<br>2. Read the folio element of each of the three sheets. |
| Expected result | Sheet 1 has no folio element at all; sheet 2 shows `2` and sheet 3 shows `3` — the numbering counts the first page rather than restarting at 1 on sheet 2. |
| Status | Not run |

### TC-10-UI-2.3 — An empty document shows one blank sheet

| Field | Value |
|---|---|
| Description | An empty document is a legitimate state, not a loading state — a spinner or an empty-state illustration here tells the user something is wrong when nothing is. |
| Preconditions | Document A9 exists, owned by account A, with `content` `""`. |
| Test data | Document A9 id `8c2f45b1-e930-4a76-bd58-71c0e6493af2` |
| Steps | 1. Open `/documents/8c2f45b1-e930-4a76-bd58-71c0e6493af2`.<br>2. Count the sheet elements, read the status bar, and search the canvas for a spinner or placeholder. |
| Expected result | Exactly one sheet element, empty of content; the status bar reads `стр. 1 из 1`; no `Расчёт страниц…` skeleton, no spinner element and no empty-state placeholder text is present. |
| Status | Not run |

---

## 3. Page Counter

### TC-10-UI-3.1 — The counter follows the caret and updates as the user types

| Field | Value |
|---|---|
| Description | A counter fixed to the scroll position or computed once at load stops telling the truth the moment the user edits. |
| Preconditions | Document A8 open, laid out to 3 pages, font resolved. |
| Test data | Caret placed in the first paragraph of sheet 3; then 40 paragraphs of `Дополнительный текст.` typed at the end |
| Steps | 1. Open document A8 and read the counter.<br>2. Click into the first paragraph of sheet 3 and read the counter.<br>3. Type enough content at the end of the document to add a page and read the counter again. |
| Expected result | Step 1: `стр. 1 из 3`. Step 2: `стр. 3 из 3` — the current page follows the caret, not the scroll. Step 3: the total rises to `4` (`стр. 4 из 4`) within the incremental-recompute budget of 150 ms after typing stops. |
| Status | Not run |

### TC-10-UI-3.2 — A shortfall against the requested volume is shown

| Field | Value |
|---|---|
| Description | The user asked for 5 pages and got 3; that has to be visible. Offering a "generate more" control here would silently spend a generation the user did not ask for. |
| Preconditions | Document A8 came from a generation with `volume_pages = 5` and lays out to 3 pages. |
| Test data | Document A8, requested `5`, actual `3` |
| Steps | 1. Open document A8 and wait for the layout.<br>2. Read the status bar in full.<br>3. Enumerate every control in the status bar and the page rail. |
| Expected result | The status bar shows `стр. 1 из 3` together with `запрошено 5 стр.`, naming both numbers; no control labelled `Дописать`, `Сгенерировать ещё` or equivalent exists anywhere in the status bar or rail, and no generation request is issued. |
| Status | Not run |

---

## 4. Manual Page Break

### TC-10-UI-4.1 — An inserted break starts a new sheet

| Field | Value |
|---|---|
| Description | The break is only useful if it is both effective and visible — an invisible break is content the user cannot find again to delete. |
| Preconditions | Document A8 open; caret placed in the middle of the second paragraph on sheet 1. |
| Test data | Insertion via `Ctrl+Enter`; break marker selector `[data-testid="page-break-marker"]` |
| Steps | 1. Place the caret between the two sentences of paragraph 2 on sheet 1.<br>2. Press `Ctrl+Enter`.<br>3. Read the sheets and the marker. |
| Expected result | The text that followed the caret now begins sheet 2, not sheet 1; a break marker element is rendered at the insertion point on sheet 1; the total in the counter increases by 1. |
| Status | Not run |

### TC-10-UI-4.2 — Editing above a break re-flows the pages without moving the break

| Field | Value |
|---|---|
| Description | If the break is attached to a page index rather than to its position in the content, an edit above it silently moves it and cuts the document in the wrong place. |
| Preconditions | Document A10 exists with a manual break between the paragraph `До разрыва.` and the paragraph `После разрыва.`. |
| Test data | Document A10 id `1a5cd4e8-9b37-4c60-8f22-e07b6d1934ca`; inserted paragraph `Новый абзац сверху.` |
| Steps | 1. Open document A10 and record which content precedes and follows the break.<br>2. Place the caret above the break and type `Новый абзац сверху.` enough times to push the content past a page boundary.<br>3. Re-read the content on each side of the break. |
| Expected result | The sheets before the break re-flow (their page count changes); the break still has `До разрыва.` immediately before it and `После разрыва.` immediately after it — the same content pair as in step 1. |
| Status | Not run |

### TC-10-UI-4.3 — A break can be selected and deleted

| Field | Value |
|---|---|
| Description | A break the user can insert but not remove is a one-way change to their document. |
| Preconditions | Document A10 open with one manual break. |
| Test data | Document A10; the break marker, then the `Delete` key |
| Steps | 1. Click the break marker to select it.<br>2. Press `Delete`.<br>3. Read the sheets and the counter. |
| Expected result | The marker is removed from the content; `После разрыва.` now flows on the same sheet as `До разрыва.` (or on the next sheet only if it no longer fits); the counter total decreases by 1; no break marker element remains in the DOM. |
| Status | Not run |

---

## 5. Page Setup Panel

### TC-10-UI-5.1 — The panel opens with the document's effective settings

| Field | Value |
|---|---|
| Description | A panel that always opens on the preset silently offers to overwrite the user's saved geometry the moment they press apply. |
| Preconditions | Document A2 has settings `S1` saved; document A1 has `page_settings` `null`. |
| Test data | `S1` (A5 / landscape / 35,15,25,40 / 11 pt / 1.15 / `Кафедра ИВТ` / `Текстери` / numbering on / skip-first off) and the default preset |
| Steps | 1. Open document A2 and open the page setup panel (`Параметры страницы`).<br>2. Read every field value.<br>3. Open document A1 and open the panel.<br>4. Read every field value. |
| Expected result | Step 2 shows `A5`, `Альбомная`, margins `35` / `15` / `25` / `40`, `11`, `1.15`, header `Кафедра ИВТ`, footer `Текстери`, numbering checked, skip-first unchecked. Step 4 shows `A4`, `Книжная`, margins `20` / `15` / `20` / `30`, `14`, `1.5`, empty header, empty footer, numbering checked, skip-first checked. |
| Status | Not run |

### TC-10-UI-5.2 — Applying a change re-paginates the document

| Field | Value |
|---|---|
| Description | The layout must follow the authoritative save, not the local form value — otherwise the sheets show a geometry the server may not hold. |
| Preconditions | Document A8 open at the default preset, laid out to 3 pages, panel open. |
| Test data | Change `page_size` from `A4` to `A5`; expected new count 5 pages |
| Steps | 1. Set the sheet size to `A5` in the panel and press `Применить`.<br>2. Wait for the save to complete.<br>3. Measure a sheet's rendered box and read the counter. |
| Expected result | The `PUT /api/v1/documents/3b7e60f4-2c19-4d5a-91b8-cf40a2e75d16` answers `200 OK`; the sheet box is redrawn at A5 portrait proportions (148 × 210 mm, within 1 px of the CSS-px equivalent); the counter total changes from `3` to `5`. |
| Status | Not run |

---

## 6. Validation Feedback

### TC-10-UI-6.1 — A rejected value is reported inline against its own field

| Field | Value |
|---|---|
| Description | A generic banner leaves the user hunting for the offending field, and a silent correction leaves them with a geometry they never chose. |
| Preconditions | Document A8 open, page setup panel open, sheet size `A4` portrait. |
| Test data | Margins `top 140`, `right 15`, `bottom 150`, `left 30` — a vertical sum of 290 mm on a 297 mm sheet, leaving under one line |
| Steps | 1. Enter those margins in the panel and press `Применить`.<br>2. Read the error rendered next to the margin fields.<br>3. Re-read the values in the margin inputs. |
| Expected result | The `PUT` answers `422`; an inline error is attached to the top and bottom margin inputs (not a page-level banner) and names the cause — that the remaining content area is too small for one line of text — rather than saying only `Некорректное значение`; the inputs still contain `140` and `150` exactly as typed, with no value replaced by a fitting one. |
| Status | Not run |

### TC-10-UI-6.2 — An over-length header is refused rather than trimmed

| Field | Value |
|---|---|
| Description | Trimming the field under the user's cursor loses text they typed and hides the fact that a limit exists. |
| Preconditions | Document A8 open, page setup panel open. |
| Test data | `header_text` = `Ё` × 201 (one over the 200-code-point limit) |
| Steps | 1. Paste the 201-character header into the header field and press `Применить`.<br>2. Read the error rendered next to the header field.<br>3. Read the header field's value length. |
| Expected result | The `PUT` answers `422`; an inline error is attached to the header field naming the 200-character limit; the field still holds all 201 characters — the UI did not truncate it to 200 and did not clear it. |
| Status | Not run |

---

## 7. Failure Handling

### TC-10-UI-7.1 — A failed save is shown differently from a rejected value

| Field | Value |
|---|---|
| Description | A network failure is retryable and a validation failure is not; showing them the same way sends the user to edit values that were never the problem. |
| Preconditions | Document A8 open, panel open with valid values entered; the save request is stubbed to fail with a network error, then with `503`. |
| Test data | Entered values: `A5`, margins 25/20/25/20, 12 pt, 1.2, header `Кафедра ИВТ`; stubbed network error and `503` |
| Steps | 1. Press `Применить` with the save request failing at the network layer.<br>2. Read the panel: the banner, any inline field errors, and every field value.<br>3. Repeat with the request stubbed to `503`. |
| Expected result | A page-level failure banner `Не удалось сохранить параметры страницы` with a `Повторить` action is shown in both runs; no inline field error appears on any input; all entered values (`A5`, `25`, `20`, `25`, `20`, `12`, `1.2`, `Кафедра ИВТ`) are still present and unchanged. |
| Status | Not run |

### TC-10-UI-7.2 — A rejected geometry rolls the layout back

| Field | Value |
|---|---|
| Description | Optimistic repagination that is not rolled back leaves the editor rendering a geometry the server refused — an inline error next to sheets already redrawn is worse than no optimism at all. |
| Preconditions | Document A8 open at settings `S1`, laid out; the save request is stubbed to `422`. |
| Test data | Applied change `font_size_pt: 500`; pre-change layout: A5 landscape, 11 pt, counter total recorded before the attempt |
| Steps | 1. Record the sheet box dimensions and the counter total.<br>2. Enter `500` in the font size field and press `Применить`.<br>3. After the `422` arrives, re-measure the sheet box and re-read the counter. |
| Expected result | The sheet box and the counter total in step 3 equal exactly the values recorded in step 1; no sheet is rendered at the 500 pt geometry after the response; the inline error is present in addition to, not instead of, the rollback. |
| Status | Not run |

### TC-10-UI-7.3 — A late response never replaces newer state

| Field | Value |
|---|---|
| Description | Last-response-wins instead of last-request-wins makes the editor snap back to an older document with no user action and no error. |
| Preconditions | Document A8 open; the harness can delay individual responses. |
| Test data | Request 1: content save with `<p>Правка 1.</p>` (response delayed 3 s). Request 2: page-settings save setting `A5`, issued 200 ms later (responds immediately). |
| Steps | 1. Issue the content save (delayed).<br>2. Issue the page-settings save.<br>3. Let request 2's response arrive, then request 1's.<br>4. Read the sheet geometry and the editor content. |
| Expected result | After the late response arrives the sheets are still laid out at `A5` (request 2's result); the editor does not revert to the A4 geometry carried in request 1's stale response; the content shows `Правка 1.`, which both responses agree on. |
| Status | Not run |

### TC-10-UI-7.4 — An in-flight action cannot be triggered twice

| Field | Value |
|---|---|
| Description | A second export is a second full render; a second settings save races its own predecessor into a version conflict the user never caused. |
| Preconditions | Document A8 open; the save and the export requests are each stubbed to take 3 s. |
| Test data | Controls `Применить` in the page setup panel and `Экспорт` in the toolbar; each clicked 3 times within 500 ms |
| Steps | 1. Click `Применить` three times in quick succession and count the outgoing `PUT` requests.<br>2. Click `Экспорт` three times in quick succession and count the outgoing export requests. |
| Expected result | Exactly one `PUT /api/v1/documents/{id}` and exactly one `GET /api/v1/documents/{id}/export` are issued; the control is disabled (`aria-disabled` / `disabled`) for the duration of its request and re-enabled when the response arrives. |
| Status | Not run |

### TC-10-UI-7.5 — Unsaved panel edits are guarded against leaving

| Field | Value |
|---|---|
| Description | Header text typed and not applied lives only in the panel; navigating away without a warning discards it with no trace. |
| Preconditions | Document A8 open, page setup panel open, nothing applied yet. |
| Test data | Header field typed as `Кафедра ИВТ`, apply NOT pressed |
| Steps | 1. Type `Кафедра ИВТ` into the header field.<br>2. Trigger a page reload / navigation away.<br>3. Observe the browser prompt. |
| Expected result | The `beforeunload` confirmation fires and the navigation is blocked until the user confirms; cancelling it leaves the panel open with `Кафедра ИВТ` still in the field. |
| Status | Not run |

---

## 8. Navigation

### TC-10-UI-8.1 — Selecting a page in the rail scrolls to it

| Field | Value |
|---|---|
| Description | The rail's only job is navigation; a rail entry that does not move the viewport is decoration. |
| Preconditions | Document A8 open, laid out to 3 pages, viewport at the top. |
| Test data | Rail entry for page 3; rail selector `[data-testid="page-rail-item-3"]` |
| Steps | 1. Click the rail entry for page 3.<br>2. Read the scroll position and which sheet is in view.<br>3. Read the rail's current-page marking and the status bar. |
| Expected result | Sheet 3 is scrolled into view; the rail entry for page 3 carries the current state (`aria-current="page"`); the status bar reads `стр. 3 из 3`. |
| Status | Not run |

### TC-10-UI-8.2 — The page rail offers no way to create a page

| Field | Value |
|---|---|
| Description | Pages are derived from content and geometry — an "add page" control would promise a document state the model cannot hold. |
| Preconditions | Document A8 open, page rail visible. |
| Test data | Every interactive element in the rail, by accessible name |
| Steps | 1. Open document A8.<br>2. Enumerate every button, menu item and control in the page rail and read its accessible name. |
| Expected result | The only page-creating action offered is inserting a break (`Разрыв страницы`); no control named `Добавить страницу`, `Новая страница` or `Удалить страницу` exists in the rail or its context menus. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the measuring state` | Skeleton sheet + rail skeletons with `Расчёт страниц…`, no page count in the status bar |
| `the document font` | The bundled Liberation Serif webfont; readiness via `document.fonts` |
| `a defined outcome` | Named error/degraded state — not an indefinite spinner |
| `the page rail` | Left column listing pages (desktop) / chip strip (mobile) |
| `inserts a page break` | Ctrl+Enter or the toolbar/rail break action |
| `applies` | The panel's `Применить` control, issuing `PUT /api/v1/documents/{id}` |
| `the save cannot reach the server` | Stubbed network failure / 5xx on the save request |
| `the server rejects` | Stubbed 422 on the save request |
| `attempt to leave the page` | Reload / navigate away, triggering the dirty-state guard |
