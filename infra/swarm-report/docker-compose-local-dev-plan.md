# Plan: docker-compose for local dev: backend + postgres + redis + frontend placeholder   (slug: docker-compose-local-dev)

## TL;DR
Add `infra/docker-compose.yml` wiring 5 services — `backend`, `worker` (arq, separate
process from backend — required, not optional), `postgres`, `redis`, `frontend` — for
local dev only. `backend/` and `frontend/` are currently empty, so `backend`/`worker`/
`frontend` build from placeholder Dockerfiles (marked TEMP) until real code lands from
their own sessions. All ports/credentials come from `infra/.env` (gitignored, an
`infra/.env.example` is committed) — no literals in compose, no cloud secret store
(per Memory Bank decision). No cloud/Terraform involvement.

## Acceptance criteria
- `docker compose -f infra/docker-compose.yml config` validates with no errors.
- `docker compose -f infra/docker-compose.yml up -d` starts 5 services: `backend`,
  `worker`, `postgres`, `redis`, `frontend` — none crash-loop.
- `postgres` and `redis` each have a healthcheck; `backend` and `worker` use
  `depends_on: condition: service_healthy` on both.
- `backend`/`worker` reach `postgres:5432` and `redis:6379` by service DNS name from
  inside their container (verified via `pg_isready` / `redis-cli ping`).
- Postgres data survives `docker compose down` (no `-v`) + `up -d` via a named volume.
- No hardcoded ports or credentials in `docker-compose.yml` — all via `${VAR}` sourced
  from `infra/.env`; `infra/.env.example` documents every var with dummy values.
- No `container_name` set on any service (avoids collision across parallel
  worktrees/sessions on the same host); host ports configurable via `infra/.env` for
  the same reason.
- `frontend` service is explicitly a static placeholder (nginx serving a stub page) —
  no framework scaffolding performed by this task.
- `infra/architecture.md` documents the topology, port map, env var contract, and
  which pieces are TEMP placeholders pending real backend/frontend code.
- `infra/.memory-bank/index.md` updated: architecture.md now exists, docker-compose
  open question resolved.

