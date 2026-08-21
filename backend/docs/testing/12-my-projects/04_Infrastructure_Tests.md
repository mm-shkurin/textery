<!-- COPIED FILE. Source of truth: ProductSpecification/stories/12-my-projects/tests/04_Infrastructure_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Мои проекты — Infrastructure Tests

The feed is a pure read, so its infrastructure surface is the database connection, the one
migration this story ships, and the two things the application does not own: the database's
collation support and the configured bounds. The migration is the interesting part:
`generations` is a populated table written continuously by the stale sweep in every replica,
which the `documents` migration it mirrors was not. Collation and configuration fail silently
in a small development database and loudly in production, which is what these tests invert.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.projects@textery.test` / `Qa!Projects2026` |
| Compose stack | `infra/docker-compose.yml`; ports read from `infra/.env`, never hardcoded |
| Database container | the compose service backing the app, stopped/started with `docker compose stop db` / `start db` |
| Migration command | `alembic upgrade head` against the seeded database |
| Migration under test | adds `generations.idempotency_key` (nullable), `generations.source_generation_id` (nullable, self-FK), and a `CONCURRENTLY`-built unique index on `(owner_id, idempotency_key)` under a `lock_timeout` |
| Seeded generations | 5 000 rows across 50 accounts, all with `idempotency_key IS NULL` |
| Stale sweep | `RequeueStaleGenerations`, run from every replica's lifespan; `GENERATION_STALE_AFTER_MINUTES=10` |
| Pinned collation | `ru-RU-x-icu` (requires an ICU-enabled Postgres image) |
| Bounds read at startup | `GENERATION_STALE_AFTER_MINUTES=10`, statement deadline `3s`, search-slot TTL `10s`, retry ceiling `5`, `PAGE_MAX=1000` |
| Error body shape | `{"error_code": "<CODE>", "message": "<generic text>", "correlation_id": "<uuid>"}` on 5xx |

---

## 1. Database Availability

### TC-12-INFRA-1.1 — The feed fails cleanly when the database is unavailable

| Field | Value |
|---|---|
| Description | An empty `200` during an outage tells the user their projects are gone and invites them to re-create paid work; the refusal must also disclose nothing about the connection. |
| Preconditions | Account A owns projects; the application is running; the database container is stopped. |
| Test data | `docker compose -f infra/docker-compose.yml stop <db service>`; account A's Bearer token. |
| Steps | 1. Stop the database container.<br>2. `GET /api/v1/projects` with account A's token.<br>3. Read the response body in full. |
| Expected result | A `5xx` (`503`) carrying `{"error_code":"…","message":"<generic text>","correlation_id":"<uuid>"}`; never `200` with `"items":[]`; the body contains no host, port, DSN, password, driver class, SQL text or stack frame. |
| Status | Not run |

### TC-12-INFRA-1.2 — The feed recovers once the database returns

| Field | Value |
|---|---|
| Description | A pool that does not recycle dead connections keeps failing after the database is healthy, and the outage only ends when someone restarts the app. |
| Preconditions | The database is stopped and a projects request has already failed (TC-12-INFRA-1.1). |
| Test data | `docker compose … start <db service>`; account A owns 6 projects. |
| Steps | 1. Start the database container again.<br>2. `GET /api/v1/projects` with account A's token, retrying for up to 30 s.<br>3. Confirm the application process id is unchanged. |
| Expected result | Within 30 s the request answers `200 OK` with all 6 projects and `"total":6`; the application's process id is the same one that served the failed request — no restart was performed. |
| Status | Not run |

---

## 2. Migration Against a Populated Table

### TC-12-INFRA-2.1 — The migration completes on a table that already has generations

| Field | Value |
|---|---|
| Description | A `NOT NULL` column or a backfilled `''` would abort the deploy or collide on the first account with two generations; nullable plus distinct NULLs is what makes it survivable. |
| Preconditions | A database holding the 5 000 seeded generations across 50 accounts, none carrying an idempotency key; schema at the revision before this story's. |
| Test data | `alembic upgrade head`; row count 5 000 recorded before the run. |
| Steps | 1. Record `SELECT count(*) FROM generations`.<br>2. Run `alembic upgrade head`.<br>3. `GET /api/v1/generations` and `GET /api/v1/projects?limit=100` for several seeded accounts. |
| Expected result | The command exits `0`; `alembic current` reports head; the row count is still 5 000 and every pre-existing generation still has `idempotency_key IS NULL`; both list endpoints answer `200 OK` and return the seeded rows. |
| Status | Not run |

### TC-12-INFRA-2.2 — The new constraint holds for new rows without rejecting old ones

| Field | Value |
|---|---|
| Description | The index must bind new writes while leaving legacy NULL-keyed rows alone — Postgres treats NULLs as distinct, which is the property the design relies on. |
| Preconditions | Database migrated to head from the populated table; account A signed in. |
| Test data | Two `POST /api/v1/generations` calls with the same `Idempotency-Key: k-infra-22`. |
| Steps | 1. `POST /api/v1/generations` with `Idempotency-Key: k-infra-22`.<br>2. Repeat the identical request.<br>3. `SELECT count(*) FROM generations WHERE idempotency_key IS NULL`. |
| Expected result | Step 1 answers `201 Created`; step 2 answers `200 OK` with the same `id` and no second row; step 3 still returns 5 000 — no legacy row was rejected, deleted or modified. |
| Status | Not run |

### TC-12-INFRA-2.3 — The migration does not block the running sweep

| Field | Value |
|---|---|
| Description | A plain index build takes `ACCESS EXCLUSIVE` over a table every replica's sweep is issuing `UPDATE`s against — the deploy would stall the whole generation pipeline. |
| Preconditions | The seeded database plus a `RequeueStaleGenerations` sweep running on its normal tick against stale rows. |
| Test data | Sweep ticking every 30 s over ≥ 20 stale rows; migration built `CONCURRENTLY` under `lock_timeout`. |
| Steps | 1. Start the sweep and confirm it is requeueing rows.<br>2. Run `alembic upgrade head` while it ticks.<br>3. Watch the sweep's log and `pg_locks` for the duration. |
| Expected result | The sweep keeps claiming and requeueing stale rows throughout the migration with no failed tick; the migration exits `0` without waiting indefinitely — it either finishes or fails on its `lock_timeout`, never blocks unbounded on `ACCESS EXCLUSIVE`. |
| Status | Not run |

### TC-12-INFRA-2.4 — The previous code version keeps writing against the migrated schema

| Field | Value |
|---|---|
| Description | The migration lands before the new code in a rolling deploy; if the old version's keyless inserts collide on the new index, the deploy breaks generation for everyone mid-roll. |
| Preconditions | Database at head; the previous application version deployed against it; the sweep running. |
| Test data | Two `POST /api/v1/generations` from the old version for account A, neither supplying `Idempotency-Key`. |
| Steps | 1. Create two generations from the previous version for one account.<br>2. `GET /api/v1/projects?limit=100` from the new version.<br>3. Let the sweep run an `UPDATE` against those two rows. |
| Expected result | Both creates answer `201` and both rows are stored with `idempotency_key IS NULL`; no unique-violation is raised; both appear as items in the new feed; the sweep's `UPDATE`s against them succeed. |
| Status | Not run |

---

## 3. Configuration and Collation

### TC-12-INFRA-3.1 — A required constant that is unset or unparsable stops startup

| Field | Value |
|---|---|
| Description | A bad bound discovered on the first request is an outage found by a user; discovered at startup it is a deploy that never rolls. |
| Preconditions | A deployable application image and its compose environment. |
| Test data | `GENERATION_STALE_AFTER_MINUTES` unset, then `""`, then `abc`. |
| Steps | 1. Start the application with the variable unset.<br>2. Repeat with `""`.<br>3. Repeat with `abc`.<br>4. In each case try one `GET /api/v1/projects`. |
| Expected result | Each start exits non-zero with a message naming `GENERATION_STALE_AFTER_MINUTES`; the process never reaches a serving state; no request is answered — the failure is not deferred to the first read. |
| Status | Not run |

### TC-12-INFRA-3.2 — A documented default is in effect and observable when its variable is unset

| Field | Value |
|---|---|
| Description | A documented default that is not actually wired is a silent divergence between the spec and the running system. |
| Preconditions | A constant whose default is documented — search-slot TTL, documented default `10s` — with its variable unset. |
| Test data | Slot-TTL variable unset; account A; an abandoned search slot. |
| Steps | 1. Start the application with that variable unset.<br>2. Read the value the app reports for it at startup/readiness.<br>3. Claim account A's search slot, abandon it, and probe a new search at `T+9.9s` and `T+10.1s`. |
| Expected result | The reported value is `10s`; the probe at `T+9.9s` answers `429 SEARCH_BUSY` and the probe at `T+10.1s` answers `200 OK` — the documented default governs observed behaviour, not just the log line. |
| Status | Not run |

### TC-12-INFRA-3.3 — A database without the pinned collation is rejected at startup

| Field | Value |
|---|---|
| Description | A non-ICU image silently orders `title_asc` differently, so the same feed reads differently per environment and no test reproduces it locally. |
| Preconditions | A Postgres image built without ICU, so `ru-RU-x-icu` does not exist. |
| Test data | Collation `ru-RU-x-icu`; the non-ICU database. |
| Steps | 1. Point the application at the non-ICU database.<br>2. Start the application.<br>3. Attempt `GET /api/v1/projects?sort=title_asc`. |
| Expected result | Startup exits non-zero with a message naming `ru-RU-x-icu`; the process does not serve; the `title_asc` request is never answered with an unpinned ordering. |
| Status | Not run |

### TC-12-INFRA-3.4 — The search deadline does not outlive its request

| Field | Value |
|---|---|
| Description | A bare `SET statement_timeout` on a pooled connection is inherited by the next borrower, and the first thing to start failing is the sweep's contended `UPDATE`. |
| Preconditions | The pool is sized to 1 so the next statement provably reuses the same connection. |
| Test data | A search request that sets the 3 s deadline; then a write deliberately taking ~8 s. |
| Steps | 1. `GET /api/v1/projects?q=климат` and let it complete.<br>2. On the same pooled connection, run the ~8 s write.<br>3. Outside any transaction on that connection, run `SHOW statement_timeout`. |
| Expected result | The write completes after ~8 s and is not cancelled at 3 s; no `QueryCanceled` is raised; `SHOW statement_timeout` returns the cluster default, not `3s`. |
| Status | Not run |

---

## 4. Search Slot Lifecycle

### TC-12-INFRA-4.1 — Reclaiming an expired search slot leaves live slots intact

| Field | Value |
|---|---|
| Description | Reclamation is a `DELETE` over shared state; a missing `WHERE expires_at < now()` would clear every account's slot and remove the cap entirely. |
| Preconditions | Account A's slot was claimed 15 s ago and has expired; accounts B and C claimed theirs 1 s ago and hold live searches; slot TTL 10 s. |
| Test data | Three slot rows: A expired, B and C live. |
| Steps | 1. Run the reclamation pass.<br>2. Count the remaining slot rows.<br>3. Issue a second concurrent search as account B, then as account C.<br>4. Run the reclamation pass again with nothing expired and count the rows. |
| Expected result | After step 1 exactly two slot rows remain — B's and C's — and A's is gone; step 3 answers `429 SEARCH_BUSY` for both B and C; step 4 removes zero rows and leaves the count at two. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the database is unavailable` | Compose-level stop of the database container (existing infra-test harness) |
| `the migration runs` | `alembic upgrade head` against the seeded database |
| `the stale sweep` | `RequeueStaleGenerations`, run from every replica's lifespan |
| `does not wait indefinitely for a lock` | `lock_timeout` set; unique index built `CONCURRENTLY` |
| `the pinned sort collation` | `ru-RU-x-icu` — requires an ICU-enabled Postgres image |
| `the search deadline` | 3 s, applied per transaction (`SET LOCAL`), never per session |
| `startup fails` | Non-zero exit with the key named in the message; no partially started app |
