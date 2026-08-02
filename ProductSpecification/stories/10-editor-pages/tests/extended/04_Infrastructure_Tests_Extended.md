> These are additional edge case tests. Implement after core tests pass.

# Editor pages — Infrastructure Tests (Extended)

## 1. Font Asset

### 1.1 A corrupted font asset fails at boot, not at first render
```gherkin
Given the bundled font file is present but truncated or corrupt
When the application starts
Then startup fails with an explicit message
And no export is ever served against the corrupt asset
```

### 1.2 The frontend and the renderer carry the same font file
```gherkin
Given the deployed frontend bundle and the deployed backend image
When the bundled font asset in each is compared
Then the two files are byte-identical
```

A drift between the two is invisible in every functional test and quietly breaks the one
property the shared font exists to provide.

---

## 2. Migration

### 2.1 The migration is reversible without touching document content
```gherkin
Given the page-settings column has been added
When the migration is rolled back
Then no document's content or version is altered
```

### 2.2 The migration does not rewrite existing rows
```gherkin
Given a table of documents predating the column
When the migration runs
Then no existing row is written to
And every document reads back as unconfigured
```

---

## 3. Configuration

### 3.1 An unset pagination or render budget fails fast
```gherkin
Given the pagination or render deadline configuration is absent
When the application starts
Then startup fails naming the missing configuration
And it is not silently defaulted at the first request
```

### 3.2 The render locale is pinned rather than inherited
```gherkin
Given a runtime whose ambient locale uses a comma decimal separator
When the application starts and a document is exported
Then the export uses the pinned formatting locale
And the ambient locale does not reach the render path
```