## Plan
1. Create `infra/.env.example` — documents every compose-consumed var with dummy
   values: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`,
   `REDIS_PORT`, `BACKEND_PORT`, `FRONTEND_PORT`, `DATABASE_URL` (or composed from the
   Postgres vars), `REDIS_URL`. Note in-file that `ANTHROPIC_API_KEY` lives in
   `backend/.env` (consumed by `backend`/`worker` via `env_file`), not here.
2. Note precondition (not created by this task, contains a secret): a local
   `infra/.env` copied from `.env.example` with real values, and `backend/.env`
   containing `ANTHROPIC_API_KEY`. Confirm both are gitignored.
3. Create `infra/docker/backend.Dockerfile` — placeholder: `python:3.12-slim`,
   `WORKDIR /app`, no `COPY` of nonexistent code, `CMD` a placeholder that keeps the
   container alive and satisfies a trivial healthcheck (e.g. minimal `http.server`).
   Comment marking it TEMP, to be replaced once FastAPI code lands.
4. Create `infra/docker/frontend.Dockerfile` — placeholder: `nginx:alpine` serving a
   static "Textery — frontend coming soon" page. Comment marking it TEMP, to be
   replaced once the React app lands. No framework scaffolding here.
5. Add `infra/.dockerignore` (or per-Dockerfile context) excluding `.git`,
   `.memory-bank`, `swarm-report`, `node_modules`, `.venv`, `__pycache__`.
6. Create `infra/docker-compose.yml`:
   - `postgres`: `postgres:16-alpine`, env `POSTGRES_USER/PASSWORD/DB` from
     `infra/.env`, named volume `postgres_data:/var/lib/postgresql/data`, host port
     `${POSTGRES_PORT}:5432`, healthcheck `pg_isready`.
   - `redis`: `redis:7-alpine`, host port `${REDIS_PORT}:6379`, healthcheck
     `redis-cli ping`.
   - `backend`: build from `docker/backend.Dockerfile`, `env_file: ../backend/.env`,
     env vars `DATABASE_URL`/`REDIS_URL` built from service DNS names (`postgres`,
     `redis`), `depends_on` postgres+redis with `condition: service_healthy`, host
     port `${BACKEND_PORT}:8000`. No `container_name`.
   - `worker`: same build (`docker/backend.Dockerfile`) and `env_file` as `backend`,
     but a distinct `CMD`/`command` placeholder for the future `arq worker.WorkerSettings`
     entrypoint — a separate process from `backend`, not folded into it, since arq
     workers and the API process have different lifecycles. Same `depends_on`
     conditions as `backend`. No host port needed. No `container_name`.
   - `frontend`: build from `docker/frontend.Dockerfile`, host port
     `${FRONTEND_PORT}:80`, plain `depends_on: backend` (start-order only). No
     `container_name`.
   - Rely on the default compose network (all services resolve each other by name);
     no need for a custom network block unless isolation is later required.
   - Top-level `volumes: postgres_data:`.
7. Validate: `docker compose -f infra/docker-compose.yml config`.
8. Bring up: `docker compose -f infra/docker-compose.yml up -d`; `docker compose ps`
   to confirm all 5 healthy/running.
9. Connectivity check: exec into `backend`, run `pg_isready -h postgres` and
   `redis-cli -h redis ping`; confirm both succeed.
10. Persistence check: write a test row to Postgres, `docker compose down` (no `-v`),
    `up -d` again, confirm the row is still present.
11. Teardown for the session: `docker compose down` (no `-v`, keep the dev volume).
12. Write `infra/architecture.md`: the 5-service topology, port map, env var
    contract, and an explicit "TEMP placeholder" callout for `backend`/`worker`/
    `frontend` Dockerfiles — what has to change once real code lands (real
    requirements/Dockerfile, real `arq` command, real frontend build, and — per
    skeptic MED finding — bind-mounting source with an anonymous-volume overlay for
    `.venv`/`node_modules` once those directories exist, so host deps don't shadow
    container deps).
13. Update `infra/.memory-bank/index.md`: point "Where to look" at the new
    `architecture.md`, remove the "nothing provisioned yet" note, mark the
    docker-compose open question resolved in `open-questions.md` (create/update that
    file if referenced but missing).

## Tests
- `docker compose -f infra/docker-compose.yml config` — no syntax/interpolation errors.
- `docker compose -f infra/docker-compose.yml up -d` — 5 containers reach
  running/healthy within ~30s, none crash-loop.
- Connectivity: `backend` → `postgres:5432` (`pg_isready`) and → `redis:6379`
  (`redis-cli ping`) both succeed.
- Volume persistence: write to Postgres, `down` (no `-v`) + `up -d`, data still
  present.
- Final cleanup: `docker compose down -v` only at the very end, to fully reset —
  not used for the persistence test itself.

## Blockers
None outstanding — all skeptic HIGH findings are folded into the plan above
(placeholder Dockerfiles so `up` succeeds today; `infra/.env`-sourced ports/creds,
no literals; a distinct `worker` service for arq). All MED findings addressed
(healthchecks + `service_healthy` depends_on; no `container_name` + configurable host
ports to avoid cross-session collisions on shared host; named Postgres volume; bind-
mount/anonymous-volume overlay strategy documented for when real code lands). LOW
findings addressed (pinned image tags; frontend placeholder explicitly scoped to a
static nginx page, no scaffolding; `.dockerignore` added).

## Out of scope
- Any cloud/deploy config (Terraform, Yandex Cloud) — dormant per Memory Bank.
- Real backend/frontend application code — separate sessions own those.
- CI/CD pipeline wiring.
- Secret management beyond local `.env` files (no Lockbox/vault) — Anthropic API key
  stays in `backend/.env` per existing decision.
- prod-copy or production compose variants; this file is local-dev only and must not
  be reused as a template for a prod compose without revisiting the exposed
  Postgres/Redis host ports.
- TLS/reverse proxy for local dev.
- Acceptance/E2E test wiring (separate, root-level module/harness).

## Assumptions
- Postgres 16 and Redis 7 are acceptable versions (Memory Bank silent on this).
- Compose file lives at `infra/docker-compose.yml` (infra subtree owns delivery per
  Memory Bank), not repo root.
- Default host ports (documented in `.env.example`, overridable): backend 8000,
  frontend 80, postgres 5432, redis 6379 — no existing convention found.
- The arq worker placeholder command can be a simple long-running stub (e.g.
  `tail -f /dev/null`) until real `arq` code exists — it only needs to prove the
  service boots and reaches Postgres/Redis, not run real jobs yet.
- "docker-compose for local dev" excludes acceptance/E2E test wiring.
