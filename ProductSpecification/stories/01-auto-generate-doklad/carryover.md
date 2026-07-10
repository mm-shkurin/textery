# Story 1: Auto-generate: доклад — Carryover

## Quirk: local backend acceptance runs need manual uvicorn + docker-compose postgres, not a scripts/ dir
**Quirk:** No `infrastructure/scripts/` directory exists in this repo (the `.claude/skills/run-backend` skill still references it) — local backend acceptance runs require starting `uvicorn` directly against a manually-started `infra/docker-compose.yml` Postgres, with `DATABASE_URL`/`GENERATION_PROVIDER=fake` set by hand.
**Where:** Repo root; `infra/` is the real IaC directory, `infrastructure/` only holds `agent-progress.log`.
**Implication:** A stray `uvicorn` process left listening on `BACKEND_PORT` across a session survives a plain `pkill -f "uvicorn main:app"` (Windows Python processes don't match that pattern) — free the port with `netstat -ano | grep :{port}` + `taskkill //F //PID {pid}` on the specific PID before restarting. Docker Desktop restarting mid-session also drops `infra-postgres-1` silently — recheck `docker ps` before assuming the DB is still up.
**From:** scenario 2.1 (valid-request-accepted-and-queued)

## Deferred: frontend CI workflow and oxlint rule expansion
**Quirk:** No CI ever wired up for `frontend/` — `npm run lint`/`tsc -b`/`npm run test`
only run manually. `.oxlintrc.json` only has 2 rules enabled.
**Where:** repo-wide — no `.github/workflows/` and no CI runner pattern under
`infrastructure/` for the frontend yet.
**Implication:** flagged, not fixed, during the 2026-07-10 audit-remediation pass
(user said "without infra for now" — see `frontend-audit-remediation.md`). When this
gets picked up, propose the IaC addition per `.claude/rules/infrastructure.md` rather
than dropping an ad-hoc `.github/workflows/*.yml`.
**From:** frontend-audit-remediation.md, 2026-07-10
