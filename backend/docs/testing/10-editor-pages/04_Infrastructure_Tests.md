<!-- COPIED FILE. Source of truth: ProductSpecification/stories/10-editor-pages/tests/04_Infrastructure_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Editor pages — Infrastructure Tests

---

## 1. Startup Validation

### 1.1 A missing document font fails the application at boot
```gherkin
Given the bundled document font asset is absent or unreadable
When the application starts
Then startup fails with an explicit message naming the missing asset
And the application does not begin serving requests
```

This is the guard that keeps the font from failing *lazily*: without it, a misbuilt image
serves successful exports laid out in a substitute face, which is a wrong document that
looks like a right one.

### 1.2 The render path depends on no system-installed face
```gherkin
Given a runtime image carrying no system fonts beyond the bundled asset
When a document is exported
Then the render succeeds using the bundled face
```

---

## 2. Database

### 2.1 The database being unavailable does not lose the user's page settings
```gherkin
Given a user has applied page settings in the editor
When the database is unavailable at the moment of the save
Then the save is reported as failed with the sanctioned error
And the entered values are still present in the panel
And no partially written settings are left behind
```

### 2.2 Page settings survive a database restart
```gherkin
Given a document with saved page settings
When the database restarts and connections are re-established
Then the document reads back with the same page settings
```

---

## 3. Rolling Deploy

### 3.1 An old instance still serves documents after the column lands
```gherkin
Given the page-settings column has been added by migration
And an instance running the previous application version
When that instance reads and serves a document
Then the read succeeds
```

### 3.2 An old instance's save does not erase page settings
```gherkin
Given a document whose page settings were written by the new version
When an instance running the previous version saves that document
Then the stored page settings are byte-identical afterwards
And are not cleared
```

This is the half of the rolling-deploy story that the read path does not cover: a
full-row write from a model that has no such column is what silently drops the data.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the bundled document font asset` | The Liberation Serif webfont shipped in the image / frontend bundle |
| `startup fails` | Fail-fast at application boot, consistent with story 17's missing-render-lib rule |
| `the previous application version` | An application build without `page_settings` in its document model |
| `the sanctioned error` | Generic client-safe error body, no internals |
