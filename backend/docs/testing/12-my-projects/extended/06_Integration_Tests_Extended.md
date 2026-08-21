<!-- COPIED FILE. Source of truth: ProductSpecification/stories/12-my-projects/tests/extended/06_Integration_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Мои проекты — Integration Tests (Extended)

Shared test data is inherited from `06_Integration_Tests.md`: account A `qa.projects@textery.test`,
source generation S `c72e5a90-3b14-4d6f-9e88-01af4c2d7b65` (`failed`, `реферат`,
`Влияние климата на урожай`, 10 pages), second source S2 `1f6c3b85-92d0-47ae-b4c1-08e5d7a26f39`,
the arq generation queue, the provider Fake with its call counter, the
`RequeueStaleGenerations` sweep at `GENERATION_STALE_AFTER_MINUTES=10`, and the retry ceiling of 5.

---

## 1. Queue and Worker

### TC-12-INT-EXT-1.1 — A job enqueued for a retry survives a queue restart

| Field | Value |
|---|---|
| Description | A job held only in memory is lost on a broker restart, and the generation sits `pending` forever with nothing behind it — paid work that never runs and cannot be retried. |
| Preconditions | Account A retried source S producing generation `N`; the job for `N` is enqueued and not yet claimed. |
| Test data | Generation `N`; restart via the compose stack (`infra/docker-compose.yml`, ports from `infra/.env`). |
| Steps | 1. Confirm the job for `N` is on the queue.<br>2. Restart the queue service.<br>3. Let the worker drain and read `N`'s status. |
| Expected result | The job for `N` is still present after the restart and is processed exactly once; `N` reaches a terminal status (`completed` or `failed`); the provider Fake records exactly 1 call for `N`. |
| Status | Not run |

### TC-12-INT-EXT-1.2 — A worker that crashes mid-run leaves the row to the sweep, not to the user

| Field | Value |
|---|---|
| Description | A crashed run leaves a non-terminal row; the user must be told it is recovering rather than offered a retry that would duplicate work the sweep is about to requeue. |
| Preconditions | Account A's retried generation `N` is `in_progress` when its worker crashes; nothing marks it terminal. |
| Test data | `GENERATION_STALE_AFTER_MINUTES=10`; the clock advanced past the threshold. |
| Steps | 1. Crash the worker mid-run for `N`.<br>2. Advance past the stale threshold.<br>3. `GET /api/v1/projects?limit=100` with account A's token.<br>4. Attempt `POST /api/v1/generations/{N}/retry` with a fresh key. |
| Expected result | The feed reports `N` with `"status":"recovering","retryable":false`; the card offers no retry action; step 4 answers `409 Conflict` with `{"error_code":"GENERATION_NOT_FAILED", …}`. |
| Status | Not run |

### TC-12-INT-EXT-1.3 — The worker's completion writes the document under the same owner as the source

| Field | Value |
|---|---|
| Description | The owner travels from the source row through the job to the document; if the worker resolves it from anything else, one account's retry produces another account's document. |
| Preconditions | Account A owns source S; account B also owns failed generations, so more than one owner is present in the queue. |
| Test data | `Idempotency-Key: k-extint13`; account A owner id `11f8c3a5-6d20-4e97-8b41-0c7a25e93d68`. |
| Steps | 1. Retry source S as account A.<br>2. Let the worker complete generation `N` and write its document `D`.<br>3. Read `D`'s owner, and `GET /api/v1/projects` as account B. |
| Expected result | `D`'s `owner_id` is `11f8c3a5-6d20-4e97-8b41-0c7a25e93d68` (account A); `D` appears in account A's feed; account B's feed does not contain `D`. |
| Status | Not run |

### TC-12-INT-EXT-1.4 — Two retries of different sources by one account both run

| Field | Value |
|---|---|
| Description | Guards written per-account rather than per-source would collapse two legitimate retries into one — the idempotency constraint is `(owner_id, key)`, and distinct keys must stay distinct. |
| Preconditions | Account A owns failed sources S and S2, both under the ceiling. |
| Test data | `Idempotency-Key: k-extint14a` for S and `k-extint14b` for S2. |
| Steps | 1. `POST /api/v1/generations/c72e5a90-…/retry` with `k-extint14a`.<br>2. `POST /api/v1/generations/1f6c3b85-…/retry` with `k-extint14b`.<br>3. Read the queue. |
| Expected result | Both answer `201 Created` with distinct generation ids; two new `generations` rows exist for account A; exactly two jobs are on the queue, one naming each new generation. |
| Status | Not run |

---

## 2. Provider Behaviour

