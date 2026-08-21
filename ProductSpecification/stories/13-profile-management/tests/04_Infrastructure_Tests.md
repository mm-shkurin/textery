# Profile management — Infrastructure Tests

Two concerns: the database being unavailable under an endpoint that every authenticated page
now depends on, and a migration landing on a populated `accounts` table across a fleet that
rolls one instance at a time.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.profile@textery.test` / `Qa!Profile2026`, `name = "Мария Соколова"`, `created_at = 2026-03-14T09:26:53Z` |
| Postgres container | the compose service in `infra/docker-compose.yml`; ports and names from `infra/.env` (never hardcoded) |
| Canonical failure form | `{"error_code": "<CODE>", "message": "<generic text>"}` via `exception_handlers.py` |
| 500 body | `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}` |
| The migration | the Alembic revision adding the nullable `name` column to `accounts` |
| Pre-story image | the application image built from the commit before that revision |
| Seeded fleet fixture | 5 `accounts` rows: 2 verified, 1 unverified, 1 with `failed_attempt_count = 3`, 1 registered in 2025 |
| App body cap | 2 MiB (`api-specs/README.md` § Request Body Cap) |
| Proxy config | `infra/docker/nginx/frontend.conf`, which proxies `location /api/` to `backend:8000` |

---

## 1. Database Availability

### TC-13-INFRA-1.1 — A profile read with the database down fails cleanly

| Field | Value |
|---|---|
| Description | The endpoint every authenticated page depends on must degrade into a defined refusal, not a driver traceback on the wire or a dead worker. |
| Preconditions | The application running and healthy; account A signed in with a valid access token; the Postgres container then stopped. |
| Test data | `docker compose -f infra/docker-compose.yml stop postgres` (service name from `infra/.env`); `GET /api/v1/auth/me`. |
| Steps | 1. Stop the Postgres service.<br>2. `GET /api/v1/auth/me` with account A's Bearer token.<br>3. Read the status, `Content-Type` and body.<br>4. `docker ps` / the app's health endpoint to confirm the process. |
| Expected result | `500` with `Content-Type: application/json` and body exactly `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}`; the body contains no `psycopg`, no `OperationalError`, no `postgresql://` connection string, no `Traceback` and no `.py:` path; the application container is still `Up` and answering its health check. |
| Status | Not run |

### TC-13-INFRA-1.2 — A rename with the database down persists nothing and reports the fault

| Field | Value |
|---|---|
| Description | A write attempted against a dead database must leave the stored name exactly as it was once the database returns — no queued or replayed write. |
| Preconditions | Account A stored with `name = "Мария Соколова"`; the application healthy; the Postgres container then stopped. |
| Test data | `PATCH /api/v1/auth/me` with `{"name": "Мария Волкова"}`. |
| Steps | 1. Stop the Postgres service.<br>2. `PATCH /api/v1/auth/me` with `{"name": "Мария Волкова"}`; read the status and body.<br>3. Start the Postgres service and wait for it to be healthy.<br>4. Re-read account A's row in a new session. |
| Expected result | Step 2: `500` with the `INTERNAL_ERROR` body. Step 4: `name` is still `Мария Соколова` — `Мария Волкова` is nowhere in the table. |
| Status | Not run |

### TC-13-INFRA-1.2a — A database that accepts the connection and never answers is abandoned

| Field | Value |
|---|---|
| Description | TC-13-INFRA-1.1 covers the database being **down** and the extended file covers the pool being **exhausted**; neither covers it being **slow**. The pool's checkout timeout does not bound a statement already running on a checked-out connection, so without a statement or socket deadline a slow database converts into fleet-wide worker exhaustion on the product's highest-rate endpoint. |
| Preconditions | Postgres reachable but the account select made to hang — e.g. a TCP proxy in front of Postgres that completes the handshake and then withholds the result, or `SELECT pg_sleep(600)` injected on the account read path. Account A signed in. |
| Test data | Bounded statement wait: the configured statement/socket deadline (expected `<= 10 s`); the pool checkout gauge sampled before and after. |
| Steps | 1. Record the checked-out-connection count.<br>2. `GET /api/v1/auth/me` and start a stopwatch.<br>3. Record the status, body and elapsed time when the response arrives.<br>4. Sample the checkout gauge again 5 s after the response. |
| Expected result | The response arrives within the configured statement deadline (`<= 10 s`), not after the client gives up and not never; it is `500` with the canonical `{"error_code": "INTERNAL_ERROR", "message": …}` body; the checkout gauge in step 4 equals step 1 — the connection went back to the pool rather than staying pinned to the abandoned statement. |
| Status | Not run |

