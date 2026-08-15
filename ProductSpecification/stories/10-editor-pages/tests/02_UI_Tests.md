> **Implementation Order**: sequential TDD — measuring state → sheet display → counter →
> manual break → settings panel → validation feedback → failure handling → navigation.

# Editor pages — UI Tests

## 1. Pre-layout State

### 1.1 Pagination waits for the document font
```gherkin
Given a document is opened and the document font has not finished loading
When the editor is displayed
Then the measuring state is shown
And no page count is displayed
And the state is visibly distinct from an error and from an empty document
```

### 1.2 The page count appears only once the font has resolved
```gherkin
Given a document is opened with the document font still loading
When the font finishes loading
Then the pages are laid out and the page count appears
And the count does not change again on its own afterwards
```

### 1.3 A font that never loads reaches a defined outcome, not a permanent spinner
```gherkin
Given a document is opened and the document font never loads
When the load deadline passes
Then a defined outcome is shown rather than an indefinite measuring state
```

---

## 2. Sheet Display

### 2.1 Content is laid out on discrete sheets
```gherkin
Given a document longer than one page
When the editor displays it
Then the content is shown on separate sheets with a visible gap between them
And a block that does not fit continues on the following sheet
```

### 2.2 The first page carries no number by default, later pages do
```gherkin
Given a document of more than one page with default page settings
When the editor displays it
Then no page number is shown on the first sheet
And each following sheet shows its number
```

### 2.3 An empty document shows one blank sheet
```gherkin
Given a document with no content
When the editor displays it
Then exactly one empty sheet is shown
And the page count reads one of one
And no spinner or empty-state placeholder is shown
```

---

## 3. Page Counter

### 3.1 The counter follows the caret and updates as the user types
```gherkin
Given a document of more than one page
When the user moves the caret to a later page
Then the counter shows that page as current
When the user types enough content to add a page
Then the total in the counter increases
```

### 3.2 A shortfall against the requested volume is shown
```gherkin
Given a document generated with a requested page count larger than it turned out
When the editor displays it
Then the shortfall is shown against the requested number
And no control is offered that would generate more content
```

---

## 4. Manual Page Break

### 4.1 An inserted break starts a new sheet
```gherkin
Given the caret is inside a page of content
When the user inserts a page break
Then the content after the caret starts on a new sheet
And a break marker is visible at the insertion point
```

### 4.2 Editing above a break re-flows the pages without moving the break
```gherkin
Given a document containing a manual page break
When the user adds a paragraph above the break
Then the pages before the break re-flow
And the break still separates the same content it separated before
```

### 4.3 A break can be selected and deleted
```gherkin
Given a document containing a manual page break
When the user selects the break marker and deletes it
Then the content after it re-joins the preceding page flow
```

---

## 5. Page Setup Panel

### 5.1 The panel opens with the document's effective settings
```gherkin
Given a document with saved page settings
When the user opens the page setup panel
Then every field shows the saved value
Given a document that has never been configured
When the user opens the panel
Then every field shows the default preset value
```

### 5.2 Applying a change re-paginates the document
```gherkin
Given the page setup panel is open
When the user changes the sheet size and applies
Then the save succeeds
And the sheets are redrawn at the new geometry
And the page count is recalculated
```

---

## 6. Validation Feedback

### 6.1 A rejected value is reported inline against its own field
```gherkin
Given the page setup panel is open
When the user enters margins that leave no room for text and applies
Then an error is shown against the margin fields
And the message states why the values do not fit, not merely that they are invalid
And no value is silently corrected
```

### 6.2 An over-length header is refused rather than trimmed
```gherkin
Given the page setup panel is open
When the user enters a header longer than the limit and applies
Then an error is shown against the header field
And the entered text is left as the user typed it
```

---

## 7. Failure Handling

### 7.1 A failed save is shown differently from a rejected value
```gherkin
Given the page setup panel is open with valid values
When the save cannot reach the server
Then a failure banner with a retry action is shown
And it is visibly distinct from the inline field errors
And the entered values are preserved
```

### 7.2 A rejected geometry rolls the layout back
```gherkin
Given a document laid out at its saved geometry
When the user applies a geometry the server rejects
Then the sheets remain laid out at the previously saved geometry
And the editor is not left showing a layout the server does not hold
```

### 7.3 A late response never replaces newer state
```gherkin
Given a content save and a page-settings save are both in flight
When the earlier request's response arrives last
Then the editor still shows the result of the later save
```

### 7.4 An in-flight action cannot be triggered twice
```gherkin
Given a page-settings save or an export is in flight
When the user activates the same control again
Then no second request is issued
```

### 7.5 Unsaved panel edits are guarded against leaving
```gherkin
Given the user has typed a header text in the page setup panel without applying
When they attempt to leave the page
Then they are warned before the edits are lost
```

---

## 8. Navigation

### 8.1 Selecting a page in the rail scrolls to it
```gherkin
Given a document of more than one page
When the user selects a later page in the page rail
Then the editor scrolls to that sheet
And that page is marked as current
```

### 8.2 The page rail offers no way to create a page
```gherkin
Given a document is open
When the user inspects the page rail
Then the only page action offered is inserting a break
And no control claims to add or delete a page
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the measuring state` | Skeleton sheet + rail skeletons, no page count in the status bar |
| `the document font` | The bundled Liberation Serif webfont; readiness via `document.fonts` |
| `a defined outcome` | Named error/degraded state — not an indefinite spinner |
| `the page rail` | Left column listing pages (desktop) / chip strip (mobile) |
| `inserts a page break` | Ctrl+Enter or the toolbar/rail break action |
| `applies` | The panel's apply control, issuing `PUT /api/v1/documents/{id}` |
| `the save cannot reach the server` | Stubbed network failure / 5xx on the save request |
| `the server rejects` | Stubbed 422 on the save request |
| `attempt to leave the page` | Reload / navigate away, triggering the dirty-state guard |
