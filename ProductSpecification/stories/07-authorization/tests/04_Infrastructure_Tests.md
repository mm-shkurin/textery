# Authorization — Infrastructure Tests

Endpoints under test: `POST /api/v1/auth/register`, `/auth/verify`, `/auth/resend-code`,
`/auth/login`, `/auth/refresh`. Infrastructure is driven only through
`infra/docker-compose.yml` and `infra/.env` — never by hand on a running host.

Shared test data for every case below:

| Name | Value |
|---|---|
| Account V (verified) | `qa.auth.verified@textery.test` / `Qa!Verified2026` |
| Backend / Postgres | the services and ports declared in `infra/.env` (never hardcoded) |
| Generic 500 body | `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}` |
| Sentinel strings that must never reach the client | `psycopg`, `sqlalchemy`, `relation "users" does not exist`, `/app/usecase/src/auth/`, `Traceback` |

---

## TC-07-INFRA-1 — Database connection failure during auth request

| Field | Value |
|---|---|
| Description | With Postgres down, the driver exception must be translated into one generic error — a leaked driver message names the stack, the schema and the file layout — and no auth request may be left half-applied. |
| Preconditions | Backend running and healthy; Postgres reachable; account V exists. |
| Test data | All five auth endpoints, each with an otherwise-valid body; sentinel strings above |
| Steps | 1. `docker compose -f infra/docker-compose.yml stop postgres`.<br>2. Call each of register, verify, resend-code, login and refresh once.<br>3. Read each response body.<br>4. `docker compose -f infra/docker-compose.yml start postgres`, then query `users` and the verification-code table for any partial write from step 2. |
| Expected result | Every call answers `500` with exactly the generic `INTERNAL_ERROR` body; no sentinel string appears in any response; the backend container stays up (no restart loop); step 4 finds no new account row, no new code row, and no counter change from the failed calls. |
| Status | Not run |

## TC-07-INFRA-2 — Database recovery after failure

| Field | Value |
|---|---|
| Description | A pool that keeps handing out dead connections after the database returns leaves the service broken long after the outage ends — recovery must need no restart. |
| Preconditions | Postgres has just been stopped and restarted per TC-07-INFRA-1; the backend container was never restarted. |
| Test data | Registration for `qa.auth.recover@textery.test` / `Qa!Auth2026`, then login as account V |
| Steps | 1. `docker compose -f infra/docker-compose.yml start postgres` and wait for its healthcheck to pass.<br>2. `POST /api/v1/auth/register` for `qa.auth.recover@textery.test`.<br>3. `POST /api/v1/auth/login` with account V's credentials.<br>4. Repeat step 3 nine more times. |
| Expected result | Step 2 answers `201 Created` with a 6-digit `verification_code`; steps 3–4 answer `200 OK` with a token pair every time — no `500`, no intermittent stale-connection failure, and no backend restart was required. |
| Status | Not run |

## TC-07-INFRA-3 — JWT signing secret misconfiguration at startup

| Field | Value |
|---|---|
| Description | A service that boots without a usable signing secret would either issue tokens nobody can verify or fall back to a default key — both are silent auth bypasses. Failing at startup makes the misconfiguration impossible to miss. |
| Preconditions | A copy of `infra/.env` where the JWT secret entry can be blanked and restored. |
| Test data | Case A: JWT secret key removed entirely; Case B: JWT secret set to the empty string; Case C: JWT secret set to a malformed value (e.g. 4 characters, below the minimum key length) |
| Steps | 1. Blank the JWT secret in the env file and `docker compose -f infra/docker-compose.yml up backend`.<br>2. Read the container's exit code and its stderr.<br>3. Attempt `POST /api/v1/auth/login` against the backend port.<br>4. Repeat for the empty-string and malformed values.<br>5. Restore the original value and restart. |
| Expected result | In all three cases the container exits non-zero during startup with an explicit configuration error naming the missing/invalid JWT secret setting; step 3 gets a connection refusal, not a served response — the service never reaches a state where it could issue an unsigned or unverifiable token; step 5 restores a healthy backend. |
| Status | Not run |
