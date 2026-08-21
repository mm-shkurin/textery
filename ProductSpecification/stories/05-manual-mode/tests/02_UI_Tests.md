# Manual input mode (non-AI document creation) — UI Tests

> **Implementation Order**: Tests are numbered for sequential TDD implementation.
> Start with mode-modal display (reused component, small change), then the empty editor
> display, then formatting interaction, then save submission, then save feedback, then
> navigation.

No prerequisite blocker screens apply to this story — there is no parent resource that
must exist before the flow can start. The type-select modal is reused unchanged from
story #1 and is not retested here.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the visitor) | `qa.manual@textery.test` / `Qa!Manual2026` |
| Document A1 | id `3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3`, `document_type` `реферат`, `content` `""`, `version` `1` |
| Editor route | `/documents/3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3` |
| Save request | `PUT /api/v1/documents/{document_id}` with `{"content": …, "version": …}` |
| Mockups | `mockups/02-mode-modal.html`, `03-editor-empty.html`, `05-editor-saved.html`, `06-editor-error.html` |
| Visible strings | `Ручной режим`, `Автоматический режим`, `Сохранить`, `Сохранено`, `Назад` |

---

## 1. Mode Modal

### TC-05-UI-1.1 — The mode modal now shows both modes as available

| Field | Value |
|---|---|
| Description | The manual card shipped disabled with a "скоро" badge. Leaving either behind makes the whole story unreachable from the UI even after the backend lands. |
| Preconditions | Account A signed in; the document-type modal is open and a type (`реферат`) has been chosen, so the mode modal is showing. |
| Test data | Screen: mode modal (`mockups/02-mode-modal.html`); controls: the two `.mode-card` elements |
| Steps | 1. Open the mode modal via the document-type modal.<br>2. Inspect both `.mode-card` elements' classes and text.<br>3. Hover and click-target each card. |
| Expected result | Two cards are shown, reading `Ручной режим` and `Автоматический режим`; neither carries the `disabled` class nor a `soon-pill`/"скоро" badge; the text `скоро` appears nowhere in the modal; both cards are clickable and selectable. |
| Status | Not run |

### TC-05-UI-1.2 — Selecting Ручной режим opens the empty editor

| Field | Value |
|---|---|
| Description | The mode choice must both dismiss the modal and carry the chosen document type through — a modal left open over the editor, or a type lost in transit, breaks the flow's only entry point. |
| Preconditions | The mode modal is open with document type `реферат` chosen. |
| Test data | Control: the `Ручной режим` card; expected route `/documents/{document_id}` for the newly created document |
| Steps | 1. Click the `Ручной режим` card.<br>2. Observe the modal.<br>3. Observe the page that renders. |
| Expected result | The mode modal is removed from the DOM; the browser is on the editor route for the newly created `document_id`; the editor's content area is empty; the chosen type `реферат` is still displayed in the breadcrumb. |
| Status | Not run |

---

## 2. Empty Editor — Page Display

### TC-05-UI-2.1 — A freshly created document shows an empty, ready-to-type editor

| Field | Value |
|---|---|
| Description | An empty document must look ready, not loading. A skeleton here reads as "still fetching" and the user waits for content that will never arrive. |
| Preconditions | Account A has just created document A1 via the mode modal; it has never been saved. |
| Test data | Editor route `/documents/3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3`; toolbar per `mockups/03-editor-empty.html`; breadcrumb text `реферат` / `Ручной режим` |
| Steps | 1. Land on the editor for document A1.<br>2. Inspect the content area.<br>3. Inspect the formatting toolbar.<br>4. Read the breadcrumb. |
| Expected result | The contenteditable region is empty and shows placeholder text — no spinner and no loading skeleton element; the toolbar is visible carrying heading (H3), bold and italic controls, and offers no H1/H2, paragraph or list control (the inline-only schema has no block nodes — see `functionality.md`); the breadcrumb reads the chosen document type and `Ручной режим`. |
| Status | Not run |

---

## 3. Formatting Interaction

### TC-05-UI-3.1 — Applying a format changes the content and highlights the active toolbar button

