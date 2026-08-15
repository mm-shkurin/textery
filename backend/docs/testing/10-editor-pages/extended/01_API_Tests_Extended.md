<!-- COPIED FILE. Source of truth: ProductSpecification/stories/10-editor-pages/tests/extended/01_API_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Editor pages — API Tests (Extended)

## 1. Page Settings Edges

### 1.1 Zero margins are accepted
```gherkin
Given a document owned by the caller
When they save all four margins as zero
Then the save succeeds
And the content box equals the full sheet
```

### 1.2 An empty header text is distinguishable from an absent one
```gherkin
Given a document owned by the caller
When they save a header text that is an empty string
Then reading it back returns an empty header, not an absent one
```

### 1.3 Whitespace-only header text is trimmed to nothing
```gherkin
Given a document owned by the caller
When they save a header text consisting only of whitespace
Then the stored header is empty
And no whitespace-only running head is rendered
```

### 1.4 A fractional margin round-trips without drift
```gherkin
Given a document owned by the caller
When they save a margin with a fractional millimetre value
Then reading it back returns the same value
And exporting twice produces the same geometry both times
```

### 1.5 Landscape swaps the effective content box
```gherkin
Given a document with margins that fit in landscape but not in portrait
When the caller saves it as landscape
Then the save succeeds
When they then switch it to portrait without changing margins
Then the request is refused as unprocessable
```

---

## 2. Interaction With Content

### 2.1 Content at the size limit still accepts a settings change
```gherkin
Given a document whose content is at the maximum permitted size
When the caller saves new page settings without changing content
Then the save succeeds
```

### 2.2 A document consisting only of manual breaks is handled
```gherkin
Given a document whose content is a run of consecutive manual page breaks
When the caller reads and exports it
Then each break produces one page
And no empty trailing page is produced beyond the last break
```

### 2.3 A manual break as the very first block does not create a leading blank page
```gherkin
Given a document beginning with a manual page break
When it is read and exported
Then no blank page precedes the first content
```

---

## 3. Concurrency Edges

### 3.1 A settings save and a settings save race resolves to one winner
```gherkin
Given two clients holding the same document version
When both save different page settings simultaneously
Then exactly one succeeds
And the other is refused as a conflict
And the stored settings are one of the two submitted objects, never a blend
```

### 3.2 A conflict response carries the information needed to retry
```gherkin
Given a client whose page-settings save is refused as a conflict
When it refetches the document
Then it receives the current version and the current settings
And a resubmission under that version succeeds
```
