# Story 1: Auto-generate: доклад — Carryover

## Quirk: local backend acceptance runs need manual uvicorn + docker-compose postgres, not a scripts/ dir
**Quirk:** No `infrastructure/scripts/` directory exists in this repo (the `.claude/skills/run-backend` skill still references it) — local backend acceptance runs require starting `uvicorn` directly against a manually-started `infra/docker-compose.yml` Postgres, with `DATABASE_URL`/`GENERATION_PROVIDER=fake` set by hand.
**Where:** Repo root; `infra/` is the real IaC directory, `infrastructure/` only holds `agent-progress.log`.
**Implication:** A stray `uvicorn` process left listening on `BACKEND_PORT` across a session survives a plain `pkill -f "uvicorn main:app"` (Windows Python processes don't match that pattern) — free the port with `netstat -ano | grep :{port}` + `taskkill //F //PID {pid}` on the specific PID before restarting. Docker Desktop restarting mid-session also drops `infra-postgres-1` silently — recheck `docker ps` before assuming the DB is still up.
**From:** scenario 2.1 (valid-request-accepted-and-queued)