| Field | Value |
|---|---|
| Description | Formatting that applies but does not light up the button leaves the user unable to tell whether the mark took — they re-click and toggle it back off. |
| Preconditions | The editor is open with the text `Пример текста` typed in it. |
| Test data | Selection: the word `Пример`; control: the bold toolbar button (or `Ctrl+B`); active class `.toolbar-btn.active` |
| Steps | 1. Select the word `Пример`.<br>2. Click the bold toolbar button.<br>3. Leave the cursor inside the now-bold word and inspect the toolbar. |
| Expected result | `Пример` renders bold (wrapped in a `<b>`/`<strong>` mark in the content); the bold toolbar button carries the `active` class while the cursor remains within the bold text. |
| Status | Not run |

### TC-05-UI-3.2 — The toolbar reflects formatting state at the cursor position, not globally

| Field | Value |
|---|---|
| Description | A toolbar that latches on "the document contains bold somewhere" instead of "the cursor is inside bold" reports the wrong state everywhere else in the document. |
| Preconditions | The editor contains `Жирный обычный` where `Жирный` is bold and ` обычный` is not. |
| Test data | Cursor positions: inside `Жирный`, then inside `обычный`; controls: every toolbar button |
| Steps | 1. Place the cursor inside `Жирный` and note the bold button state.<br>2. Move the cursor into `обычный` by click or arrow key.<br>3. Inspect every toolbar button. |
| Expected result | After step 2 the bold button no longer carries `active`; no other formatting button carries `active` either — italic and H3 are inactive, since the cursor sits in unformatted text. |
| Status | Not run |

### TC-05-UI-3.3 — Pressing Enter inserts a line break and the text spans multiple lines

| Field | Value |
|---|---|
| Description | The inline-only document has no paragraph to split, so Enter must emit a hardBreak. A trailing one at document end would grow the save payload with a stray `<br>` on every keystroke session. |
| Preconditions | The editor is open with `Первая строка` typed in it. |
| Test data | Keystroke: `Enter`; second line `Вторая строка`; expected saved content `Первая строка<br>Вторая строка` |
| Steps | 1. Place the cursor at the end of `Первая строка` and press `Enter`.<br>2. Type `Вторая строка`.<br>3. Read the editor's `getHTML()` save payload. |
| Expected result | The two lines render on separate visual lines; the payload is exactly `Первая строка<br>Вторая строка` — a single `<br>` between them; no `<br>` follows `Вторая строка` at document end. |
| Status | Not run |

> Design: `decisions/line-break-in-inline-doc-decision.md` (A′ — hardBreak +
> strip-trailing-hardBreak). The inline* document has no paragraph to split on, so the
> break is a hardBreak `<br>`; a trailing one at document end is stripped so `getHTML()`
> (the save payload) never grows a stray `<br>`.

---

## 4. Save Submission

### TC-05-UI-4.1 — Saving shows a loading state and disables the save control

| Field | Value |
|---|---|
| Description | Without an in-flight lock, an impatient double-click fires two `PUT`s with the same version — the second gets a `409` and the user sees a conflict error on their own single edit. |
| Preconditions | The editor is open on document A1 with typed and formatted content; the save request is held open (throttled or stubbed) so the in-flight window is observable. |
| Test data | Control: the `Сохранить` button; request `PUT /api/v1/documents/3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3` |
| Steps | 1. Click `Сохранить`.<br>2. While the request is in flight, inspect the button.<br>3. Click `Сохранить` a second time.<br>4. Count the `PUT` requests issued. |
| Expected result | During flight the button shows a spinner/loading state and carries the `disabled` attribute; exactly one `PUT /api/v1/documents/{A1}` is issued — the second click fires no request. |
| Status | Not run |

### TC-05-UI-4.2 — A save completing out of order still reflects the latest edit, not a stale response

| Field | Value |
|---|---|
| Description | Responses are not guaranteed to arrive in send order. A UI that trusts the last response to arrive shows the older save's status, telling the user their newest edit is saved when it may not be. |
| Preconditions | The editor is open on document A1; two save responses can be released in a controlled order. |
| Test data | Save 1 content `<p>Первая правка</p>`; save 2 content `<p>Вторая правка</p>`; release order: save 2's response first, then save 1's |
| Steps | 1. Trigger save 1 and hold its response.<br>2. Keep editing and trigger save 2.<br>3. Release save 2's response.<br>4. Release save 1's (older) response.<br>5. Read the displayed save status. |
| Expected result | After step 3 the status reflects save 2; after step 4 it still reflects save 2 — the stale save-1 response does not overwrite it. The UI tracks requests by a monotonic client-side sequence and discards a response older than the newest resolved one. |
| Status | Not run |

