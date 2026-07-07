# Controller Implementation Template -- Python/FastAPI/Hexagonal

> Universal rules: `.claude/templates/tdd/green-rest.md`

## Tech-Specific Rules

- Routes are `APIRouter` handler functions, not classes. Dependencies (usecase instances) are injected via `Depends(get_{feature}_usecase)` where the provider function is defined in the composition root (`backend/application/container.py`).
- Handler functions are `async def` and `await` the usecase call directly.

## Reference (read before generating)

- Router example: `backend/adapters/rest/src/router/{feature}/{feature}_router.py`
- Request DTO example: `backend/adapters/rest/src/dto/{feature}/{feature}_request_dto.py`
- Response DTO example: `backend/adapters/rest/src/dto/{feature}/{feature}_response_dto.py`
- Composition root providers: `backend/application/container.py`

## Key Paths

- Routers: `backend/adapters/rest/src/router/`
- DTOs: `backend/adapters/rest/src/dto/`
- Tests: `backend/adapters/rest/tests/router/`
