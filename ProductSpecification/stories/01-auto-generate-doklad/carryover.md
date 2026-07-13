# Story 1: Auto-generate: доклад — Carryover

## Quirk: local backend acceptance runs need manual uvicorn + docker-compose postgres, not a scripts/ dir
**Quirk:** No `infrastructure/scripts/` directory exists in this repo (the `.claude/skills/run-backend` skill still references it) — local backend acceptance runs require starting `uvicorn` directly against a manually-started `infra/docker-compose.yml` Postgres, with `DATABASE_URL`/`GENERATION_PROVIDER=fake` set by hand.
**Where:** Repo root; `infra/` is the real IaC directory, `infrastructure/` only holds `agent-progress.log`.
**Implication:** A stray `uvicorn` process left listening on `BACKEND_PORT` across a session survives a plain `pkill -f "uvicorn main:app"` (Windows Python processes don't match that pattern) — free the port with `netstat -ano | grep :{port}` + `taskkill //F //PID {pid}` on the specific PID before restarting. Docker Desktop restarting mid-session also drops `infra-postgres-1` silently — recheck `docker ps` before assuming the DB is still up.
**From:** scenario 2.1 (valid-request-accepted-and-queued)

## Resolved: frontend CI workflow now exists
**Quirk:** was flagged deferred across two 2026-07-10 passes, then added in a third
pass the same day once the user confirmed the frontend was already containerized
(`infra/docker/frontend.Dockerfile` + `infra/docker-compose.yml`, same repo — the
`gitverse-backend`/`gitverse-frontend` remotes are unrelated split-repo mirrors, not
a separate infra repo).
**Where:** `.github/workflows/frontend-ci.yml` — `lint-test-build` job
(`npm ci`/`lint`/`test`/`build`) + `docker-image` job (builds
`infra/docker/frontend.Dockerfile` from repo root to catch Dockerfile drift).
**Implication:** if this repo's remote strategy changes (e.g. CI needs to run on
`gitverse` instead of/in addition to GitHub), the workflow will need porting to
whatever CI the new host supports — GitHub Actions syntax doesn't transfer.
**From:** frontend-audit-remediation.md, 2026-07-10