---

## 5. Save Feedback

### TC-05-UI-5.1 — A successful save shows a lightweight confirmation, no full-page transition

| Field | Value |
|---|---|
| Description | A route change on save would throw the user out of the editor mid-writing and drop their cursor position. |
| Preconditions | The editor is open on document A1 with valid content; the backend returns `200 OK`. |
| Test data | Control: `Сохранить`; expected visible text `Сохранено` per `mockups/05-editor-saved.html`; the editor URL before the click |
| Steps | 1. Note the current URL.<br>2. Click `Сохранить`.<br>3. Wait for the save to complete.<br>4. Compare the URL and inspect the page. |
| Expected result | The text `Сохранено` appears inline in the editor chrome; the URL is unchanged and no navigation occurred; the editor content and cursor remain as they were. |
| Status | Not run |

### TC-05-UI-5.2 — A failed save shows an inline error and keeps the content in the editor

| Field | Value |
|---|---|
| Description | Clearing the editor on a failed save destroys exactly the text the user could not persist — the one copy that still exists. |
| Preconditions | The editor is open on document A1 with the content `<p>Важный текст</p>` typed; the save endpoint is stubbed to fail (`500` with `{"error_code": "INTERNAL_ERROR", …}`). |
| Test data | Control: `Сохранить`; error banner per `mockups/06-editor-error.html` |
| Steps | 1. Click `Сохранить`.<br>2. Wait for the failure response.<br>3. Inspect the page and the editor content area. |
| Expected result | An inline error banner is shown in the editor (not a full-page error, not a silent no-op); the content area still contains `Важный текст` exactly as typed; the `Сохранить` button is re-enabled so the save can be retried. |
| Status | Not run |

---

## 6. Navigation

### TC-05-UI-6.1 — "Назад" from the editor returns to the mode modal

| Field | Value |
|---|---|
| Description | Going back must land on the mode modal with the type still chosen — dropping back to the type modal would make the user re-pick a type they already selected. |
| Preconditions | The visitor reached the editor via the document-type modal (`реферат`) and the mode modal (`Ручной режим`). |
| Test data | Control: the breadcrumb `Назад` link; expected screen: the mode modal for `реферат` |
| Steps | 1. Click `Назад` in the editor breadcrumb.<br>2. Inspect the resulting screen. |
| Expected result | The mode modal is shown again with both mode cards; the document type is still scoped to `реферат` — the type modal is not re-shown and no type re-selection is required. |
| Status | Not run |

### TC-05-UI-6.2 — Reopening a previously saved document shows its saved content

| Field | Value |
|---|---|
| Description | The editor must hydrate from `GET`, not from a leftover client cache. A blank editor on reopen looks to the user like their document was lost. |
| Preconditions | Document A1 was created, formatted and saved in an earlier session with `<h3>Заголовок</h3>Текст <b>жирный</b>`; the browser session has been restarted (no in-memory state). |
| Test data | Route `/documents/3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3`; request `GET /api/v1/documents/{document_id}` |
| Steps | 1. Reopen document A1 in a fresh session.<br>2. Inspect the rendered content and its formatting. |
| Expected result | The editor renders exactly the last-saved content: the H3 heading, the text, and `жирный` still bold — the same markup the last successful save stored, with no formatting dropped and no placeholder shown. |
| Status | Not run |

---

## 7. Extended formatting toolbar (ProductSpecification/plans/jazzy-stirring-key.md)

No mockup exists for scenarios 7.1-7.9 — these extend the toolbar beyond what
`ProductSpecification/stories/05-manual-mode/mockups/` specifies, per user
direction outside the mockup process. `align-design` for these scenarios notes
"no mockup; reuse `.me-toolbar-btn` styling unchanged" instead of comparing
against a mockup file.

### TC-05-UI-7.1 — Applying strikethrough changes the content and highlights the active toolbar button

