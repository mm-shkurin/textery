<!-- COPIED FILE. Source of truth: ProductSpecification/stories/01-auto-generate-doklad/tests/04_Infrastructure_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Auto-generate: доклад — Infrastructure Tests

> **Provider and worker: read as GigaChat + `BackgroundTasks`, not OpenRouter + arq.**
> Written before 2026-07-09, when the engine was still planned as Claude via OpenRouter
> and the queue as `arq`. Neither shipped: generation goes through a direct `httpx`
> client to GigaChat (`backend/adapters/generation_provider/`), runs inline via
> FastAPI `BackgroundTasks`, and stale jobs are recovered by a periodic DB sweep —
> there is no worker process. `OPENROUTER_*` reads as the `GIGACHAT_*` credentials,
> "a stub OpenRouter server" as a stub GigaChat server. Behaviour is unchanged; the
> vendor and the transport are not. Source of truth: `ProductSpecification/technology.md`,
> `known-debt.md` #11 and #13. Verified against the code 2026-08-15.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.doklad@textery.test` / `Qa!Doklad2026` |
| Valid create body | `{"document_type": "доклад", "topic": "Влияние искусственного интеллекта на образование", "volume_pages": 5}` |
| Generation G1 | id `3f8a1d02-9c47-4b6e-8e10-5d2c7a91f430` |
| Error body shape | `{"error_code": "<CODE>", "message": "<text>"}` |
| Provider credentials | `GIGACHAT_CREDENTIALS` (required), `GIGACHAT_MODEL`, `GIGACHAT_CA_BUNDLE` |
| Staleness window | `GENERATION_STALE_AFTER_MINUTES`, default `10` |
| Attempt budget | `MAX_PROVIDER_ATTEMPTS = 2`, backoff `1.0 s` base plus up to `0.5 s` jitter |
| Generic failure text | `Не удалось сгенерировать документ. Попробуйте позже.` |

---

## 1. Database Connection Failure Handling

### TC-01-INFRA-1.1 — Generation submission fails cleanly when the database is unavailable

