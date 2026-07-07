# Security Adapter Test Template

## Test Class Rules

- Pure unit tests -- NO FastAPI test client context for `JwtService`/OAuth client tests
- Mock dependencies with `pytest-mock`'s `mocker.Mock()` / `mocker.AsyncMock()` (OAuth clients are async)
- Construct the class under test manually in a fixture or at the top of the test
- Use `FakeClock` for deterministic time -- never `mocker.patch("time.time")` directly (see `tdd.md` Test Clock)
- Use class-level docstring with Gherkin-style description

## Security-Specific Failure Patterns

| Current Implementation | Expected Test Failure |
|----------------------|----------------------|
| Wrong mock interaction | Mock verification failure |
| JWT expiry not enforced | `assert_raises(ExpiredTokenException)` fails to raise |

## Reference (read before generating)

- Existing test: `backend/adapters/security/tests/test_jwt_service.py`
- JWT service: `backend/adapters/security/src/jwt_service.py`
- Config: `backend/adapters/security/src/jwt_config.py`
- Auth dependency: `backend/adapters/security/src/dependency/current_user.py`

## Test Pattern

1. **Setup**: create mocks, fixed `FakeClock`, construct class under test
2. **Mock**: `mock_dependency.method.return_value = value` (or `mocker.AsyncMock(return_value=value)` for async collaborators)
3. **Execute**: call method under test (`await` if async)
4. **Assert**: use `assert actual == expected` with descriptive messages
5. **Verify** (optional): `mock_dependency.method.assert_called_once_with(args)` for side-effect verification

## Naming Convention

- Test file: `test_{component_name}.py`
- Test method: `test_should_{expected_behavior}`

## Key Paths

- Tests: `backend/adapters/security/tests/`
- Production: `backend/adapters/security/src/`
