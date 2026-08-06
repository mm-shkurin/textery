> These are additional edge case tests. Implement after core tests pass.

# Editor pages — Integration Tests (Extended)

## 1. Geometry Across Targets

### 1.1 Every supported sheet size and orientation renders at its declared dimensions
```gherkin
Given each supported sheet size in each orientation
When a document is exported as pdf and as docx
Then each file's page dimensions match the declared millimetre values for that size
```

### 1.2 The same settings render identically on repeated exports
```gherkin
Given a document with non-default page settings
When it is exported twice without any change in between
Then the two files carry identical geometry
And differ only in fields that are expected to differ between renders
```

---

## 2. Content Round-Trip

### 2.1 A manual break survives a full save, reload and export cycle
```gherkin
Given a document containing a manual page break
When it is saved, reloaded in the editor, and exported
Then the break is present at the same position in the content at every step
And the sanitizer has not stripped it
```

### 2.2 A legacy document with no breaks and no settings exports unchanged
```gherkin
Given a document created before this story
When it is opened, saved without edits, and exported
Then its content is unchanged
And its page settings remain unconfigured
And the exported file matches the pre-story output
```

---

## 3. Multibyte

### 3.1 Header, footer and page numbers survive multibyte content into both formats
```gherkin
Given a document with Cyrillic content, an emoji header and a combining-accent footer
When it is exported as pdf and as docx
Then no replacement character appears in either file
And the header, footer and page numbers are present as submitted
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the declared millimetre values` | A4 210×297, A5 148×210, Letter 215.9×279.4 |
| `fields expected to differ between renders` | Timestamps written by the render library |
| `the pre-story output` | A stored reference file produced before page settings existed |
