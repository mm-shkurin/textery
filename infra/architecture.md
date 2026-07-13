# Architecture — deployable infra

Scope: `infra/docker-compose.yml`. All services are real (no placeholders/mocks):
Postgres, Redis, the real FastAPI backend (migrated via Alembic on boot), and the
real React/Vite frontend (built and served by nginx). No cloud/Terraform
involvement yet (dormant — see `.memory-bank/index.md`). Exposed Postgres/Redis
host ports still need revisiting before this is reused as a public-facing
production template (see Deploy notes below).

## Topology

Four services on the compose default network, resolving each other by service
DNS name:

```
frontend (nginx, real Vite build)     backend (FastAPI, real app)
        |  depends_on: backend               |
        v (start-order only)                 v
                                        depends_on: postgres, redis (service_healthy)
                                              |
                                    +---------+---------+
                                    v                   v
                              postgres:5432        redis:6379
```

- `redis` is provisioned and reachable (`REDIS_URL` wired into `backend`) ahead
  of the planned `arq` background worker (see `ProductSpecification/technology.md`)
  — no `worker` service exists yet because there's no arq code to run. Add it
  back (same backend image, `arq worker.WorkerSettings` command) once that
  code lands.
- No `container_name` on any service, and all host ports are `${VAR}`-driven —
  both avoid collisions when multiple worktrees/sessions run this compose file
  on the same host simultaneously.
- No custom network block: the compose default network is enough since nothing
  needs isolation yet.

## Port map

All host-side ports come from `infra/.env` (see `infra/.env.example` for the
full list with dummy defaults). Container-internal ports are fixed.

| Service  | Container port | Host port var   | Default |
|----------|-----------------|------------------|---------|
| postgres | 5432            | `POSTGRES_PORT`  | 5432    |
| redis    | 6379            | `REDIS_PORT`     | 6379    |
| backend  | 8000            | `BACKEND_PORT`   | 8000    |
| frontend | 80              | `FRONTEND_PORT`  | 80      |

## Env var contract

- `infra/.env` (gitignored, copy from `infra/.env.example`): `POSTGRES_USER`,
  `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`, `REDIS_PORT`,
  `BACKEND_PORT`, `FRONTEND_PORT`.
- `DATABASE_URL` and `REDIS_URL` are **not** read from `infra/.env` — they're
  composed inside `docker-compose.yml`'s `environment:` block from the Postgres
  vars plus the in-network service DNS names (`postgres`, `redis`), because
  `.env` files are parsed literally by compose (no recursive `${...}`
  interpolation inside `.env` itself).
- `backend/.env` (gitignored, owned by the backend module): holds
  `GIGACHAT_CREDENTIALS`, `GIGACHAT_CA_BUNDLE`, `GENERATION_PROVIDER` and any
  other backend-only secrets (see `backend/.env.example`). Wired into
  `backend` via `env_file: ../backend/.env` with `required: false`. This stays
  local-`.env`-only per the existing Memory Bank decision — no cloud secret
  store until a cloud provider is chosen.

## Build

Build context for both `backend` and `frontend` is the **repo root** (`..`
relative to `infra/`), because each Dockerfile needs to `COPY` its module tree
(`backend/domain`, `backend/usecase`, `backend/adapters`, `backend/application`
for the backend; the whole `frontend/` tree for the frontend). The root
`.dockerignore` excludes VCS/harness/cache directories from both build
contexts.

- **`infra/docker/backend.Dockerfile`**: `python:3.12-slim`, installs
  `backend/requirements.txt`, copies all backend module `src/` trees. `CMD`
  runs Alembic migrations (`cd backend/adapters/db && alembic upgrade head`)
  then serves with `uvicorn app.main:app --app-dir backend/application/src`.
  `HEALTHCHECK` hits `/openapi.json`.
- **`infra/docker/frontend.Dockerfile`**: multi-stage — `node:20-alpine` build
  stage runs `npm ci && npm run build`, then `nginx:alpine` serves the built
  `dist/` via `infra/docker/nginx/frontend.conf` (SPA fallback to
  `index.html`).

## Deploy notes

This compose file is usable as-is for a single-host deploy (`docker compose
-f infra/docker-compose.yml up -d --build`), given a populated `infra/.env`
and `backend/.env` on that host. Before exposing it publicly:

- Postgres/Redis host port mappings (`ports:`) should be dropped or bound to
  `127.0.0.1` — they're only exposed today for local debugging/migration
  access, not for any external caller.
- `backend/.env` and `infra/.env` must be provisioned on the deploy host
  out-of-band (no secret store wired yet — see Env var contract above).
- Add the `worker` service back once `arq` background-job code exists (see
  `ProductSpecification/technology.md`); `redis` is already provisioned for it.

## Validated

- `docker compose -f infra/docker-compose.yml config` — no errors.
- `docker compose up -d --build` — all 4 services reach running/healthy, no
  crash-loop; Alembic applies the `generations` table migration on backend
  boot.
- From inside `backend`: `pg_isready -h postgres` → `accepting connections`;
  reaches `redis:6379`.
- Frontend served at `FRONTEND_PORT`, backend API at `BACKEND_PORT`.
- Postgres data survives `docker compose down` (no `-v`) + `up -d` via the
  named `postgres_data` volume.
