# Story 7: Authorization — Carryover

Quirk and enduring-invariant entries promoted from completed scenario summaries. Backend and frontend both read this file.

## Quirk: adapters-discovery does not catch an unmounted router

**Quirk:** `green-adapter rest` wired the auth router's DI stub (`get_register_user_usecase`) but never registered `auth_router` on the FastAPI app itself (`backend/application/src/app/main.py`) — only `generation_router` was included, so the acceptance test 404'd until a later step added `app.include_router(auth_router)` and a `create_register_user()` factory in `container.py`.
**Where:** `backend/application/src/app/main.py`, `backend/application/src/app/container.py`.
**Implication:** `adapters-discovery`'s ports/exceptions/response-shape checklist does not catch "router not mounted on the app" — future scenarios adding new routers must verify `main.py` wiring explicitly, not just the router module and its DI stub.
**From:** scenario 1.1 (reject-malformed-email)

## Quirk: acceptance client's BACKEND_PORT defaults to 8000, not the compose-mapped port

**Quirk:** The acceptance HTTP client (`acceptance/clients/application/application_client.py`) reads `BACKEND_PORT` from the shell environment, defaulting to 8000, but the docker-compose backend service maps to host port 8100 (`infra/.env`). Running pytest without `BACKEND_PORT=8100` set silently hits a non-existent/wrong service and produces a misleading 404.
**Where:** `acceptance/clients/application/application_client.py`; port value in `infra/.env`.
**Implication:** Any acceptance backend test run locally needs `BACKEND_PORT=8100` exported (or sourced from `infra/.env`) — otherwise a real 404 (route not mounted) is indistinguishable from a wrong-port 404.
**From:** scenario 1.1 (reject-malformed-email)

## Quirk: `docker compose build backend` fails with "invalid file request" on OneDrive-synced checkout

**Quirk:** `docker compose build backend` (needed to pick up new backend code before `green-acceptance`) fails with `ERROR: invalid file request backend/adapters/generation_provider/certs/russiantrustedca.pem` during context transfer — reproduced with default builder, a fresh `docker buildx` builder, and after `docker builder prune`. Root cause: repo lives under OneDrive (`C:\Users\trape\OneDrive\Desktop\textery`), and OneDrive's cloud-file (Files On-Demand) reparse-point handling races with buildkit's context sync even when the file is fully hydrated/pinned locally.
**Workaround used:** stopped the `infra-backend-1` container and ran the backend directly with local `uvicorn` (`DATABASE_URL=postgresql+asyncpg://textery:change-me@localhost:5432/textery`, `REDIS_URL=redis://localhost:6379/0`, pointed at the compose-exposed Postgres/Redis ports) to exercise `green-acceptance` against fresh code, then restarted the container afterward (still running the old image).
**Implication:** Any `green-acceptance` step that needs a backend code change picked up will hit this until the container image is rebuilt. Either rebuild the image outside this checkout path (e.g. a non-OneDrive clone) or keep using the local-uvicorn workaround per scenario.
**From:** scenario 1.3 (reject-password-failing-policy)
