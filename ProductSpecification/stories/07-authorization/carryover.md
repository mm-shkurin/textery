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

## Quirk: find_active_by_account_id returns consumed/expired codes
**Quirk:** `SqlAlchemyVerificationCodeRepository.find_active_by_account_id` returns the most-recently-issued code for an account regardless of whether it is consumed or expired — "active" means "the current one", with validity judged by the caller.
**Where:** `backend/adapters/db/src/access/auth/verification_code_storage.py`.
**Implication:** The `is_verified` idempotent-replay fork and the 3.6 code-consume guard both depend on this (a consumed code is still found, so a replay is distinguishable from an unknown one); any future "tidy" that filters `consumed_at IS NULL`/expiry in the query would silently break idempotency (3.4) with all usecase tests still green, and would need the expiry/consumption checks that currently live in `VerifyAccount.execute` re-homed.
**From:** scenario 3.4 (idempotent-consumed-code)

## Quirk: acceptance suite is not bound to the running :8100 image SHA (stale-image false green)

**Quirk:** Every `green-acceptance` run asserts behavior against the running `infra-backend-1` container on `:8100`, but nothing binds that image to the checked-out source: `backend/application/src/app/main.py` exposes no `/health` or `/version` route, and `acceptance/clients/application/application_client.py` / `acceptance/conftest.py` post blind and assert only status/body — no image-SHA check. Combined with the OneDrive `docker compose build backend` failure (this file's earlier quirk — the workaround leaves "the container still running the old image"), a stale image is the *default* failure mode, not a rare one. A future change that breaks a resend-family (or any) behavior can pass a full acceptance run against a pre-break image, and "N passed / 0 failed" is byte-identical to a run against HEAD — the suite silently stops being a regression gate.
**Where:** `backend/application/src/app/main.py` (no version route), `acceptance/clients/application/application_client.py` + `acceptance/conftest.py` (no SHA-binding fixture).
**Implication:** Green-acceptance greenness is only trustworthy when the image was **rebuilt from current source this run** (as 4.5's was — its new 409 assertion would have gone red on a gate-less image, so that specific run is sound). The durable fix (tracked, needs an owner — surfaced repeatedly across 4.1–4.5, most sharply by the premortem on 8bc5df4): add a build-SHA `/version` (or `/health`) endpoint and a session-scoped acceptance fixture that fails fast unless the running image's SHA equals `git rev-parse HEAD`. Until then, always rebuild before trusting a green-acceptance result.
**From:** scenario 4.5 (resend-rejected-when-already-verified) green-acceptance / premortem on 8bc5df4

## Quirk: two-racing-session db tests need a race-window sleep or asyncio serializes them

**Quirk:** A two-`AsyncSession` concurrency test launched with `asyncio.gather` does NOT reliably race on a single event loop — without a suspension point between the read and the commit, one coroutine runs its whole critical section (read → write → commit) before the other starts, so a NON-atomic / no-op-lock implementation still produces the correct result and the falsification is masked.
**Where:** the `*_concurrency_statements.py` DSLs (`resend_concurrency_statements.py` added an `asyncio.sleep(_RACE_WINDOW_SECONDS)` between the read and the commit; `account_concurrency_statements.py` / `verification_code_concurrency_statements.py` race single-statement conditional UPDATEs where the DB row lock is the whole mechanism, so they need no sleep).
**Implication:** when the racing operation is a multi-step read-then-write critical section (lock → read → decide → write → commit), insert an `asyncio.sleep` between the read and the commit so a real DB row lock is what serializes the racers — otherwise the test passes against a broken (non-atomic) implementation and proves nothing. A single-statement atomic `UPDATE … SET c = c + 1` or conditional `UPDATE … WHERE` does not need the sleep (the row lock serializes inside one statement).
**From:** scenario 4.4 (concurrent-resend-single-writer)

## Quirk: a client-side 25s timeout now wraps EVERY httpClient request

**Quirk:** `httpClient.request` (`frontend/src/shared/api/httpClient.ts`) wraps every call — GET and POST, all flows (login/register/verify/resend/refresh + future generation) — in `withTimeout(..., REQUEST_TIMEOUT_MS=25_000)`, a reject-only `Promise.race` against a self-rejecting timer (deliberately not signal-based, so a black-holed connection still rejects). It does NOT abort or auto-retry — a hung request surfaces as a `RequestTimeoutError` (bodyless, no `status`/`errorCode`), giving a retry affordance without silently replaying a mutating POST.
**Where:** `frontend/src/shared/api/httpClient.ts`.
**Implication:** Only `LoginForm` maps a transport-shaped rejection to a network-error state; `VerifyCodeForm`/`RegisterForm` currently render a `RequestTimeoutError` as a wrong-code / email-field error (a correct code told "invalid"). Any flow legitimately slower than 25s hard-fails — a real generation POST must carry an Idempotency-Key (login/register do not yet). Future verify/register network-error work must route no-`errorCode`/timeout rejections to a distinct network state, not the field-error path.
**From:** scenario 5.6 (network-timeout-vs-validation)

## Quirk: AuthApiError.status is attached ONLY on the codeless (UNKNOWN_ERROR) path

**Quirk:** `toAuthApiError` (`frontend/src/features/auth/api/apiError.ts`) threads `HttpError.status` onto `AuthApiError` only when the body carries no usable `error_code` (the `!hasUsableCode` branch); a coded error keeps its exact 2-field `{errorCode, message}` shape. So the login `status>=500` network branch can fire only for a CODELESS 5xx — a coded 5xx (`INTERNAL_SERVER_ERROR` with a body) keeps generic copy, never the retry state.
**Where:** `frontend/src/features/auth/api/apiError.ts`.
**Implication:** The existing coded-error `toStrictEqual` tests (loginApi/accountLocked) are the guard forcing this conditional — attaching `status` to every AuthApiError breaks them. Future api-layer work must preserve the codeless-only attach; if all 5xx should be retry-capable, that is a new scenario.
**From:** scenario 5.6 (network-timeout-vs-validation)

## Decision: the app is a plain BrowserRouter — no useBlocker available

**Decision:** In-app navigation guards must be implemented at the click seam (a `Link`'s `onClick` + `window.confirm`) or via `beforeunload`, NOT react-router's `useBlocker`/data-router APIs.
**Why:** `App.tsx` uses a plain `<BrowserRouter>` (not `createBrowserRouter`), so `useBlocker` throws; migrating to a data router is a cross-cutting change out of scope for a single scenario.
**Where applied:** `frontend/src/app/App.tsx`; the 5.8 unsaved-input guard (`useUnsavedGuard` + the register→login `Link` onClick). Consequence: a browser Back/history-pop nav-away is UNGUARDED until a data-router migration — any future nav-interception scenario inherits this limit.
**From:** scenario 5.8 (unsaved-registration-input)
