> **Implementation Order**: sequential TDD — block schema first (everything stands on it),
> then lists, autosave, title, paste-sanitize, undo/redo, count, tables.

# Story 5 — Editor Extension Tests (points 1–8)

Covers the editor upgrade in `editor-extension.md`. Mostly frontend; the `title` column is
backend (shared with stories 17/18).

## 1. Block Schema

### 1.1 Multi-paragraph block content round-trips
```gherkin
Given the editor with block content: paragraphs, H1, H2, H3
When the document is saved and reloaded
Then each block returns as its correct semantic element
```

### 1.2 An existing inline-only document loads without data loss
```gherkin
Given a document saved before the block-schema migration
When it is opened in the upgraded editor
Then its content loads intact
```

### 1.3 Inline marks survive co-resident with block nodes
```gherkin
Given block content whose paragraphs and headings contain inline marks (bold, link, code, alignment)
When the document is saved and reloaded
Then the inline marks round-trip intact inside their block nodes, not stripped
```
> Added by ADR `decisions/block-schema-migration-decision.md` (premortem gap #2): the base
> block round-trip (1.1) only exercises bare-text blocks; this pins mixed inline+block content.

## 2. Lists

### 2.1 Bulleted and numbered lists round-trip
```gherkin
Given the editor with a bulleted list and a numbered list
When the document is saved and reloaded
Then both lists return as the correct semantic elements
```

## 3. Autosave

### 3.1 Edits autosave without an explicit click
```gherkin
Given a document open with unsaved edits
When the user stops typing past the debounce interval
Then the edits are saved automatically
And a saved indicator is shown
```

### 3.2 A failed autosave keeps the content and shows the failure
```gherkin
Given a document open with edits
When an autosave fails
Then the editor content is not cleared
And a failed-save state is shown
```

### 3.3 Out-of-order autosave responses reflect the latest edit
```gherkin
Given two autosaves in flight resolving out of order
When they return
Then the shown save status reflects the latest edit
```

### 3.4 A stale autosave is rejected, not a silent overwrite
```gherkin
Given the document was updated in another session
When an autosave lands against a stale version
Then it is rejected as a version conflict and reconciled
And the other session's edit is not overwritten
```

## 4. Document Title

### 4.1 A title can be set and round-trips
```gherkin
Given a document open in the editor
When the user sets a title and saves
Then reopening the document shows that title
```

### 4.2 An over-length title is rejected at the boundary
```gherkin
Given a document open in the editor
When the user saves a title past the pinned max length
Then the save is refused at the boundary, never truncated silently
```

### 4.3 Markup in the title is neutralized
```gherkin
Given a title containing markup and control characters
When it is saved
Then the stored title carries no markup
```

## 5. Paste Sanitize

### 5.1 Pasted rich content is sanitized before entering the document
```gherkin
Given the user pastes rich HTML containing a script, an event handler, and a javascript link
When the paste lands in the editor
Then none of them enter the document content
```

### 5.2 The server re-sanitizes on save regardless of the client
```gherkin
Given content submitted directly to save bypassing the editor with dangerous markup
When it is saved
Then the stored content is sanitized
```

## 6. Undo / Redo

### 6.1 Undo and redo restore block structure
```gherkin
Given the user applies a heading and a list, then undoes
When they redo
Then the block structure is restored, not just inline text
```

## 7. Word / Character Count

### 7.1 The count reflects content in grapheme clusters
```gherkin
Given content containing a combining accent and an emoji
When the count is shown
Then each counts as one grapheme
And the count updates as the user types
```

## 8. Tables

### 8.1 A table can be inserted and round-trips
```gherkin
Given the user inserts a table and fills cells
When the document is saved and reloaded
Then the table and its cell content return intact
```
