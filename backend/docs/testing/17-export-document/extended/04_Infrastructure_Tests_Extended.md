<!-- COPIED FILE. Source of truth: ProductSpecification/stories/17-export-document/tests/extended/04_Infrastructure_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Export document — Infrastructure Tests (Extended)

## 1. Image Reproducibility

### 1.1 The render libraries are present in the built image
```gherkin
Given the built backend image
When the render backend is probed
Then the required native libraries are present and loadable
```
