# Story 17: Export document — Carryover

Enduring quirks and invariants promoted from completed scenarios. Read by `/continue` on resume.

## Codebase Quirk: baked backend image must be rebuilt before acceptance runs
**Quirk:** The compose `backend` service runs a baked image (source copied in at build, no volume mount / reload), so freshly-committed backend code is invisible to a running container until it is rebuilt.
**Where:** infra/docker-compose.yml `backend` service.
**Implication:** Every green-acceptance / green-selenium step must `docker compose -f infra/docker-compose.yml up -d --build backend` and wait for a healthy recreate (~30s) before running the acceptance test — otherwise a correct green reads as RED against stale code.
**From:** scenario 1.1 (export-nonexistent-refused)
