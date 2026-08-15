<!-- COPIED FILE. Source of truth: ProductSpecification/stories/17-export-document/tests/extended/01_API_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Export document — API Tests (Extended)

## 1. Content Edge Cases

### 1.1 A document at the content limit still exports
```gherkin
Given a document whose content is at the content limit
When it is exported
Then a valid file is returned within the render deadline
```

### 1.2 Content with only whitespace exports to a valid file
```gherkin
Given a document whose content is only whitespace
When it is exported
Then a valid near-empty file is returned
```

## 2. Format Casing

### 2.1 Format matching is exact, not case-folded loosely
```gherkin
Given a document owned by the caller
When it is exported with a mixed-case format value
Then the endpoint applies its documented casing rule consistently
```