| Field | Value |
|---|---|
| Description | A refused Postgres connection must surface as this API's own `500` envelope, not as a driver traceback in the body — and must leave nothing half-written that a later sweep would pick up. |
| Preconditions | Backend running; account A signed in; Postgres stopped (or its port blocked) so every connection is refused. |
| Test data | Valid create body; connection refused at the adapter boundary |
| Steps | 1. Stop the database container for this repo index (never another session's).<br>2. `POST /api/v1/generations` with account A's token and the valid body.<br>3. Restart the database.<br>4. `GET /api/v1/generations` and count rows. |
| Expected result | Step 2 answers `500 Internal Server Error` with exactly `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}` — no driver message, no host name, no SQL; the server log carries the driver error with its traceback; step 4 returns `{"items": [], "next_cursor": null}` — no partial row was committed. |
| Status | Not run |

---

## 2. Database Recovery After Failure

### TC-01-INFRA-2.1 — Pending generations resume processing after the database recovers

| Field | Value |
|---|---|
| Description | A row committed just before an outage has no live job behind it once the process recovers; without the sweep it stays pending forever and the user's document never arrives. |
| Preconditions | Generation G1 committed as `pending`; the database then made unreachable and its background job lost; the database subsequently restored. |
| Test data | G1 aged past the `10`-minute staleness window; stub GigaChat server returns `200` with document text |
| Steps | 1. Create G1 and confirm it is `pending`.<br>2. Stop the database, then restart the backend so the in-process job is lost.<br>3. Restart the database.<br>4. Let the periodic sweep run (or trigger `RequeueStaleGenerations` with `older_than = now − 10 min`).<br>5. Poll `GET /api/v1/generations/{G1}`. |
| Expected result | The sweep returns G1 in its requeued list and re-triggers it; G1 moves from `pending` through `in_progress` to `completed` with the stub's `content` present; no manual intervention is needed and no duplicate document is produced. |
| Status | Not run |

---

## 3. External Service Unavailable Handling

### TC-01-INFRA-3.1 — Generation fails gracefully when the generation provider is unreachable

| Field | Value |
|---|---|
| Description | A totally-down provider is the failure mode with the longest blast radius: if the connection error escapes the job, the row is stranded in `in_progress` with no error ever written. |
| Preconditions | Generation G1 is `pending`; the stub GigaChat host refuses every connection (port closed) and counts connection attempts. |
| Test data | Connection refused on every call; budget `MAX_PROVIDER_ATTEMPTS = 2` |
| Steps | 1. Point the provider at the closed port.<br>2. Run the background job for G1.<br>3. `GET /api/v1/generations/{G1}` after the job returns.<br>4. Read the attempt count and repeat the read 15 minutes later. |
| Expected result | Exactly 2 connection attempts are made with the backoff between them; `status` is `"failed"` with `error_message` = `Не удалось сгенерировать документ. Попробуйте позже.`; the row is never left in `"pending"` or `"in_progress"`, at the first read or 15 minutes later. |
| Status | Not run |

---

## 4. Startup Configuration Validation

### TC-01-INFRA-4.1 — The application fails fast at boot when required generation-provider config is missing

| Field | Value |
|---|---|
| Description | Validating credentials lazily on the first job means the deploy looks healthy and every generation fails afterwards; the boot is the only place the failure is attributable to the deploy. |
| Preconditions | A backend instance that is not serving traffic, started with the environment below. |
| Test data | `GIGACHAT_CREDENTIALS` unset, then set to an empty string; expected message `GIGACHAT_CREDENTIALS environment variable is not set` |
| Steps | 1. Start the application with `GIGACHAT_CREDENTIALS` unset.<br>2. Read the process exit code and its stderr.<br>3. Attempt `GET /health` (or any route) against the instance.<br>4. Repeat steps 1–3 with `GIGACHAT_CREDENTIALS=""`. |
| Expected result | The process exits non-zero at startup and logs `GIGACHAT_CREDENTIALS environment variable is not set`; the port is never bound, so step 3 gets connection-refused rather than a served response; the blank-string run behaves identically to the unset run. |
| Status | Not run |

---

## 5. Reconciliation Sweep Correctness

### TC-01-INFRA-5.1 — The reconciliation sweep does not double-process the same stale generation

| Field | Value |
|---|---|
| Description | The sweep runs in every replica's lifespan, so two instances routinely list the same stale row. Without a conditional update both would re-trigger it and the provider would be paid twice for one generation. |
| Preconditions | Generation G1 is stale (`in_progress`, aged 15 minutes); two backend instances are running against the same database; the stub GigaChat server counts calls. |
| Test data | `older_than = now − 10 min`; two sweeps released simultaneously; stub call counter reset to 0 |
| Steps | 1. Seed G1 as stale.<br>2. Trigger the sweep on both instances at the same instant.<br>3. Wait for both to return, then read the stub's call count and G1's row. |
| Expected result | Exactly one sweep reports G1 in its requeued list; the loser's conditional update matches no row and is skipped without raising (logged at debug, not as a sweep failure); the stub is called exactly once for G1; exactly one document exists for it. |
| Status | Not run |

### TC-01-INFRA-5.2 — A generation whose job was silently never enqueued is still reconciled

| Field | Value |
|---|---|
| Description | The retry-exhaustion guard only fires for a job that ran. A row whose enqueue was lost has never had an attempt, so only the age-based sweep can ever reach it. |
| Preconditions | Generation G2 is committed as `pending` with the enqueue step suppressed — no background job was ever created for it. |
| Test data | G2 id `5c7e2f18-4d90-4a63-b1c2-8e64f0d27a35`, aged 15 minutes past creation; `GENERATION_STALE_AFTER_MINUTES = 10` |
| Steps | 1. Commit G2 as `pending` with the enqueue suppressed.<br>2. Confirm no job exists for it and that it is still `pending` after 15 minutes.<br>3. Run the sweep with `older_than = now − 10 min`.<br>4. Poll `GET /api/v1/generations/{G2}` to a terminal state. |
| Expected result | The sweep treats G2 exactly as it treats an abandoned `in_progress` row — it is picked up and driven to a terminal state (`completed` or `failed`, per the provider's behaviour), never left `pending`; the outcome is the same whether the row was abandoned mid-processing or never enqueued at all. |
| Status | Not run |

### TC-01-INFRA-5.3 — Resource usage returns to baseline after repeated failure and cancellation handling

| Field | Value |
|---|---|
| Description | Leaks show up only on the failure path — an unclosed `httpx` response or a session not returned to the pool costs nothing on the happy path and exhausts the pool after a few hundred failures. |
| Preconditions | Backend idle; baseline measurements taken; stub GigaChat server scripted to produce provider errors, retryable errors, and hung calls in sequence. |
| Test data | 200 generations driven through the failure paths; baseline `pg_stat_activity` connection count and the process's open socket count recorded before the run |
| Steps | 1. Record the Postgres active-connection count and the backend process's open socket count.<br>2. Drive 200 generations through the scripted failure/cancellation paths.<br>3. Wait until all 200 are terminal.<br>4. Wait 60 seconds, then re-measure both counts. |
| Expected result | All 200 generations reach `failed`; the post-run Postgres connection count is back at the recorded baseline (within the pool's idle allowance) and the open socket count is back at its baseline; neither grows with the number of failures, so nothing is leaked by the failure or cancellation handling. |
| Status | Not run |
