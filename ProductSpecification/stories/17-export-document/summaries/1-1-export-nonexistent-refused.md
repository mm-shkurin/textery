# Scenario 1.1: Export of a non-existent document is refused — Journey Summary

## green-acceptance (2026-07-26)

**Quirk:** The compose `backend` service runs a **baked image** (build context copies source in; no volume mount, no reload), so a freshly-committed route is invisible until the container is rebuilt — the acceptance test kept getting Starlette's default `{'detail':'Not Found'}` against a container that had been `Up 2 days`.
**Where:** infra/docker-compose.yml `backend` service (build: infra/docker/backend.Dockerfile).
**Implication:** Before running any acceptance test that exercises new backend code, run `docker compose -f infra/docker-compose.yml up -d --build backend` and wait for the container to recreate + report healthy (~30s); a stale container makes a green step read as RED.
