# Database Storage Test Template

## Test Class Rules

- Use an async fixture that opens a connection, begins a transaction, yields an `AsyncSession` bound to it, and rolls back the transaction on teardown — never truncate tables or recreate the schema per test.
- Inject the storage class under test with that session.
- Use class-level docstring with Gherkin-style description.
- Test methods are `async def test_...` (see `tdd.md` Async Test Execution).

## DB-Specific Failure Patterns

| Current Implementation | Expected Test Failure |
|----------------------|----------------------|
| `return None` | `assert result is not None` or `assert result == expected` |
| `return []` | `assert result != []` or `assert result == expected` |

## Reference (read before generating)

- Test example: `backend/adapters/db/tests/access/{feature}/test_{feature}_storage.py`
- Test setup: `backend/adapters/db/tests/conftest.py`
- Storage example: `backend/adapters/db/src/access/{feature}/{feature}_storage.py`
- Model example: `backend/adapters/db/src/model/{feature}/{feature}_model.py`

## Naming Convention

- Test file: `test_{entity}_storage_{method}.py`
- Test method: `test_should_{expected_behavior}`

## Key Paths

- Tests: `backend/adapters/db/tests/access/`
- Production: `backend/adapters/db/src/access/`
- Models: `backend/adapters/db/src/model/`
- Migrations: `backend/adapters/db/migrations/versions/`
