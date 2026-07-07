# Architecture — local dev delivery

Scope: `infra/docker-compose.yml`, local dev only. No cloud/Terraform involvement
(dormant — see `.memory-bank/index.md`). Not a template for prod-copy/production —
revisit exposed Postgres/Redis host ports before reusing it there.

## Topology

Five services on the compose default network, resolving each other by service
DNS name:

```
frontend (nginx, TEMP static)         backend (FastAPI, TEMP http.server)
        |  depends_on: backend               |
        v (start-order only)                 v
        [ no runtime call wired yet ]   depends_on: postgres, redis (service_healthy)
                                              |
                                    +---------+---------+
                                    v                   v
                              postgres:5432        redis:6379
                                    ^                   ^
                                    |                   |
                              worker (arq, TEMP tail -f /dev/null)
                              depends_on: postgres, redis (service_healthy)
```

- `worker` is a **separate process** from `backend`, built from the same image,
  because the future arq worker and the API process have different lifecycles
  (arq workers don't serve HTTP, restart independently, scale independently).
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
| worker   | (none exposed)  | —                | —       |
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
- `backend/.env` (gitignored, owned by the backend session): holds
  `OPENROUTER_API_KEY`/`OPENROUTER_MODEL` and any other backend-only secrets
  (see `backend/.env.example`). Wired into `backend`/`worker` via
  `env_file: ../backend/.env` with `required: false`. This stays
  local-`.env`-only per the existing Memory Bank decision — no cloud secret
  store until a cloud provider is chosen.

## Build context

`backend` and `worker` build from `infra/docker/backend.Dockerfile`; `frontend`
builds from `infra/docker/frontend.Dockerfile`. Both use build context `infra/`
(the compose file's own directory), so `infra/.dockerignore` (excluding `.git`,
`.memory-bank`, `swarm-report`, `node_modules`, `.venv`, `__pycache__`) applies
to both builds.

## TEMP placeholders — what changes once real code lands

`backend/` and `frontend/` are empty today; real code lands from separate
sessions. Until then:

- **`infra/docker/backend.Dockerfile`** (used by both `backend` and `worker`):
  `python:3.12-slim` running `python3 -m http.server 8000` with a trivial
  `HEALTHCHECK` hitting that same port. No dependency install, no app code.
  Replace with: install real deps (requirements/poetry/uv), and change
  `backend`'s `CMD`/compose `command` to
  `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- **`worker` service** (`docker-compose.yml`): `command: ["tail", "-f", "/dev/null"]`
  with `healthcheck: disable: true` (the inherited image healthcheck probes an
  HTTP port this command never opens). Replace with the real
  `arq worker.WorkerSettings` entrypoint and re-enable/rewrite the healthcheck
  once the worker exposes something to probe (or leave it disabled if arq
  workers stay unprobed — revisit then).
- **`infra/docker/frontend.Dockerfile`**: `nginx:alpine` serving a single static
  `docker/frontend-static/index.html` stub. No framework scaffolding was done
  here. Replace with a real multi-stage build (Node build stage → nginx serve
  stage) once the React app exists.
- **Bind mounts for local dev** (not yet wired — nothing to mount while
  `backend/`/`frontend/` are empty): once real code lands, prefer bind-mounting
  `../backend` and `../frontend` into their containers for live-reload dev,
  with an **anonymous volume overlay** on `.venv` (backend) and `node_modules`
  (frontend) so host-installed dependencies don't shadow the
  container-installed ones, e.g.:
  ```yaml
  volumes:
    - ../backend:/app
    - /app/.venv        # anonymous volume: container's own venv wins
  ```
  and equivalently `- /app/node_modules` for `frontend`.

## Validated (this task)

- `docker compose -f infra/docker-compose.yml config` — no errors.
- `docker compose up -d` — all 5 services reach running/healthy, no crash-loop.
- From inside `backend`: `pg_isready -h postgres` → `accepting connections`;
  `redis-cli -h redis ping` → `PONG` (client tools installed ad hoc for the
  check; not baked into the placeholder image).
- Wrote a row to Postgres, `docker compose down` (no `-v`), `up -d` again — row
  still present via the named `postgres_data` volume.
- Final `docker compose down -v` used only at the very end, to fully reset.
