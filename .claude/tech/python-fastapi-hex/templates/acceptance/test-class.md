# Acceptance Test Template -- Python/FastAPI/Hexagonal

> Universal structure and rules: `.claude/templates/tdd/red-acceptance.md`

## Framework Rules

- Inherits from `AbstractBackendTest` (backend) or `AbstractUiTest` (frontend)
- `@pytest.mark.skip(reason="TDD Red Phase - Not yet implemented")` on test class
- Not-implemented marker in Statements: `raise NotImplementedError()`
- Add class-level docstring with Gherkin-style scenario
- Statements are plain classes instantiated in `conftest.py` fixtures
- Backend API tests hit the real running FastAPI app (via `application_client`, an `httpx.AsyncClient` pointed at `BACKEND_PORT`) and a real `arq` worker for generation flows -- no in-process `ASGITransport` shortcut here, this is black-box

## Test Types

| Type | Base Class | Marker |
|------|------------|--------|
| Backend API | `AbstractBackendTest` | `@pytest.mark.backend` |
| Frontend UI | `AbstractUiTest` | `@pytest.mark.frontend` |

## Reference Paths

- Test example: `acceptance/tests/backend/{feature}/test_{feature}_acceptance.py`
- Base class: `acceptance/tests/backend/abstract_backend_test.py`
- Statements example: `acceptance/statements/{feature}_statements.py`
- Client: `acceptance/clients/application/application_client.py`
- TestData: `acceptance/statements/test_data.py`

## Key Paths

- Backend tests: `acceptance/tests/backend/`
- Statements: `acceptance/statements/`
- Client: `acceptance/clients/application/`
- DTOs: `acceptance/clients/application/dto/`
