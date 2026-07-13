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
