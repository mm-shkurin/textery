<!-- COPIED FILE. Source of truth: ProductSpecification/stories/01-auto-generate-doklad/tests/extended/02_UI_Tests_Extended.md
     Regenerate with `node scripts/sync-test-cases.mjs` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Auto-generate: доклад — UI Tests (Extended)

## 1. Disabled Document Types

### 1.1 Clicking a "coming soon" document type does nothing

```gherkin
Given the visitor is on the generation form
When the visitor clicks one of the not-yet-available document type cards
Then nothing happens
And the currently selected type remains "доклад"
```

## 2. Long-Running Pending State

### 2.1 The pending view keeps polling if generation takes longer than usual

```gherkin
Given the visitor's generation is still pending after the typical wait time
Then the pending view continues showing the waiting state
And does not show an error before the generation actually fails
```

## 3. Field-Level Edge Cases

### 3.1 The requirements and extra wishes fields show a character counter near the limit

```gherkin
Given the visitor is typing in the requirements field
And the text approaches the maximum allowed length
Then a character counter is shown to indicate the remaining allowance
```
