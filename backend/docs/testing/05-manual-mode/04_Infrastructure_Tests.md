<!-- COPIED FILE. Source of truth: ProductSpecification/stories/05-manual-mode/tests/04_Infrastructure_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Manual input mode (non-AI document creation) — Infrastructure Tests

No external service dependency exists in this story (no LLM/generation provider call),
so only database failure/recovery scenarios apply.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the owner) | `qa.manual@textery.test` / `Qa!Manual2026` |
| Document A1 | id `3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3`, `document_type` `реферат`, `content` `<p>Первый абзац.</p>`, `version` `2` |
| Create request | `POST /api/v1/documents` `{"document_type": "реферат"}` + `Idempotency-Key: <fresh UUID>` |
| Save request | `PUT /api/v1/documents/{document_id}` `{"content": "<p>Абзац</p>", "version": <current>}` |
| Error body shape | `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}` |
| Fault injection | Postgres connection refused/timeout injected at the adapter boundary (compose service stopped, or the port blackholed) |
| Health probe | `GET /health` → `200 {"status": "ok", "failed_dependencies": []}` when healthy |

---

## 1. Database Connection Failure Handling

### TC-05-INFRA-1.1 — Document creation fails cleanly when the database is unavailable

| Field | Value |
|---|---|
| Description | An unreachable database must produce one clean server error, not a hang, a raw driver traceback, or a half-written row that surfaces later as a phantom document. |
| Preconditions | Backend running; account A signed in with a valid access token; Postgres made unreachable at the adapter boundary. |
| Test data | `POST /api/v1/documents` `{"document_type": "реферат"}` with a fresh `Idempotency-Key`; after recovery, the document list for account A |
| Steps | 1. Stop/blackhole Postgres and confirm `GET /health` reports the dependency as failed.<br>2. `POST /api/v1/documents` with account A's token.<br>3. Restore Postgres.<br>4. Query the `documents` table for rows owned by account A. |
| Expected result | Step 2 answers `500 Internal Server Error` with exactly `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}` — no raw SQLAlchemy/psycopg text, no connection string; the response arrives rather than hanging; step 4 shows zero committed rows for the failed attempt. |
| Status | Not run |

### TC-05-INFRA-1.2 — Document save fails cleanly when the database is unavailable

| Field | Value |
|---|---|
| Description | A failed save must leave the previous version intact — a partially applied write would hand back content that is neither the old nor the new document. |
| Preconditions | Document A1 exists with `content` `<p>Первый абзац.</p>` and `version` `2`; Postgres then made unreachable. |
| Test data | `PUT /api/v1/documents/3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3` `{"content": "<p>Новый абзац.</p>", "version": 2}` |
| Steps | 1. Record document A1's `content` and `version`.<br>2. Make Postgres unreachable.<br>3. Issue the save request.<br>4. Restore Postgres and `GET /api/v1/documents/{A1}`. |
| Expected result | Step 3 answers `500` with the generic `{"error_code": "INTERNAL_ERROR", …}` body; step 4 returns `content` `<p>Первый абзац.</p>` and `version` `2` — unchanged from step 1, with `<p>Новый абзац.</p>` nowhere stored. |
| Status | Not run |

### TC-05-INFRA-1.3 — A failed manual-document creation never leaves a stray Generation row behind

| Field | Value |
|---|---|
| Description | The manual path must never create a `Generation`, including on its failure path. A stray one would let story #1's completion handler later push this document to `completed`. |
| Preconditions | Account A signed in; the `generations` row count for account A recorded; a fault injected during the single insert underlying `POST /api/v1/documents`. |
| Test data | `POST /api/v1/documents` `{"document_type": "реферат"}` with a fresh `Idempotency-Key`; tables `documents` and `generations` |
| Steps | 1. Record the `documents` and `generations` row counts for account A.<br>2. Inject the mid-insert failure and issue the create request.<br>3. Recover and re-count both tables. |
| Expected result | The request answers `500` with the generic error body; the `documents` count is exactly the step-1 count — no row for the failed attempt; the `generations` count is exactly the step-1 count and no `Generation` row references the attempted `document_id`. |
| Status | Not run |

