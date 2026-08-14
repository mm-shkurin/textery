<!-- COPIED FILE. Source of truth: ProductSpecification/stories/01-auto-generate-doklad/tests/extended/05_Security_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Auto-generate: доклад — Security Tests (Extended)

> Both scenarios originally drafted here were promoted to `05_Security_Tests.md`
> (§8.1 header injection, §9.1 oversized payload) — hazard-catalogue scan (2026-07-06)
> found this is a fully public, unthrottled, paid endpoint, making pre-parse cost/
> injection guards critical-path, not edge cases. No further edge cases identified for
> this category yet.