### TC-12-INT-EXT-2.1 — Retrying a generation whose source parameters are no longer supported fails cleanly

| Field | Value |
|---|---|
| Description | Parameters are copied from a row written under an older catalogue; if the retry accepts a value the flow can no longer serve, the job is enqueued only to fail at the worker after the money is committed. |
| Preconditions | Account A owns a failed generation created with `document_type = курсовая`, a type no longer offered. |
| Test data | Generation `3c9f5a71-84e2-4b06-9d17-6a2058e4c13b`, `document_type=курсовая`; `Idempotency-Key: k-extint21`. |
| Steps | 1. `POST /api/v1/generations/3c9f5a71-…/retry` with that key.<br>2. Read the response body.<br>3. Inspect the queue. |
| Expected result | The request is refused with a stated reason in the `{error_code, message}` envelope (a `4xx`, not a `500` and not a `201`); no job is enqueued; no new generation row is created. |
| Status | Not run |

### TC-12-INT-EXT-2.2 — A provider rate-limit answer marks the retry failed, not lost

| Field | Value |
|---|---|
| Description | A rate-limit answer that leaves the row non-terminal shows in the feed as still running, and the user cannot retry a row that is not `failed`. |
| Preconditions | Account A owns source S; the provider Fake answers with its rate-limit refusal. |
| Test data | `Idempotency-Key: k-extint22`; provider Fake configured to rate-limit. |
| Steps | 1. Retry source S with that key.<br>2. Let the worker run and the provider refuse.<br>3. `GET /api/v1/projects?limit=100`. |
| Expected result | The new generation `N` reaches terminal `status=failed` (never left `pending` or `in_progress`); the feed lists it as `{"status":"failed","retryable":true}`, so the user can retry it again within the ceiling. |
| Status | Not run |

### TC-12-INT-EXT-2.3 — A provider answer in an unexpected shape fails closed

| Field | Value |
|---|---|
| Description | Storing whatever the provider sent, unparsed, puts unvalidated third-party content into a document the app renders — fail closed instead. |
| Preconditions | Account A owns source S; the provider Fake returns content the flow cannot parse (truncated JSON / an unexpected schema). |
| Test data | Provider response `{"choices": ` (truncated); `Idempotency-Key: k-extint23`. |
| Steps | 1. Retry source S with that key.<br>2. Let the worker process the unparsable answer.<br>3. Read the generation's status and query for any document created from it. |
| Expected result | The generation ends terminal `status=failed`; no document exists for it; nothing unparsed from the provider response is stored in `generations` or `documents`; the feed lists the row as `failed` and retryable. |
| Status | Not run |

---

## 3. Cross-Flow

### TC-12-INT-EXT-3.1 — A retry that completes can be converted like any generation

| Field | Value |
|---|---|
| Description | A retry's generation must be an ordinary generation downstream; a lineage column that the conversion path does not expect would make retried work unconvertible. |
| Preconditions | Account A's retry generation `N` reached `completed` with `source_generation_id = c72e5a90-…` and no document yet. |
| Test data | `POST /api/v1/documents/from-generation` with generation id `N`. |
| Steps | 1. `GET /api/v1/projects?limit=100` and confirm `N` is listed as a generation.<br>2. `POST /api/v1/documents/from-generation` for `N`; record the document id `D`.<br>3. `GET /api/v1/projects?limit=100` again. |
| Expected result | Step 2 succeeds and creates document `D`; after it, the feed shows `{"kind":"document","id":"<D>"}` and no longer shows `kind:"generation"` with id `N`; the failed source `c72e5a90-…` is still listed separately. |
| Status | Not run |

### TC-12-INT-EXT-3.2 — Deprecated list endpoints keep answering while the feed is used

| Field | Value |
|---|---|
| Description | `deprecated: true` is documentation, not a behaviour change; a client still on the old endpoints must keep working alongside the new feed. |
| Preconditions | Account A owns documents and generations, some with `idempotency_key IS NULL`; the projects feed is in active use. |
| Test data | `GET /api/v1/documents`, `GET /api/v1/generations`, no new parameters. |
| Steps | 1. Issue `GET /api/v1/projects?limit=100` repeatedly in the background.<br>2. `GET /api/v1/documents` with account A's token.<br>3. `GET /api/v1/generations` with account A's token. |
| Expected result | Steps 2 and 3 answer `200 OK` with their contracts' previous response shapes field for field — no added required field, no removed one, no new required parameter; the keyless generations are listed; the concurrent feed requests are unaffected. |
| Status | Not run |

---

## DSL Technical Reference

Inherits `06_Integration_Tests.md`.
