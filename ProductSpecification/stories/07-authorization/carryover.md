## Quirk: shared local Postgres volume can be stamped by another worktree's migrations
**Quirk:** The shared local dev Postgres volume can be stamped with an `alembic_version` from a different worktree/branch's migration chain, causing backend startup to fail with "Can't locate revision".
**Where:** `infra/docker-compose.yml` postgres volume (`infra_postgres_data`), shared across worktrees on this host.
**Implication:** If backend fails to start with an alembic revision-not-found error, reset the local volume (`docker volume rm infra_postgres_data`) rather than debugging migrations — this is a shared-host artifact, not a code bug.
**From:** scenario 2.2 (verify-code-auto-advance-focus)

## Quirk: multiple frontend-serving processes can coexist on this host
**Quirk:** A stray `npm run dev` from another worktree can squat port 5173, and the docker frontend container (port 80) may be running a stale build that predates current source.
**Where:** Selenium acceptance test `app_url` fixture (`acceptance/conftest.py`), `FRONTEND_PORT` resolution.
**Implication:** Before trusting a Selenium test's PASS/FAIL, verify `FRONTEND_PORT` via `infra/.env` and rebuild the docker frontend container (`docker compose up -d --build frontend`) if the port-80 build looks stale, or run this worktree's own `npx vite --port <free>` and pass that `FRONTEND_PORT` explicitly.
**From:** scenario 2.2 (verify-code-auto-advance-focus)
