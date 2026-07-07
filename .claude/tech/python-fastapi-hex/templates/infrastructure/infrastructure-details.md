# Infrastructure Details

Detailed reference for local development infrastructure.
For rules and quick reference, see `.claude/rules/infrastructure.md`.

## Local Development

All services run via Docker Compose, provisioned by a **separate infra session**
(`infra/` subtree, its own harness — see `infra/.memory-bank/index.md`). This backend
profile's skills/agents only ever *connect* to these services; they never start, stop,
or modify the compose file themselves (see `.claude/rules/infrastructure.md`,
Destructive-Action Guardrails).

### Topology (`infra/docker-compose.yml`, see `infra/architecture.md` for the full doc)

Five services on the compose default network:

```
frontend (nginx)          backend (FastAPI/uvicorn)
                                |
                     depends_on: postgres, redis (service_healthy)
                                |
                      +---------+---------+
                      v                   v
                postgres:5432        redis:6379
                      ^                   ^
                      |                   |
                worker (arq, separate process from backend)
                depends_on: postgres, redis (service_healthy)
```

- `worker` runs the `arq` task queue as its **own process**, built from the same image
  as `backend` — it never serves HTTP, restarts/scales independently of the API process.
- No service is started/stopped by this profile's scripts — only by the `infra/` harness.

### Port Configuration

Host-side ports come from `infra/.env` (see `infra/.env.example`); container-internal
ports are fixed:

| Service  | Container port | Host port var   | Default |
|----------|-----------------|------------------|---------|
| postgres | 5432            | `POSTGRES_PORT`  | 5432    |
| redis    | 6379            | `REDIS_PORT`     | 6379    |
| backend  | 8000            | `BACKEND_PORT`   | 8000    |
| worker   | (none exposed)  | —                | —       |
| frontend | 80              | `FRONTEND_PORT`  | 80      |

### Env Var Contract

- `DATABASE_URL` and `REDIS_URL` are composed inside `docker-compose.yml`'s
  `environment:` block from the Postgres vars plus in-network service DNS names
  (`postgres`, `redis`) — never read `POSTGRES_PORT`/`REDIS_PORT` directly from
  application code, only the composed `DATABASE_URL`/`REDIS_URL`.
- `backend/.env` (gitignored, owned by the backend session): `ANTHROPIC_API_KEY` and any
  other backend-only secret. Wired into `backend`/`worker` via `env_file` in
  `docker-compose.yml`.

### Service Scripts

| Script | Purpose |
|--------|---------|
| `run-backend.sh` | Start FastAPI backend (`uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT`) |
| `run-frontend.sh` | Start Vite dev server |
| `stop-backend.sh` | Stop backend by port PID |
| `test-acceptance.sh` | Run acceptance tests with correct env vars |

`run-infra.sh`/`stop-infra.sh` (Docker Compose start/stop) belong to the `infra/`
session, not this profile — see `.claude/rules/infrastructure.md`.

### Network Flow (Local)

```
Browser -> frontend dev server (FRONTEND_PORT)
       -> /api/ -> backend (BACKEND_PORT)

Backend:
  -> Database (via DATABASE_URL, resolves to postgres:5432 in-network)
  -> Redis / arq queue (via REDIS_URL, resolves to redis:6379 in-network)
  -> Anthropic API (external, via ANTHROPIC_API_KEY from backend/.env)

Worker (arq):
  -> Redis (job queue)
  -> Database (writes generation/document results)
  -> Anthropic API (the actual generation call)
```

## Migrations

`alembic upgrade head` must run against `DATABASE_URL` before backend/worker startup in
local dev — not baked into the placeholder image yet (see `infra/architecture.md`'s TEMP
placeholder notes; this runs once `backend/` has real code).
