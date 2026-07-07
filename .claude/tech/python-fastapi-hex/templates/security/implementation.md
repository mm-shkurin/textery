# Security Adapter Implementation Template

## Product Context

Needed from story 7 (Authorization) onward -- not for story 1-4's anonymous generation
flow. Covers email+password (mocked verification code) plus Yandex ID and VK ID OAuth.
**No Google** anywhere in this project.

## Rules

- Pure unit tests in test code -- no FastAPI app context needed for the JWT/OAuth logic itself
- Constructor injection via `__init__` parameters in production code
- JWT operations via `JwtService` (using `PyJWT`), configuration via `JwtConfig` dataclass
- OAuth token exchange (Yandex ID, VK ID): plain `httpx.AsyncClient` calls to each
  provider's authorization-code-exchange endpoint -- no heavyweight OAuth library needed,
  both providers use a standard authorization-code flow
- Use `Clock` protocol for time operations (inject `FakeClock` in tests)
- FastAPI integration: a `get_current_user` dependency function (not middleware) wraps
  `JwtService.verify()` and is applied per-route via `Depends(get_current_user)`

## Reference (read before generating)

- JWT service: `backend/adapters/security/src/jwt_service.py`
- Config: `backend/adapters/security/src/jwt_config.py`
- Auth dependency: `backend/adapters/security/src/dependency/current_user.py`
- OAuth clients: `backend/adapters/security/src/oauth/yandex_id_client.py`, `backend/adapters/security/src/oauth/vk_id_client.py`

## Key Paths

- Production: `backend/adapters/security/src/`
- Tests: `backend/adapters/security/tests/`
