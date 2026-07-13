# Python/FastAPI/Hexagonal Infrastructure Idioms

Tech binding for `infrastructure.md`. Load alongside the universal rules.

## Health Check

- FastAPI health endpoint: `source infra/.env && curl http://localhost:$BACKEND_PORT/health`

## Process Safety

- Never kill by executable name: `taskkill //IM python.exe` — use port-based stop scripts instead.
- Never run `pkill python` / `pkill uvicorn` or `killall python` — it kills ALL Python processes system-wide, breaking parallel sessions.
- The `arq` worker runs as a **separate process** from the `uvicorn` API process (`arq backend.application.worker.WorkerSettings`). Stop scripts must target its own PID, not just the API server's.

## Config Fallback Syntax

Each file type has its own fallback pattern:
- Python (`pydantic-settings` / `os.environ`): `os.environ.get('VAR', 'fallback')`
- Docker Compose, shell scripts: `${VAR:-fallback}` (colon-dash)

## Acceptance Tests

- `test-acceptance.sh` exports env vars then runs pytest: `pytest acceptance/` or `pytest acceptance/ -m backend` / `pytest acceptance/ -m frontend`.

## Local Infrastructure Dependencies

- PostgreSQL and Redis (for `arq`) are provisioned by a separate infra session's `docker-compose` — this profile's skills/agents connect to them via `infra/.env` ports and never attempt to start/stop those containers themselves.
- Alembic migrations run against the same PostgreSQL instance: `alembic upgrade head` before backend startup in local dev.
