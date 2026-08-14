<!-- COPIED FILE. Source of truth: ProductSpecification/stories/17-export-document/tests/extended/06_Integration_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Export document — Integration Tests (Extended)

## 1. Generated-Document Export

### 1.1 A generated-then-edited document exports faithfully
```gherkin
Given a document created from a generation and then edited and saved
When it is exported to pdf and docx
Then each file reflects the edited content
```
