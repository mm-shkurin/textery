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

## Quirk: `RegisterUser.execute` never compares confirm_password

**Quirk:** `RegisterUser.execute` (`backend/usecase/src/auth/register_user.py`) accepts `confirm_password` as a parameter but never compares it against `password` — no code path enforces the match, and no scenario-1.3 fixture could catch a mismatch since they always set both fields equal.
**Where:** `backend/usecase/src/auth/register_user.py`.
**Implication:** Scenario 1.4's pending red-usecase/green-usecase steps must add the actual comparison. Any other usecase touching password fields should not assume unused constructor parameters are enforced elsewhere.
**From:** scenario 1.3 (reject-password-failing-policy)

## Quirk: Account/AccountModel has no reconstruction path for a verified account

**Quirk:** `Account.__init__` (`backend/domain/src/auth/account.py`) hardcodes `is_verified=False` with no constructor parameter and no setter — correct for *creating* a new account, but `AccountModel.to_domain()` (`backend/adapters/db/src/model/auth/account_model.py`) reuses this same constructor to *reconstruct* an account from a DB row, silently dropping the row's real `is_verified` value.
**Where:** `backend/domain/src/auth/account.py`, `backend/adapters/db/src/model/auth/account_model.py`.
**Implication:** Scenario 3.x (email verification) needs a domain-level way to represent a verified account on reconstruction (e.g. a `reconstitute` factory distinct from `create`), plus a round-trip test writing `is_verified=True` and asserting `to_domain().is_verified is True`.
**From:** scenario 1.5 (ignore-server-owned-fields)

## Quirk: SqlAlchemyAccountRepository.save() has no exception mapping

**Quirk:** `save()` has no exception handling around `session.commit()` — a raw SQLAlchemy/DB-driver exception (connection failure, or a future unique-constraint violation once scenario 2.2 lands) propagates unmapped, even though the ADR commits to "persistence failure maps to a defined exception."
**Where:** `backend/adapters/db/src/access/auth/account_storage.py`.
**Implication:** A future step needs a test that stubs `commit()` to raise and asserts `save()` translates it into a defined `AccountRepository`-level exception, not a raw driver error.
**From:** scenario 1.5 (ignore-server-owned-fields)

## Quirk: container.py's session-scoped factories have zero dedicated test coverage

**Quirk:** `create_register_user()`, `create_get_generation()`, and `create_request_generation()` in `backend/application/src/app/container.py` all share the same open-session/yield/finally-close shape, but `backend/application` has no `tests/` directory at all — none of these generators' commit-then-close or close-on-exception behavior is exercised by any unit test, only indirectly by acceptance tests.
**Where:** `backend/application/src/app/container.py`.
**Implication:** Worth a dedicated task to add `backend/application/tests/` covering session lifecycle for these factories — not scoped to story 7 alone, since two of the three affected factories predate it.
**From:** scenario 1.5 (ignore-server-owned-fields)

## Quirk: passwords are persisted as plaintext (hashing deferred to Security phase)

**Quirk:** `RegisterUser.execute` passes the raw validated password straight to `Account.create(password_hash=password, ...)` — no hashing exists anywhere in the codebase. Before scenario 1.5's green-adapter rest step, the null-object repository fallback silently discarded every account, so this was inert; now that a real repository is wired, plaintext passwords are actually persisted.
**Where:** `backend/usecase/src/auth/register_user.py`, `backend/domain/src/auth/password.py`.
**Implication:** Deliberate, tracked deferral — password hashing is `05_Security_Tests.md` Scenario 1, sequenced after Backend/Integration/Frontend per this project's lifecycle. Rated BLOCK-severity by premortem since real rows now exist with plaintext credentials — prioritize the Security phase's password-hashing scenario before any shared/prod-like environment sees real user data.
**From:** scenario 1.5 (ignore-server-owned-fields)

## Quirk: server-owned-fields acceptance fixture uses a fixed email, not per-run-unique

**Quirk:** `given_registration_request_with_server_owned_fields()` (`acceptance/statements/auth_statements.py`) uses a fixed email (`attacker@example.com`) instead of a per-run-unique one, despite the ADR calling for a per-run-unique fixture so reruns don't accumulate duplicate rows.
**Where:** `acceptance/statements/auth_statements.py`.
**Implication:** Reruns create additional `accounts` rows with the same email today (no unique constraint yet); once scenario 2.2 adds the constraint, reruns will start failing with a 409/conflict unless this fixture is made unique first.
**From:** scenario 1.5 (ignore-server-owned-fields)

## Quirk: local-uvicorn OneDrive workaround skips the container's alembic migration step

**Quirk:** The documented OneDrive-build workaround (run `uvicorn app.main:app` directly instead of the `infra-backend-1` container) starts the app without running `alembic upgrade head` first — the container's entrypoint runs migrations as a `sh -c` prefix before `uvicorn`, but the bare `uvicorn` command doesn't. A fresh/reset local Postgres then 500s with `UndefinedTableError: relation "accounts" does not exist` on the first write.
**Where:** workaround startup command (see `.claude/guidelines/infrastructure-detail.md` / prior scenario notes), migrations at `backend/adapters/db/alembic/`.
**Implication:** Every time the local-uvicorn workaround is used against a Postgres that hasn't already been migrated (new container, `docker compose down -v`, etc.), run `alembic upgrade head` (with `DATABASE_URL` pointed at the same host/port the app uses) before the first acceptance test, not just before the first code-picking-up run.
**From:** scenario 2.4c (unicode-normalization-email-uniqueness)