### TC-13-INFRA-1.3 — The profile read recovers once the database returns

| Field | Value |
|---|---|
| Description | A pool that caches dead connections keeps failing after the database is healthy again, and the symptom is "restart the app to fix it". |
| Preconditions | The database was stopped and a `GET /api/v1/auth/me` failed with `500` (TC-13-INFRA-1.1 executed); the application container never restarted. |
| Test data | Restart of the Postgres service; the same account A token. |
| Steps | 1. Confirm the app container's start time / PID and record it.<br>2. Start the Postgres service and wait for its health check to pass.<br>3. `GET /api/v1/auth/me` with account A's token.<br>4. Re-read the container's start time / PID. |
| Expected result | Step 3 answers `200 OK` with `{"email": "qa.profile@textery.test", "name": "Мария Соколова", "created_at": "2026-03-14T09:26:53Z"}` on the first attempt; the start time / PID in step 4 is identical to step 1 — the recovery required no restart. |
| Status | Not run |

---

## 2. Migration on a Live Fleet

### TC-13-INFRA-2.1 — Pre-story code keeps working against the new schema

| Field | Value |
|---|---|
| Description | N-1 code against N schema is live, not theoretical: instances roll one at a time, so the old image serves traffic against the migrated table during the overlap. |
| Preconditions | The 5-row seeded `accounts` fixture in place; the migration applied; one instance running the **pre-story image**. |
| Test data | Against the pre-story instance: `POST /api/v1/auth/register` (`qa.overlap@textery.test` / `Qa!Overlap2026`), `POST /api/v1/auth/verify`, `POST /api/v1/auth/login`, `POST /api/v1/auth/resend-code`. |
| Steps | 1. Apply the migration.<br>2. Snapshot all 5 pre-existing rows (`email`, `is_verified`, `created_at`, `failed_attempt_count`).<br>3. Run register → verify → login → resend against the pre-story image.<br>4. Re-snapshot the 5 pre-existing rows. |
| Expected result | Register answers `201`, verify `200`, login `200` with tokens, resend `200` — none returns `500` and none references the unknown `name` column; the step-4 snapshot is field-for-field equal to step 2. |
| Status | Not run |

### TC-13-INFRA-2.2 — The migration adds the column without touching existing rows

| Field | Value |
|---|---|
| Description | An `ALTER TABLE … ADD COLUMN name text NOT NULL DEFAULT ''` would rewrite every row and give every existing account the blank identity the contract forbids. |
| Preconditions | The 5-row seeded `accounts` fixture, none of which has ever had a name; the migration not yet applied. |
| Test data | 5 rows: 2 verified, 1 unverified, 1 with `failed_attempt_count = 3`, 1 with `created_at` in 2025. |
| Steps | 1. Record `SELECT count(*) FROM accounts` and the full 5-row snapshot.<br>2. Run `alembic upgrade head`.<br>3. Re-read the 5 rows including `name`, and re-count. |
| Expected result | The migration succeeds; every pre-existing row keeps its `email`, `is_verified`, `created_at` and `failed_attempt_count` byte-for-byte; every pre-existing row has `name IS NULL` (never `''`); `count(*)` is still `5`. |
| Status | Not run |

### TC-13-INFRA-2.2a — A row written by the pre-story image during the overlap reads back fine

| Field | Value |
|---|---|
| Description | TC-13-INFRA-2.1 asserts the old paths succeed and 2.2 asserts pre-existing rows survive; the case in between — a row **created** during the overlap and read by the new code — is what a column authored not-nullable, or a reader assuming non-null, breaks while both stay green. |
| Preconditions | The migration applied; one instance on the pre-story image and one on the new image, both against the same database. |
| Test data | Register `qa.overlap2@textery.test` / `Qa!Overlap2026` **through the pre-story instance**, then read it through the new instance. |
| Steps | 1. Register and verify the account against the pre-story instance.<br>2. Confirm the insert succeeded (`201`, row present).<br>3. Sign in and `GET /api/v1/auth/me` against the **new** instance. |
| Expected result | Step 2: the insert succeeds with no `NotNullViolation`; the row's `name` is `NULL`. Step 3: `200 OK` with body `{"email": "qa.overlap2@textery.test", "name": null, "created_at": "<its instant>Z"}` — the `name` key present and `null`, no `500`. |
| Status | Not run |

### TC-13-INFRA-2.3 — A rollback and re-apply leaves pre-existing data intact