| Field | Value |
|---|---|
| Description | Each new toolbar mark needs both halves wired: the command that applies it and the state query that lights the button. A missing state query is the common half to forget. |
| Preconditions | The editor is open with `Удалённый текст` typed and the word `Удалённый` selected. |
| Test data | Control: the strikethrough toolbar button (`.me-toolbar-btn`); active class `active` |
| Steps | 1. Select `Удалённый`.<br>2. Click the strikethrough button.<br>3. Leave the cursor inside the struck text and inspect the button. |
| Expected result | `Удалённый` renders struck through (`<s>`/`<del>` mark in the content); the strikethrough button carries `active` while the cursor is within struck-through text. |
| Status | Not run |

### TC-05-UI-7.2 — Applying a blockquote changes the content and highlights the active toolbar button

| Field | Value |
|---|---|
| Description | Blockquote is a block node, not a mark — applying it must wrap the line rather than decorate the selection. |
| Preconditions | The editor is open with the cursor on the line `Цитата автора`. |
| Test data | Control: the blockquote toolbar button |
| Steps | 1. Place the cursor on the line `Цитата автора`.<br>2. Click the blockquote button.<br>3. Inspect the rendered line and the button. |
| Expected result | The line renders as a blockquote (`<blockquote>` in the content); the blockquote button carries `active` while the cursor is inside the blockquote. |
| Status | Not run |

### TC-05-UI-7.3 — Inserting a horizontal rule adds a divider at the cursor position

| Field | Value |
|---|---|
| Description | The rule must land at the cursor, not appended at document end — a node inserted in the wrong place is the classic mistake for a cursorless command. |
| Preconditions | The editor is open with `Первый абзац` and `Второй абзац`, cursor placed between them. |
| Test data | Control: the horizontal-rule toolbar button; expected node `<hr>` |
| Steps | 1. Place the cursor between the two lines.<br>2. Click the horizontal-rule button.<br>3. Inspect the content. |
| Expected result | An `<hr>` divider is rendered between `Первый абзац` and `Второй абзац` — at the cursor position, not at the end of the document. |
| Status | Not run |

### TC-05-UI-7.4 — Applying inline code and code blocks changes the content and highlights the active toolbar button

| Field | Value |
|---|---|
| Description | Inline code is a mark and a code block is a node; wiring one command to the other's state query lights the wrong button. |
| Preconditions | The editor is open with the text `print(1)` typed. |
| Test data | Controls: the inline-code button and the code-block button; expected elements `<code>` and `<pre><code>` |
| Steps | 1. Select `print(1)` and click the inline-code button; inspect the content and the button.<br>2. Undo, place the cursor on the line, click the code-block button; inspect the content and the button. |
| Expected result | Step 1: the selection renders as inline code (`<code>`) and the inline-code button carries `active` while the cursor is within it. Step 2: the line renders as a code block (`<pre><code>`) and the code-block button carries `active` while the cursor is within it; the inline-code button is not simultaneously active. |
| Status | Not run |

### TC-05-UI-7.5 — Undo and redo revert and reapply the last editor change, disabled when there is nothing to undo/redo

| Field | Value |
|---|---|
| Description | Undo/redo buttons that never disable tell the user an action is available when it is a no-op; redo that stays disabled after an undo makes the undo irreversible. |
| Preconditions | A freshly loaded editor with no edit history, then the text `Новый текст` typed into it. |
| Test data | Controls: the undo and redo toolbar buttons; `disabled` attribute on each |
| Steps | 1. On the freshly loaded editor, inspect the undo button.<br>2. Type `Новый текст`.<br>3. Click undo; inspect the content and the redo button.<br>4. Click redo; inspect the content. |
| Expected result | Step 1: the undo button is `disabled` (nothing to undo). Step 3: the typed text is reverted and the redo button becomes enabled. Step 4: `Новый текст` is restored. |
| Status | Not run |

### TC-05-UI-7.6 — Applying an H3 heading changes the content and highlights the active toolbar button

| Field | Value |
|---|---|
| Description | H3 is the only heading level the schema offers; it must apply as a real heading node so save/reload and export see semantic markup rather than styled text. |
| Preconditions | The editor is open with the cursor on the line `Раздел первый`. |
| Test data | Control: the `Heading 3` toolbar button; expected element `<h3>` |
| Steps | 1. Place the cursor on `Раздел первый`.<br>2. Click the `Heading 3` button.<br>3. Inspect the content and the button. |
| Expected result | The line renders as `<h3>Раздел первый</h3>`; the H3 button carries `active` while the cursor is within the heading. |
| Status | Not run |

