# Scenario 2.1: Valid request is accepted and queued without waiting on the LLM call — Journey Summary

## green-adapter rest (2026-07-10)

**Decision:** Extended `GenerationCreatedDto` to echo `topic`/`volume_pages`/`document_type` back in the POST response, matching what `assert_generation_created_pending` in `acceptance/statements/generation_statements.py` already asserted.
**Why:** The evening-demo implementation (known-debt #10) shipped a narrower DTO (`generation_id`/`status`/`created_at` only) than the pre-existing red-acceptance test expected — a real regression, not a stale test. Per TDD rules the pre-existing test is authoritative.
**Where applied:** `backend/adapters/rest/src/dto/generation/generation_response_dto.py`.

## green-acceptance (2026-07-10)

**Quirk:** No `infrastructure/scripts/` directory exists in this repo (the `.claude/skills/run-backend` skill still references it) — local backend acceptance runs require starting `uvicorn` directly against a manually-started `infra/docker-compose.yml` Postgres, with `DATABASE_URL`/`GENERATION_PROVIDER=fake` set by hand.
**Where:** Repo root; `infra/` is the real IaC directory, `infrastructure/` only holds `agent-progress.log`.
**Implication:** A stray `uvicorn` process left listening on `BACKEND_PORT` across a session survives a plain `pkill -f "uvicorn main:app"` (Windows Python processes don't match that pattern) — free the port with `netstat -ano | grep :{port}` + `taskkill //F //PID {pid}` on the specific PID before restarting. Docker Desktop restarting mid-session also drops `infra-postgres-1` silently — recheck `docker ps` before assuming the DB is still up.
