# Controller Test Template -- Python/FastAPI/Hexagonal

> Universal rules: `.claude/templates/tdd/red-rest.md`

## Tech-Specific Rules

- Use `httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")` against the FastAPI app instance — no running server needed.
- Override the usecase dependency with `app.dependency_overrides[get_{feature}_usecase] = lambda: mock_usecase` (mock built with `pytest-mock`'s `mocker.Mock()`), then clear overrides in teardown.
- Create exactly ONE test method, add `@pytest.mark.skip`
- Use class-level docstring with Gherkin-style description
- Setup: `mock_usecase.execute.return_value = ...` (or `AsyncMock` return value if the mock itself needs to be awaitable — `mocker.Mock()` methods called with `await` must be `mocker.AsyncMock()`)
- Execute: `response = await client.get("/api/...")` / `await client.post("/api/...", json=body)`
- Verify: `assert response.json() == expected`

## Expected Response JSON

Create in `backend/adapters/rest/tests/fixtures/{feature}/` or inline as dict literals for small responses.

## Reference (read before generating)

- Test example: `backend/adapters/rest/tests/router/{feature}/test_{feature}_router.py`
- Test setup: `backend/adapters/rest/tests/conftest.py`
- Request DTO example: `backend/adapters/rest/src/dto/{feature}/{feature}_request_dto.py`
- JSON fixture example: `backend/adapters/rest/tests/fixtures/` (look for existing JSON files)

## Key Paths

- Tests: `backend/adapters/rest/tests/router/`
- Production: `backend/adapters/rest/src/router/`
- DTOs: `backend/adapters/rest/src/dto/`
- Fixtures: `backend/adapters/rest/tests/fixtures/`
