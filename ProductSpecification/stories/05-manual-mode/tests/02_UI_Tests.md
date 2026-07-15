# Manual input mode (non-AI document creation) — UI Tests

> **Implementation Order**: Tests are numbered for sequential TDD implementation.
> Start with mode-modal display (reused component, small change), then the empty editor
> display, then formatting interaction, then save submission, then save feedback, then
> navigation.

No prerequisite blocker screens apply to this story — there is no parent resource that
must exist before the flow can start. The type-select modal is reused unchanged from
story #1 and is not retested here.

---

## 1. Mode Modal

### 1.1 The mode modal now shows both modes as available

```gherkin
Given the mode modal is open, reached via the document-type modal
Then "Ручной режим" and "Автоматический режим" cards are both shown as available and
  selectable
And neither card shows a "скоро" badge
```

### 1.2 Selecting Ручной режим opens the empty editor

```gherkin
Given the mode modal is open
When the visitor selects "Ручной режим"
Then the mode modal closes
And an empty editor opens, scoped to the chosen document type
```

---

## 2. Empty Editor — Page Display

### 2.1 A freshly created document shows an empty, ready-to-type editor

```gherkin
Given a visitor has just created a manual document
Then the editor shows an empty content area with a placeholder, not a loading skeleton
And the formatting toolbar is visible with heading, paragraph, list, bold, and italic
  controls
And the breadcrumb shows the chosen document type and "Ручной режим"
```

---

## 3. Formatting Interaction

### 3.1 Applying a format changes the content and highlights the active toolbar button

```gherkin
Given the visitor has typed some text in the editor
When the visitor selects the text and applies bold formatting
Then the selected text is rendered bold
And the bold toolbar button shows as active while the cursor remains inside it
```

### 3.2 The toolbar reflects formatting state at the cursor position, not globally

```gherkin
Given the editor contains both bold and non-bold text
When the visitor moves the cursor from inside bold text to inside non-bold text
Then the bold toolbar button becomes inactive
And no other formatting button is incorrectly shown as active
```

---

## 4. Save Submission

### 4.1 Saving shows a loading state and disables the save control

```gherkin
Given the visitor has typed and formatted content in the editor
When the visitor clicks "Сохранить"
Then the save control shows a loading state and becomes disabled
And a second click while the save is in flight has no additional effect
```

### 4.2 A save completing out of order still reflects the latest edit, not a stale response

```gherkin
Given the visitor triggers a save, then keeps editing and triggers a second save before
  the first save's response has arrived
When the first save's response arrives after the second save's response
Then the displayed save status reflects the second, more recent save
And the stale first response does not overwrite the newer status shown to the visitor
```

---

## 5. Save Feedback

### 5.1 A successful save shows a lightweight confirmation, no full-page transition

```gherkin
Given the visitor has clicked "Сохранить" on valid content
When the save completes successfully
Then an inline "Сохранено" confirmation is shown
And the visitor remains on the same editor, with no page navigation
```

### 5.2 A failed save shows an inline error and keeps the content in the editor

```gherkin
Given the visitor has clicked "Сохранить" and the save request fails
Then an inline error message is shown
And the visitor's typed content remains in the editor, never cleared
```

---

## 6. Navigation

### 6.1 "Назад" from the editor returns to the mode modal

```gherkin
Given the visitor is in the editor, reached via the type and mode modals
When the visitor clicks "Назад"
Then the visitor is returned to the mode modal, document type still scoped
```

### 6.2 Reopening a previously saved document shows its saved content

```gherkin
Given a manual document was created, formatted, and saved in an earlier session
When the visitor reopens that same document
Then the editor shows exactly the content and formatting that was last saved
```

---

## 7. Extended formatting toolbar (ProductSpecification/plans/jazzy-stirring-key.md)

No mockup exists for scenarios 7.1-7.9 — these extend the toolbar beyond what
`ProductSpecification/stories/05-manual-mode/mockups/` specifies, per user
direction outside the mockup process. `align-design` for these scenarios notes
"no mockup; reuse `.me-toolbar-btn` styling unchanged" instead of comparing
against a mockup file.

### 7.1 Applying strikethrough changes the content and highlights the active toolbar button

```gherkin
Given the visitor has selected text in the editor
When the visitor clicks the strikethrough toolbar button
Then the selected text is struck through
And the strikethrough toolbar button shows as active while the cursor is within struck-through text
```

### 7.2 Applying a blockquote changes the content and highlights the active toolbar button

```gherkin
Given the visitor's cursor is on a line of text in the editor
When the visitor clicks the blockquote toolbar button
Then the line is rendered as a blockquote
And the blockquote toolbar button shows as active while the cursor is within a blockquote
```

### 7.3 Inserting a horizontal rule adds a divider at the cursor position

```gherkin
Given the visitor's cursor is at some position in the editor content
When the visitor clicks the horizontal-rule toolbar button
Then a horizontal divider is inserted at the cursor position
```

### 7.4 Applying inline code and code blocks changes the content and highlights the active toolbar button

```gherkin
Given the visitor has selected text in the editor
When the visitor clicks the inline-code toolbar button
Then the selected text is rendered as inline code
And the inline-code toolbar button shows as active while the cursor is within inline code

Given the visitor's cursor is on a line of text in the editor
When the visitor clicks the code-block toolbar button
Then the line is rendered as a code block
And the code-block toolbar button shows as active while the cursor is within a code block
```

### 7.5 Undo and redo revert and reapply the last editor change, disabled when there is nothing to undo/redo

```gherkin
Given the visitor has just typed content into the editor
When the visitor clicks the undo toolbar button
Then the last change is reverted
And the redo toolbar button becomes enabled

Given the editor has no changes left to undo
Then the undo toolbar button is disabled
```

### 7.6 Applying an H3 heading changes the content and highlights the active toolbar button

```gherkin
Given the visitor's cursor is on a line of text in the editor
When the visitor clicks the "Heading 3" toolbar button
Then the line is rendered as an H3 heading
And the H3 toolbar button shows as active while the cursor is within an H3 heading
```

### 7.7 Applying underline changes the content and highlights the active toolbar button

```gherkin
Given the visitor has selected text in the editor
When the visitor clicks the underline toolbar button
Then the selected text is underlined
And the underline toolbar button shows as active while the cursor is within underlined text
```

### 7.8 Applying text alignment changes the content and highlights the active toolbar button

```gherkin
Given the visitor's cursor is on a line of text in the editor
When the visitor clicks the center-align toolbar button
Then the line's text alignment becomes centered
And the center-align toolbar button shows as active while the cursor is on that line
And the same holds for left, right, and justify alignment
```

### 7.9 Applying a link changes the content and highlights the active toolbar button

```gherkin
Given the visitor has selected text in the editor
When the visitor clicks the link toolbar button and provides a URL
Then the selected text becomes a hyperlink to that URL
And the link toolbar button shows as active while the cursor is within a link
```

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
