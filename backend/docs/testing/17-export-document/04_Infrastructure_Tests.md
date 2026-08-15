<!-- COPIED FILE. Source of truth: ProductSpecification/stories/17-export-document/tests/04_Infrastructure_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Export document — Infrastructure Tests

Native render dependencies, config fail-fast, resource release, and the shared schema
change.

## 1. Render Dependencies

### 1.1 Missing native render libraries fail fast at boot
```gherkin
Given the render backend's native libraries are absent from the image
When the application starts or its health check runs
Then it fails fast and loud
And does not surface the failure as a runtime error on the first export
```

### 1.2 An unset render-timeout config fails fast at boot
```gherkin
Given the render-timeout configuration is unset
When the application starts
Then it fails fast rather than rendering unbounded at runtime
```

### 1.3 The render dependencies pass the vulnerability audit
```gherkin
Given the new render dependencies in the lockfile
When the dependency audit runs
Then it reports no known vulnerability
```

## 2. Resource Release

### 2.1 Repeated exports including failures do not leak resources
```gherkin
Given a sequence of exports that includes induced render failures
When they run
Then native and memory resources return to baseline
And do not grow monotonically
```

## 3. Schema

### 3.1 Old code serves documents after the title column lands
```gherkin
Given the pre-migration application code
When it reads and serves documents against the migrated schema with the new title column
Then it succeeds without error
```
