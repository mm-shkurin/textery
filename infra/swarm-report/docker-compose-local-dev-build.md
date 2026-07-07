# Build: docker-compose for local dev   (slug: docker-compose-local-dev)

## Agent: devops (single scope — all affected files were infra/devops)

### Changed files
- `infra/docker-compose.yml` (new) — 5 services: postgres, redis, backend, worker, frontend
- `infra/docker/backend.Dockerfile` (new) — TEMP placeholder, python:3.12-slim
- `infra/docker/frontend.Dockerfile` (new) — TEMP placeholder, nginx:alpine
- `infra/docker/frontend-static/index.html` (new) — static "coming soon" stub
- `infra/.dockerignore` (new)
- `infra/.env.example` (new) — documents all compose-consumed vars
- `infra/architecture.md` (new) — topology, port map, env var contract
- `infra/.memory-bank/index.md` (updated) — points at architecture.md, provisioning note removed
- `infra/.memory-bank/open-questions.md` (new)

### Tests / validation — real output
- `docker compose -f infra/docker-compose.yml config` — clean, no interpolation errors.
- `docker compose up -d --build` — all 5 images built, all containers started; postgres/redis reported healthy before backend/worker started (`depends_on: condition: service_healthy` honored).
- `docker compose ps` — backend Up (healthy), frontend Up, postgres Up (healthy), redis Up (healthy), worker Up. No crash-loops.
- Connectivity from inside `backend`: `pg_isready -h postgres` → "accepting connections"; `redis-cli -h redis ping` → "PONG".
- Persistence: wrote a row to a test table, `down` (no `-v`), `up -d`, row still present via named `postgres_data` volume.
- Final `down -v` — full teardown, no stray files left, git status clean.

**Result: PASS.**

### Cross-layer / deviations from plan (documented in architecture.md too)
1. `env_file: ../backend/.env` uses Compose's `required: false` — `backend/.env` doesn't exist yet (backend/ is empty), so this is needed for `up` to succeed today. Real key still loads automatically once the backend session creates that file.
2. `DATABASE_URL` / `REDIS_URL` are composed in `docker-compose.yml`'s `environment:` block, not in `.env` — plain `.env` files don't support compose's `${...}` interpolation recursively. Documented in `.env.example` and `architecture.md`.
3. `worker` disables the inherited image healthcheck (`healthcheck: disable: true`) since its placeholder `tail -f /dev/null` command doesn't open the HTTP port the backend image's healthcheck probes.
4. The agent used non-default ports (18000/18080/15432/16379) in its own local `.env` only, to avoid colliding with unrelated containers already running on the host during validation. `infra/.env.example` still documents the plan's intended defaults (8000/80/5432/6379) — no change needed on your end.

No blockers.
