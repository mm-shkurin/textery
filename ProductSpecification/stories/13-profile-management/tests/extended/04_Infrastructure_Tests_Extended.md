> These are additional edge case tests. Implement after core tests pass.

# Profile management — Infrastructure Tests (Extended)

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.profile@textery.test` / `Qa!Profile2026`, `name = "Мария Соколова"` |
| Canonical failure form | `{"error_code": "<CODE>", "message": "<generic text>"}` |
| 500 body | `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}` |
| Pool configuration | `pool_size = 5`, `max_overflow = 10`, checkout timeout 30 s |
| The migration | the Alembic revision adding the nullable `name` column to `accounts` |
| Pre-story image | the application image built from the commit before that revision |
| Seeded fleet fixture | 5 `accounts` rows: 2 verified, 1 unverified, 1 with `failed_attempt_count = 3`, 1 registered in 2025 |
| Proxy config | `infra/docker/nginx/frontend.conf` (`location /api/`) |
| App body cap | 2 MiB (`api-specs/README.md` § Request Body Cap) |

---

## 1. Partial Availability

### TC-13-INFRA-1.1e — A saturated connection pool refuses cleanly rather than hanging

| Field | Value |
|---|---|
| Description | At two checkouts per request the pool saturates faster than anyone expects; the request must fail at the checkout timeout with a defined body, not hang until the client gives up. |
| Preconditions | The application healthy; all 15 connections (`5 + 10 overflow`) held open by a fixture that checks out and sleeps; account A signed in. |
| Test data | 15 held sessions; checkout timeout 30 s; `GET /api/v1/auth/me`. |
| Steps | 1. Hold all 15 pool connections.<br>2. `GET /api/v1/auth/me` and start a stopwatch.<br>3. Record the status, `Content-Type`, body and elapsed time.<br>4. Release the held sessions; check the container is still `Up` and issue another `GET /api/v1/auth/me`. |
| Expected result | The response arrives at approximately the 30 s checkout timeout, not later and not never; it is `500` with `Content-Type: application/json` and body `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}` — no `QueuePool limit` text, no `Traceback`, no `.py:` path in the body; the container is still `Up` and the follow-up request answers `200`. |
| Status | Not run |

### TC-13-INFRA-1.2e — An application restart mid-request loses nothing already committed

| Field | Value |
|---|---|
| Description | A committed rename lives in Postgres, not in the process — a restart that loses it means the write was buffered somewhere it should not have been. |
| Preconditions | Account A signed in with `name = "Мария Соколова"`. |
| Test data | `PATCH /api/v1/auth/me` with `{"name": "Мария Волкова"}`; then `docker compose restart` of the application service (name from `infra/.env`). |
| Steps | 1. `PATCH /api/v1/auth/me` with `{"name": "Мария Волкова"}`; confirm `200 OK`.<br>2. Restart the application container; wait for its health check.<br>3. Re-read account A's row in a new session and `GET /api/v1/auth/me` with a fresh token. |
| Expected result | Step 3 shows `name = "Мария Волкова"` in the row and `"name": "Мария Волкова"` in the `200` body — the committed rename survived the restart intact. |
| Status | Not run |

---

## 2. Migration Edges

### TC-13-INFRA-2.1e — The migration is safe to apply twice

| Field | Value |
|---|---|
| Description | A re-run during a retried deploy must be a no-op, not a `DuplicateColumn` failure or a row rewrite. |
| Preconditions | The 5-row seeded `accounts` fixture with the migration already applied; two rows given names. |
| Test data | `alembic upgrade head` re-issued; also the raw revision re-applied directly. |
| Steps | 1. Snapshot all 5 rows including `name`, and the row count.<br>2. Run `alembic upgrade head` again.<br>3. Re-snapshot and re-count. |
| Expected result | The command exits `0` with no `DuplicateColumn`/`ProgrammingError`; the step-3 snapshot is field-for-field equal to step 1, names included; `count(*)` unchanged at `5`. |
| Status | Not run |

### TC-13-INFRA-2.2e — Names survive a rolling deploy in both directions

| Field | Value |
|---|---|
| Description | During the overlap the old image serves the same migrated table; its writes must not clobber a name it does not know about. |
| Preconditions | The migration applied; two instances running — one on the pre-story image, one on the new image — against one database; 3 accounts with names set through the new image. |
| Test data | Accounts `qa.roll1@textery.test` (`Мария Соколова`), `qa.roll2@textery.test` (`Иван Петров`), `qa.roll3@textery.test` (`Ольга Белова`). |
| Steps | 1. Set the three names through the new instance; snapshot all three rows.<br>2. Against the **pre-story** instance: sign in as each, and run a verification/failed-attempt path that writes the account row.<br>3. Against the **new** instance: `GET /api/v1/auth/me` as each.<br>4. Re-snapshot the three rows. |
| Expected result | All sign-ins succeed on both images (`200` with tokens); step 3 returns each account's own name; step 4 shows all three names still `Мария Соколова`, `Иван Петров`, `Ольга Белова` — no name reset to `NULL` or `''` by the old image's write. |
| Status | Not run |

---

## 3. Configuration Drift

### TC-13-INFRA-3.1e — The proxy body cap and the application body cap stay in their required order

| Field | Value |
|---|---|
| Description | The ordering is what makes the canonical `413` reachable from a browser; the assertion must fail when the order inverts, or it is only reading a file. |
| Preconditions | `infra/docker/nginx/frontend.conf` present with `client_max_body_size` set; the app cap readable as 2 MiB. |
| Test data | Expected proxy cap `4m`; app cap `2 MiB`; the inversion fixture sets the proxy to `1m`. |
| Steps | 1. Parse the proxy cap and the app cap; normalize both to bytes.<br>2. Assert `proxy cap > app cap` strictly.<br>3. Set the proxy cap to `1m` and re-run the check.<br>4. Restore the proxy cap. |
| Expected result | Step 2 passes with `4194304 > 2097152`; step 3 makes the check **fail** with a message naming both values — proving the assertion is live; an absent `client_max_body_size` also fails (nginx's 1 MiB default is below the app cap). |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `every database connection is checked out` | Pool exhausted by held sessions for the duration |
| `its bounded wait` | SQLAlchemy pool checkout timeout |
| `this product's canonical failure form` | `{"error_code": …, "message": …}` |
| `the pre-story image` | Application built from the commit before this story's migration |
| `the proxy configuration` | `infra/docker/nginx/frontend.conf` |
| `the application's declared body cap` | 2 MiB (`api-specs/README.md`) |