| Field | Value |
|---|---|
| Description | The rollback drops the column, and with it every name entered since the deploy — accepted and stated (`13_ProfileManagement_Notes.md` § Infrastructure Notes), not discovered later. The sibling migration for the failed-attempt count really does drop its column on downgrade, so this is the established behaviour. |
| Preconditions | The 5-row seeded `accounts` fixture; the migration not yet applied. |
| Test data | `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head`. |
| Steps | 1. Snapshot the 5 rows and the row count.<br>2. `alembic upgrade head`.<br>3. `alembic downgrade -1` and confirm the `name` column is gone.<br>4. `alembic upgrade head` again.<br>5. Re-snapshot and re-count. |
| Expected result | All three Alembic commands exit `0`; step 5 shows every pre-existing row with its `email`, `is_verified`, `created_at` and `failed_attempt_count` unchanged from step 1, `name IS NULL` for all of them, and `count(*)` still `5`. Names written between steps 2 and 3 are gone — the accepted loss. |
| Status | Not run |

---

## 3. Configuration

### TC-13-INFRA-3.0 — The application refuses to start with a profile-path setting missing

| Field | Value |
|---|---|
| Description | Each of these degrades lazily at first use today. On the endpoint every authenticated page depends on, a silent fallback is discovered as a production symptom rather than a failed deploy. |
| Preconditions | A working `infra/.env`; three copies of it, each with exactly one setting removed. |
| Test data | (a) the request-body-cap setting unset; (b) the connection-pool-size setting unset; (c) the access-token-lifetime setting unset. |
| Steps | 1. Start the application with (a); record the exit code, the elapsed time to exit and stderr.<br>2. Repeat with (b).<br>3. Repeat with (c).<br>4. For each, probe whether the app ever bound its port. |
| Expected result | Each start exits non-zero within a few seconds; stderr names the missing setting by its exact env-var key; the app never binds its port and never serves a request; no run falls back to a framework default (2 MiB, 5, or 15 minutes appearing silently in a started process fails this case). |
| Status | Not run |

### TC-13-INFRA-3.0a — The timeout budget nests in the required order

| Field | Value |
|---|---|
| Description | The same shape TC-13-INFRA-3.1 gives the body caps, applied to time — otherwise the client gives up first and leaves inner work in flight, or the proxy cuts a response mid-commit, and either drifts silently the next time someone tunes one number. |
| Preconditions | All four values readable from source: the client's bounded wait (`frontend/src/features/auth/api/`), nginx `proxy_read_timeout` (`infra/docker/nginx/frontend.conf`), and the backend's pool-checkout and statement budgets plus retry count (`infra/.env`). |
| Test data | Backend worst case = (checkout budget + statement budget) × (retries + 1); then nginx `proxy_read_timeout`; then the client's bounded wait. |
| Steps | 1. Read the four numbers from their source files.<br>2. Compute the backend innermost worst-case total.<br>3. Assert `backend worst case < proxy_read_timeout < client bounded wait`.<br>4. Raise the backend statement budget above `proxy_read_timeout` and re-run the check. |
| Expected result | Step 3 holds with strict `<` at both boundaries; step 4 makes the check **fail** with a message naming the two values that inverted — proving the assertion is live and not merely reading the file. |
| Status | Not run |

### TC-13-INFRA-3.1 — The proxy's body cap sits above the application's

| Field | Value |
|---|---|
| Description | Unset today, so the proxy's 1 MiB default is the real ceiling and it answers with an HTML error page rather than this product's failure form — which would make the canonical size refusal unreachable for every browser while a backend-port test went green (`endpoints.md`). The existing configuration-reading check under `frontend/scripts/` is where this assertion belongs. |
| Preconditions | `infra/docker/nginx/frontend.conf` present; the application cap readable (2 MiB). |
| Test data | Expected `client_max_body_size 4m;` in the `server` or `location /api/` block; app cap 2 MiB. |
| Steps | 1. Parse `infra/docker/nginx/frontend.conf` for a `client_max_body_size` directive covering `location /api/`.<br>2. Parse the application's configured body cap.<br>3. Compare the two numerically. |
| Expected result | The directive is present (not relying on nginx's 1 MiB default) and its value is strictly greater than the application's 2 MiB cap — `4m` satisfies this, an absent directive or any value `<= 2m` fails. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the database is unavailable` | Postgres container stopped / connections refused for the duration |
| `this product's canonical failure form` | `{"error_code": …, "message": …}` via `exception_handlers.py` |
| `a fresh read of the stored profile` | Re-read through a new session against real Postgres |
| `the pre-story code path` | The application image built from the commit before this story's migration |
| `the migration` | The Alembic revision adding the nullable `name` column to `accounts` |
| `the frontend proxy configuration` | `infra/docker/nginx/frontend.conf`, which proxies `/api/` |
| `the application's own body cap` | 2 MiB (`api-specs/README.md` § Request Body Cap) |