---

## 2. Database Recovery After Failure

### TC-05-INFRA-2.1 — Document creation and save succeed again once the database recovers

| Field | Value |
|---|---|
| Description | A pool that caches dead connections keeps returning `500` long after Postgres is back; the outage must end when the database does. |
| Preconditions | Postgres was made unreachable, a create request failed with `500`, and Postgres has since been restored. |
| Test data | `POST /api/v1/documents` `{"document_type": "реферат"}` with a fresh `Idempotency-Key`, then `PUT /api/v1/documents/{new id}` `{"content": "<p>После восстановления</p>", "version": 1}` |
| Steps | 1. Restore Postgres and wait for `GET /health` → `200 {"status": "ok", "failed_dependencies": []}`.<br>2. Retry the create request.<br>3. Save content into the newly created document. |
| Expected result | Step 2 answers `201 Created` with `status` `draft` and `content` `""`; step 3 answers `200 OK` with `version` `2` and the saved content; no `500` on either, and no manual backend restart was required. |
| Status | Not run |

### TC-05-INFRA-2.2 — Many concurrent clients retrying after a shared recovery do not re-trigger the outage

| Field | Value |
|---|---|
| Description | A thundering herd — every blocked client retrying at the same instant — can exhaust the connection pool the moment the database returns, turning one outage into a repeating cycle. |
| Preconditions | 200 clients were all blocked by the same Postgres outage and hold pending create/save retries; Postgres has since recovered. |
| Test data | 200 concurrent clients re-issuing their blocked `POST`/`PUT`; connection-pool ceiling from `infra/.env`; retry timestamps captured per client |
| Steps | 1. Signal recovery to all 200 clients at once.<br>2. Let every client re-issue its blocked request.<br>3. Record each retry's send timestamp and connection-acquisition attempt.<br>4. Poll `GET /health` throughout the retry burst. |
| Expected result | All 200 retries eventually answer `2xx` (`201`/`200`); the retry timestamps are spread by jitter/backoff rather than clustered in a single instant; connection acquisitions stay within the configured pool ceiling; `GET /health` never reports the database as a failed dependency again during or after the burst. |
| Status | Not run |

---

## 3. Startup Configuration Validation

### TC-05-INFRA-3.1 — The application fails fast at boot when required database configuration is missing

| Field | Value |
|---|---|
| Description | A backend that binds its port with no database configured is reported healthy by the orchestrator and then fails every single request — failing fast keeps the bad instance out of rotation. |
| Preconditions | A backend container/process that has not yet started. |
| Test data | The database connection env var (per `infra/.env`) unset, then set to the empty string; the application's listening port from `infra/.env` |
| Steps | 1. Start the application with the DB connection env var unset; capture the exit code and stderr.<br>2. Repeat with the var set to `""`.<br>3. During both, attempt a TCP connection to the application's port. |
| Expected result | Both starts exit non-zero with a clear configuration error naming the missing setting; neither ever binds the port — the step-3 connection is refused in both runs; no request is ever served in a partially-configured state. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---|---|
| `the database is unreachable` | Postgres connection refused/timeout injected at the adapter boundary |
| `no partial document record is left behind` | no committed row for the failed creation attempt |
| `the document's previously persisted content is unchanged` | prior `content`/`version` values unchanged after the failed save |
| `has since recovered` | DB connectivity restored after the injected failure |
| `the database write for a manual-document creation fails partway through` | fault injected during the single insert underlying `POST /api/v1/documents` |
| `no Generation row exists referencing the attempted document` | `Generation` table row count for that `document_id` is zero, checked even on the failure path |
| `many clients ... retry ... at once` | M concurrent clients re-issue their blocked `POST`/`PUT` requests immediately after recovery is signaled |
| `not synchronized into a single overwhelming spike` | retry timestamps/connection-acquisition attempts show jitter/spread, not all landing in the same instant |
| `the database connection configuration is missing or blank` | DB connection string/credentials env var unset/blank at process start |
| `startup fails immediately` | application process exits non-zero / refuses to bind before serving traffic |
