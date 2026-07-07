# Test Review Patterns: DB Adapter Layer (Python/FastAPI, SQLAlchemy async)

Python/pytest code examples for persistence adapter test anti-patterns. For universal rules: `.claude/templates/testing/test-review-patterns.md`

## Python-Specific Rules (DB)

1. **Use descriptive assertion messages** -- add a second argument to `assert` for clear failure messages
2. **Prefer dataclass equality** -- replace 2+ sequential per-field `assert` calls with `assert actual == expected` (frozen dataclasses do deep structural comparison by default)
3. **Use timedelta for timestamp comparisons** -- assert `abs(actual - expected) < timedelta(minutes=1)`. Never truncate to minutes -- truncation causes flaky failures at minute boundaries
4. **`await` every session call in assertions** -- `AsyncSession.execute()`, `.commit()`, `.refresh()` are all coroutines; a missing `await` silently returns a coroutine object that is always truthy, masking a broken assertion

## Anti-Pattern Examples

Persistence adapter tests share many patterns with usecase and acceptance tests. Common issues:

- **Loose existence checks** on returned entities -- use `== expected` not `is not None`
- **Missing field assertions** on `to_domain()` results -- assert ALL domain fields after round-trip
- **Timestamp precision mismatches** -- use timedelta within 60 seconds, never truncate
- **Missing `await`** on `AsyncSession` calls in test setup or assertions (see rule 4 above)

See `test-review-usecase.md` for Statements purity patterns and `test-review-acceptance.md` for assertion strictness patterns -- both apply to DB adapter tests.
