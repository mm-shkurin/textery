<!-- COPIED FILE. Source of truth: ProductSpecification/stories/18-generate-then-edit/tests/extended/06_Integration_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Generate → edit — Integration Tests (Extended)

## 1. Conversion Fidelity Variants

### 1.1 Mixed markdown and multibyte content converts faithfully
```gherkin
Given a completed generation whose markdown content also contains Cyrillic and emoji
When it is converted
Then the sanitized HTML preserves both the structure and the multibyte characters
```

## 2. Idempotent End-to-End

### 2.1 A double auto-transition yields one document end to end
```gherkin
Given the fake provider is configured
When a generation completes and the client fires the conversion twice
Then exactly one document exists and opens in the editor
```
