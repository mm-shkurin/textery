---
name: run-backend
description: Run the backend application. Use when user wants to start the backend server or mentions /run-backend command.
---

# Run Backend Application

## Prerequisite

Ensure `infra/.env` and `backend/.env` exist (copy from their `.env.example` if not —
there is no generator script; see `infra/architecture.md`).

## Action

Start the backend service via the real compose stack (all services are real, no
placeholders — see `infra/architecture.md`):
```bash
docker compose -f infra/docker-compose.yml up -d --build backend
```

`backend` depends on `postgres`/`redis` reaching `service_healthy`, so compose brings
those up first automatically. Use `run_in_background: true` if you additionally want to
tail logs (`docker compose -f infra/docker-compose.yml logs -f backend`).

Port comes from `BACKEND_PORT` in `infra/.env` (default `8000`).

## Output

Report startup status. Server runs at `http://localhost:{BACKEND_PORT}` (from `infra/.env`).