### TC-05-UI-7.7 — Applying underline changes the content and highlights the active toolbar button

| Field | Value |
|---|---|
| Description | Underline must be its own mark with its own state query — reusing bold's query lights both buttons for one mark. |
| Preconditions | The editor is open with `Подчёркнутый` typed and selected. |
| Test data | Control: the underline toolbar button; expected element `<u>` |
| Steps | 1. Select `Подчёркнутый`.<br>2. Click the underline button.<br>3. Leave the cursor inside and inspect the toolbar. |
| Expected result | The selection renders underlined (`<u>` mark); the underline button carries `active` while the cursor is within underlined text, and the bold and italic buttons do not. |
| Status | Not run |

### TC-05-UI-7.8 — Applying text alignment changes the content and highlights the active toolbar button

| Field | Value |
|---|---|
| Description | Alignment is a per-line attribute with four mutually exclusive values; exactly one button may be active at a time or the user cannot read the current alignment. |
| Preconditions | The editor is open with the cursor on the line `Выровненный текст`. |
| Test data | Controls: the left, center, right and justify alignment buttons; values `left`, `center`, `right`, `justify` |
| Steps | 1. Click the center-align button; inspect the line and the four buttons.<br>2. Repeat for left, right, and justify in turn. |
| Expected result | After each click the line's alignment becomes the clicked value; the clicked button carries `active` while the cursor is on that line and the other three do not — exactly one alignment button is active at any moment. |
| Status | Not run |

### TC-05-UI-7.9 — Applying a link changes the content and highlights the active toolbar button

| Field | Value |
|---|---|
| Description | The link command takes a URL argument the others do not, so the prompt-and-apply path is a separate failure surface from the plain marks. |
| Preconditions | The editor is open with `Источник` typed and selected. |
| Test data | Control: the link toolbar button; URL `https://textery.test/doc` |
| Steps | 1. Select `Источник`.<br>2. Click the link button and enter `https://textery.test/doc`.<br>3. Leave the cursor inside the link and inspect the toolbar. |
| Expected result | `Источник` renders as a hyperlink whose `href` is exactly `https://textery.test/doc`; the link button carries `active` while the cursor is within the link. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---|---|
| `neither card shows a "скоро" badge` | both `.mode-card` elements render without `.disabled`/`soon-pill`, matching `02-mode-modal.html` |
| `an empty editor opens` | client navigates to the editor route for the newly created `document_id` |
| `an empty content area with a placeholder` | contenteditable region shows placeholder text, distinct from a loading spinner/skeleton |
| `the formatting toolbar` | toolbar buttons for `heading-1`/`heading-2`/`pilcrow`/`list`/`list-ordered`/`bold`/`italic`, per `03-editor-empty.html` |
| `applies bold formatting` | toolbar bold button or `Ctrl+B` shortcut on a text selection |
| `the bold toolbar button shows as active` | `.toolbar-btn.active` class applied while selection/cursor is within bold-formatted text |
| `moves the cursor from inside bold text to inside non-bold text` | cursor placed via click/arrow-key navigation between differently-formatted spans |
| `clicks "Сохранить"` | save button triggers `PUT /api/v1/documents/{document_id}` |
| `shows a loading state and becomes disabled` | button shows spinner, `disabled` attribute set, matching mass-assignment-safe in-flight lock |
| `a second click while the save is in flight has no additional effect` | disabled button does not fire a second `PUT` request |
| `two saves... out of order` | two `PUT` requests in flight where the later-triggered one's response resolves first |
| `the displayed save status reflects the second, more recent save` | UI tracks save requests by a monotonic client-side sequence/timestamp, ignoring a stale response that resolves after a newer one |
| `an inline "Сохранено" confirmation` | success indicator per `05-editor-saved.html`, no route change |
| `an inline error message` | error banner per `06-editor-error.html` |
| `clicks "Назад"` | breadcrumb back-link navigates to the mode modal for the current document type |
| `reopens that same document` | client navigates to `GET /api/v1/documents/{document_id}` for a document created in a prior session |
