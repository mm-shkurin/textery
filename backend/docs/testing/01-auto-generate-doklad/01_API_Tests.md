<!-- COPIED FILE. Source of truth: ProductSpecification/stories/01-auto-generate-doklad/tests/01_API_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Auto-generate: доклад — API Tests

> **Provider and worker: read as GigaChat + `BackgroundTasks`, not OpenRouter + arq.**
> Written before 2026-07-09, when the engine was still planned as Claude via OpenRouter
> and the queue as `arq`. Neither shipped: generation goes through a direct `httpx`
> client to GigaChat (`backend/adapters/generation_provider/`), runs inline via
> FastAPI `BackgroundTasks`, and stale jobs are recovered by a periodic DB sweep —
> there is no worker process. `OPENROUTER_*` reads as the `GIGACHAT_*` credentials,
> "a stub OpenRouter server" as a stub GigaChat server. Behaviour is unchanged; the
> vendor and the transport are not. Source of truth: `ProductSpecification/technology.md`,
> `known-debt.md` #11 and #13. Verified against the code 2026-08-15.

> **Implementation Order**: Tests are numbered for sequential TDD implementation.
> Start with request validation (no infrastructure needed), then the happy-path create,
> then the mandatory re-run-safety guards, then read operations (which depend on a
> generation existing), then failure-handling, then listing.

No prerequisite-resource guards apply to this story (unlike board/column-style
dependencies elsewhere) — `POST /generations` has no parent resource that must exist
first; the only "guard" this story has is field-level validation, covered in section 1.

Endpoints: `POST /api/v1/generations`, `GET /api/v1/generations/{generation_id}`,
`GET /api/v1/generations`. Contracts: `ProductSpecification/api-specs/generations_create.yaml`,
`generations_get.yaml`, `generations_list.yaml`.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.doklad@textery.test` / `Qa!Doklad2026` |
| Account B (a stranger) | `qa.other@textery.test` / `Qa!Other2026` |
| Access token | `Authorization: Bearer <access token of account A>` |
| Valid create body | `{"document_type": "доклад", "topic": "Влияние искусственного интеллекта на образование", "volume_pages": 5, "requirements": "Три раздела и вывод", "extra_wishes": "Простой язык"}` |
| Generation G1 | id `3f8a1d02-9c47-4b6e-8e10-5d2c7a91f430`, created from the body above |
| Idempotency key | `Idempotency-Key: gen-key-1` |
| Error body shape | `{"error_code": "<CODE>", "message": "<text>"}` |
| Bounds | `topic` ≤ 500 chars, `volume_pages` 1–10, `requirements` ≤ 2000, `extra_wishes` ≤ 2000 |

---

## 1. Create Generation — Validation

### TC-01-API-1.1 — Reject request with missing topic

| Field | Value |
|---|---|
| Description | Topic is the only free-text input the prompt cannot be built without; accepting a body without it would enqueue a job that can never be phrased. |
| Preconditions | Account A signed in; no generation exists for account A. |
| Test data | Body `{"document_type": "доклад", "volume_pages": 5}` — `topic` omitted entirely |
| Steps | 1. `POST /api/v1/generations` with account A's Bearer token and the body above.<br>2. `GET /api/v1/generations` with the same token. |
| Expected result | `400 Bad Request`; body `{"error_code": "VALIDATION_ERROR", "message": "topic is required"}`; step 2 returns `{"items": [], "next_cursor": null}` — no generation was created. |
| Status | Not run |

### TC-01-API-1.2 — Reject request with out-of-range volume

| Field | Value |
|---|---|
| Description | `volume_pages` drives the provider's length budget and therefore the spend; a 0 or an 11 must be refused at the boundary rather than clamped silently. |
| Preconditions | Account A signed in; no generation exists for account A. |
| Test data | Valid body with `volume_pages: 0`, then the same body with `volume_pages: 11` |
| Steps | 1. `POST /api/v1/generations` with `volume_pages: 0`.<br>2. `POST /api/v1/generations` with `volume_pages: 11`.<br>3. `GET /api/v1/generations`. |
| Expected result | Both posts answer `400 Bad Request` with `{"error_code": "VALIDATION_ERROR", "message": "volume_pages must be between 1 and 10"}`; step 3 returns `{"items": [], "next_cursor": null}`. |
| Status | Not run |

### TC-01-API-1.3 — Reject requirements/extra_wishes exceeding the length limit

| Field | Value |
|---|---|
| Description | Free text goes straight into a paid provider prompt; without a server-side cap the request body sets the bill. |
| Preconditions | Account A signed in; no generation exists for account A. |
| Test data | Valid body with `requirements` = `"a"` repeated 2001 times, then valid body with `extra_wishes` = `"a"` repeated 2001 times |
| Steps | 1. `POST /api/v1/generations` with the 2001-character `requirements`.<br>2. `POST /api/v1/generations` with the 2001-character `extra_wishes`.<br>3. `GET /api/v1/generations`. |
| Expected result | Step 1: `400` with `{"error_code": "VALIDATION_ERROR", "message": "requirements must be at most 2000 characters"}`. Step 2: `400` with `"extra_wishes must be at most 2000 characters"`. Step 3 returns `{"items": [], "next_cursor": null}`. |
| Status | Not run |

### TC-01-API-1.4 — Reject unsupported document type

| Field | Value |
|---|---|
| Description | The prompt template is chosen server-side from `document_type`; a value outside the allowlist must be refused, never quietly replaced by `доклад`, which would bill the user for a document they did not ask for. |
| Preconditions | Account A signed in. |
| Test data | Valid body with `document_type: "диссертация"`; allowlist is `доклад, эссе, сочинение, реферат` |
| Steps | 1. `POST /api/v1/generations` with `document_type: "диссертация"`.<br>2. `GET /api/v1/generations` and inspect any created row. |
| Expected result | `422 Unprocessable Entity`; body `{"error_code": "INVALID_DOCUMENT_TYPE", "message": "document_type must be one of: доклад, эссе, сочинение, реферат"}`; no generation exists, and none carries `document_type: "доклад"`. |
| Status | Not run |
| Note | All four allowlisted types answer `201` — see `generations_create.yaml`, which corrected an earlier single-value enum. Only a value outside the allowlist is a `422`. |

### TC-01-API-1.5 — Ignore server-owned fields in the request body

| Field | Value |
|---|---|
| Description | `status` and `id` are server-assigned. A body that could set them would let a caller mint a "completed" generation or collide with an existing id. |
| Preconditions | Account A signed in. |
| Test data | Valid body plus `"status": "completed"` and `"id": "00000000-0000-4000-8000-000000000000"` |
| Steps | 1. `POST /api/v1/generations` with the body above.<br>2. Read `generation_id` and `status` from the response.<br>3. `GET /api/v1/generations/{generation_id}`. |
| Expected result | `201 Created`; the response `status` is `"pending"`, not `"completed"`; `generation_id` is a server-generated UUID and is **not** `00000000-0000-4000-8000-000000000000`; step 3 confirms the same two values from storage. |
| Status | Not run |

### TC-01-API-1.6 — Ignore a client-supplied creation timestamp

| Field | Value |
|---|---|
| Description | `created_at` is the keyset feed's sort key. A client-settable timestamp would let a caller pin a row permanently at the top of the history. |
| Preconditions | Account A signed in; the tester notes the current UTC time before step 1. |
| Test data | Valid body plus `"created_at": "2000-01-01T00:00:00Z"` |
| Steps | 1. Record the current UTC time `T0`.<br>2. `POST /api/v1/generations` with the body above.<br>3. Read `created_at` from the `201` response. |
| Expected result | `201 Created`; `created_at` is at or after `T0` (server time, within seconds of it), never `2000-01-01T00:00:00Z`. |
| Status | Not run |

### TC-01-API-1.7 — Accept and reject requirements/extra_wishes length limits for Cyrillic text

| Field | Value |
|---|---|
| Description | The 2000 limit is counted in codepoints. Counting UTF-8 bytes instead would refuse a Cyrillic text at roughly 1000 characters — half the documented allowance. |
| Preconditions | Account A signed in. |
| Test data | `requirements` = the letter `я` repeated 2000 times (4000 UTF-8 bytes), then repeated 2001 times |
| Steps | 1. `POST /api/v1/generations` with the 2000-character Cyrillic `requirements`.<br>2. `POST /api/v1/generations` with the 2001-character Cyrillic `requirements`. |
| Expected result | Step 1: `201 Created` with `status: "pending"`. Step 2: `400` with `{"error_code": "VALIDATION_ERROR", "message": "requirements must be at most 2000 characters"}`. |
| Status | Not run |

---

## 2. Create Generation — Happy Path

### TC-01-API-2.1 — Valid request is accepted and queued without waiting on the LLM call

| Field | Value |
|---|---|
| Description | The provider call takes tens of seconds. If it ran inside the request cycle the client would block on it and a connection would be held for the whole generation. |
| Preconditions | Account A signed in; the stub GigaChat server is configured to hold its response for 5 seconds. |
| Test data | The valid create body; stub provider delay `5 s` |
| Steps | 1. `POST /api/v1/generations` with the valid body and account A's token, measuring wall-clock time.<br>2. Read the response body. |
| Expected result | `201 Created` in well under the stub's 5 s delay (< 1 s); body carries `generation_id` (a UUID), `status: "pending"`, `document_type: "доклад"`, `topic`, `volume_pages: 5`, `created_at`; no document content is present. |
| Status | Not run |

### TC-01-API-2.2 — An entirely Cyrillic request round-trips without corruption

| Field | Value |
|---|---|
| Description | A wrong encoding anywhere on the path (request parse, column collation, JSON response) shows up as `?` or `Ð` and would reach both the stored prompt and the user's screen. |
| Preconditions | Account A signed in; stub GigaChat server returns a fixed Cyrillic document. |
| Test data | `topic` = `Влияние искусственного интеллекта на образование`, `requirements` = `Три раздела, обязательно вывод`, `extra_wishes` = `Простой язык, без канцелярита` |
| Steps | 1. `POST /api/v1/generations` with the Cyrillic body.<br>2. `GET /api/v1/generations/{generation_id}` and compare each echoed field with what was sent. |
| Expected result | `201`, then `200`; `topic`, `requirements` and `extra_wishes` come back byte-identical to what was sent; no `?`, no `�`, no `Ð`-style mojibake anywhere in the response. |
| Status | Not run |

---

## 3. Create Generation — Re-run Safety (idempotency)

### TC-01-API-3.1 — Replaying the same idempotency key does not create a duplicate generation

| Field | Value |
|---|---|
| Description | A retried POST — a flaky network, a double click, a client-side retry — must not bill the user twice for the same document. |
| Preconditions | Account A signed in; no generation exists for account A. |
| Test data | The valid create body, sent twice with the identical header `Idempotency-Key: gen-key-1` |
| Steps | 1. `POST /api/v1/generations` with `Idempotency-Key: gen-key-1`; record `generation_id`.<br>2. `POST /api/v1/generations` with the identical body and the identical `Idempotency-Key: gen-key-1`.<br>3. `GET /api/v1/generations`. |
| Expected result | Step 1: `201 Created`. Step 2: `200 OK` (never `201`) carrying the **same** `generation_id` as step 1. Step 3: `items` has exactly one entry. |
| Status | Not run |

### TC-01-API-3.2 — A redelivered background job does not reprocess an already-progressing generation

| Field | Value |
|---|---|
| Description | The status move is a compare-and-swap gated on the prior status. Without it a redelivered job would call the paid provider a second time and produce a second document for one generation. |
| Preconditions | Generation G1 exists with `status = in_progress`, already claimed by a first worker that has not finished. |
| Test data | Generation G1 id `3f8a1d02-9c47-4b6e-8e10-5d2c7a91f430`; the same background job dispatched a second time while the first is still running |
| Steps | 1. Dispatch the background job for G1 and let it claim the row (`in_progress`).<br>2. Dispatch the identical job for G1 again before the first completes.<br>3. When both have returned, read G1 and count the documents referencing it. |
| Expected result | Exactly one of the two claims succeeds — the second CAS finds a status other than `pending` and does not proceed; exactly one document exists for G1; G1's final `status` is a single `completed`. |
| Status | Not run |

---

## 4. Get Generation Status

### TC-01-API-4.1 — A pending generation reports its status without document content

| Field | Value |
|---|---|
| Description | The client starts polling the instant the `201` lands. A `404` in that window — a read hitting an uncommitted or lagging row — would look to the user like the generation was lost. |
| Preconditions | Account A signed in; stub GigaChat server holds its response for 10 seconds so the row stays pending. |
| Test data | The valid create body; poll issued immediately (< 200 ms) after the `201` |
| Steps | 1. `POST /api/v1/generations`; record `generation_id`.<br>2. Immediately `GET /api/v1/generations/{generation_id}` with account A's token. |
| Expected result | `200 OK`, never `404`; body `status` is `"pending"`; `content` is `null`; `error_message` is `null`. |
| Status | Not run |

### TC-01-API-4.2 — A completed generation includes the document content

| Field | Value |
|---|---|
| Description | There is no separate get-document endpoint — this response is the only place the finished text is delivered. |
| Preconditions | Generation G1 has been processed to `completed` by the stub provider. |
| Test data | Generation G1 id `3f8a1d02-9c47-4b6e-8e10-5d2c7a91f430`; stub provider text `Доклад о влиянии ИИ на образование. Введение...` |
| Steps | 1. Poll `GET /api/v1/generations/3f8a1d02-9c47-4b6e-8e10-5d2c7a91f430` until `status` is `"completed"`.<br>2. Read the `content` field. |
| Expected result | `200 OK`; `status` is `"completed"`; `content` is non-null and equals the stub provider's returned text; `error_message` is `null`. |
| Status | Not run |

### TC-01-API-4.3 — Requesting a non-existent generation reports not found

| Field | Value |
|---|---|
| Description | An unknown id must answer a clean `404` in the canonical envelope, not a `500` from an unhandled `None`, and must not name the resource kind or the id. |
| Preconditions | Account A signed in; no generation exists with the id below. |
| Test data | `generation_id = 00000000-0000-4000-8000-000000000000` |
| Steps | 1. `GET /api/v1/generations/00000000-0000-4000-8000-000000000000` with account A's token. |
| Expected result | `404 Not Found`; body exactly `{"error_code": "NOT_FOUND", "message": "The requested resource was not found."}`; the id does not appear in the body. |
| Status | Not run |

---

## 5. Generation Lifecycle — Failure Handling

### TC-01-API-5.1 — A permanent generation-provider error fails fast without exhausting retries

| Field | Value |
|---|---|
| Description | A 4xx from the provider means the request itself is wrong; retrying it phrases the identical request again, spending the budget and the wait on an outcome that cannot change. |
| Preconditions | Generation G1 is `pending`; stub GigaChat server returns `400` for every call and counts calls. |
| Test data | Stub provider response `400`; attempt budget `MAX_PROVIDER_ATTEMPTS = 2` |
| Steps | 1. Reset the stub's call counter.<br>2. Run the background job for G1.<br>3. `GET /api/v1/generations/{G1}`.<br>4. Read the stub's call count. |
| Expected result | `status` is `"failed"`; `error_message` is `"Не удалось сгенерировать документ. Попробуйте позже."`; the stub was called once for a non-retryable rejection — no further attempt is made for G1. |
| Status | Not run |

### TC-01-API-5.2 — A transient generation-provider error is retried and can still succeed

| Field | Value |
|---|---|
| Description | A single 5xx or timeout is the provider's most common failure. Treating it as terminal would fail generations that a one-second wait would have completed. |
| Preconditions | Generation G1 is `pending`; stub GigaChat server returns `503` on the first call and `200` with document text on the second. |
| Test data | Stub script `[503, 200]`; backoff base `1.0 s` plus jitter up to `0.5 s`; budget 2 attempts |
| Steps | 1. Run the background job for G1.<br>2. Poll `GET /api/v1/generations/{G1}` until terminal. |
| Expected result | The stub records exactly 2 calls; final `status` is `"completed"`; `content` equals the second call's text; `error_message` is `null`. |
| Status | Not run |

### TC-01-API-5.3 — Exhausting the retry budget fails the generation, never leaves it stuck

| Field | Value |
|---|---|
| Description | A row abandoned in `in_progress` gives the user a spinner with no end. The budget must terminate in a written `failed`, not in silence. |
| Preconditions | Generation G1 is `pending`; stub GigaChat server returns `503` for every call. |
| Test data | Stub script `[503, 503]`; budget 2 attempts |
| Steps | 1. Run the background job for G1.<br>2. After the job returns, `GET /api/v1/generations/{G1}`. |
| Expected result | The stub records exactly 2 calls and no third; `status` is `"failed"` — not `"pending"`, not `"in_progress"`; `error_message` is `"Не удалось сгенерировать документ. Попробуйте позже."`; a repeat read minutes later shows the same terminal `failed`. |
| Status | Not run |

### TC-01-API-5.4 — A generation abandoned by a dead worker is eventually reconciled

| Field | Value |
|---|---|
| Description | `BackgroundTasks` is not durable across a process restart: a job killed mid-run writes nothing, so no retry-exhaustion error ever occurs and the row would sit in `in_progress` forever. |
| Preconditions | Generation G1 is written directly to storage with `status = in_progress` and timestamps older than the staleness window; no job is running for it. |
| Test data | `GENERATION_STALE_AFTER_MINUTES = 10` (default); G1 timestamped 15 minutes in the past |
| Steps | 1. Seed G1 as above.<br>2. Trigger the reconciliation sweep (`RequeueStaleGenerations`) with `older_than = now − 10 min`.<br>3. `GET /api/v1/generations/{G1}`. |
| Expected result | The sweep picks G1 up and transitions it out of the abandoned `in_progress` state without any retry-exhaustion error having occurred; G1 subsequently reaches a terminal state and is never left stuck. |
| Status | Not run |
| Note | The shipped sweep requeues a stale row to `pending` and re-triggers it, from where the normal bounded-retry path takes it to `completed` or `failed`; the original wording ("reconciled to failed") predates that implementation. |

### TC-01-API-5.5 — A generation still within its normal processing window is not prematurely reconciled

| Field | Value |
|---|---|
| Description | A sweep window shorter than the real processing time would fail healthy generations mid-flight and re-run them, doubling provider spend. |
| Preconditions | Generation G1 is `in_progress`, timestamped 9 minutes in the past — inside the 10-minute window. |
| Test data | `GENERATION_STALE_AFTER_MINUTES = 10`; G1 age `9 min`; sweep called with `older_than = now − 10 min` |
| Steps | 1. Seed G1 as above and record its `status` and timestamps.<br>2. Run the sweep once.<br>3. `GET /api/v1/generations/{G1}` and compare. |
| Expected result | The sweep returns an empty requeue list; G1's `status` is still `"in_progress"` and its timestamps are unchanged; it is not moved to `"failed"`. |
| Status | Not run |

### TC-01-API-5.6 — A worker's genuine completion is never clobbered by a concurrent reconciliation sweep

| Field | Value |
|---|---|
| Description | Without a status-gated conditional update, a sweep that read the row a moment before the worker committed would overwrite a real result with a failure — the user watches a finished document turn into an error. |
| Preconditions | Generation G1 is `in_progress` and sits exactly at the staleness boundary; the worker's completion write and the sweep's write are released simultaneously. |
| Test data | G1 id `3f8a1d02-9c47-4b6e-8e10-5d2c7a91f430`; both writes are CAS updates gated on `status = in_progress` |
| Steps | 1. Arrange the worker's completion write and the sweep's write to fire at the same instant against G1.<br>2. Release both.<br>3. `GET /api/v1/generations/{G1}` after both return. |
| Expected result | Exactly one write is applied — the loser's CAS matches no row and is skipped, not retried over the winner; if the completion won, `status` is `"completed"` with the generated `content` intact and is never subsequently overwritten to `"failed"`. |
| Status | Not run |

---

## 6. List Generations

### TC-01-API-6.1 — Listing returns generations across all callers, most recent page first

| Field | Value |
|---|---|
| Description | The history feed is the only way a user finds an earlier generation; it must return rows and hand back the anchor for the next page. |
| Preconditions | Several generations exist, created by more than one caller. |
| Test data | 3 generations from account A and 2 from account B, all created within the last hour; `limit` left at the default `20` |
| Steps | 1. `POST /api/v1/generations` three times as account A and twice as account B.<br>2. `GET /api/v1/generations` and read `items` and `next_cursor`. |
| Expected result | `200 OK`; body shape `{"items": [...], "next_cursor": ...}`; `items` are ordered newest first (`created_at DESC, id DESC`); each item carries `generation_id`, `status`, `document_type`, `topic`, `volume_pages`, `created_at` and no document content; `next_cursor` is a string when more rows remain and `null` when they do not. |
| Status | Not run |
| Note | `generations_list.yaml` scopes the feed to the Bearer token's account — the unscoped "across all callers" premise expired when story 7 shipped auth. Read step 2 as "regardless of which flow created them, within the caller's own rows". |

### TC-01-API-6.2 — Paginating with a cursor is stable while new generations are being created

| Field | Value |
|---|---|
| Description | An offset-based page shifts when a row is inserted ahead of it, so a row is either shown twice or skipped entirely. The keyset cursor is what makes the second page a continuation of the first read, not of the current table. |
| Preconditions | 25 generations exist for account A, created in a known order. |
| Test data | `limit=10`; one extra generation created between the two reads |
| Steps | 1. `GET /api/v1/generations?limit=10`; record the 10 `generation_id`s and `next_cursor`.<br>2. `POST /api/v1/generations` to create a new, newest generation.<br>3. `GET /api/v1/generations?limit=10&cursor={next_cursor}`. |
| Expected result | The step-3 `items` share no `generation_id` with step 1; the step-3 ids are exactly the 11th–20th rows of the ordering as it stood at step 1 — the newly created row appears in neither page, and no pre-existing row is skipped. |
| Status | Not run |

### TC-01-API-6.3 — The list caps its page size even when far more generations exist

| Field | Value |
|---|---|
| Description | Without a server-side cap, one request over a long history serializes the whole table into a single response. |
| Preconditions | 150 generations exist for account A. |
| Test data | `DEFAULT_LIMIT = 20`, `MAX_LIMIT = 100`; requests with no `limit`, with `limit=100`, and with `limit=101` |
| Steps | 1. `GET /api/v1/generations` (no `limit`).<br>2. `GET /api/v1/generations?limit=100`.<br>3. `GET /api/v1/generations?limit=101`. |
| Expected result | Step 1 returns exactly 20 items; step 2 returns exactly 100; step 3 answers `400` with `{"error_code": "INVALID_LIMIT", "message": "limit must be between 1 and 100."}`; no response ever carries all 150 rows. |
| Status | Not run |

### TC-01-API-6.4 — Generations with the same creation timestamp still list in a stable order

| Field | Value |
|---|---|
| Description | `created_at` alone is not unique. Ordering by it only leaves ties resolved by whatever the planner returns, so a page boundary landing between two tied rows drops or repeats one. |
| Preconditions | Two generations exist for account A with a byte-identical `created_at`. |
| Test data | Generations `a1b2c3d4-0000-4000-8000-000000000001` and `a1b2c3d4-0000-4000-8000-000000000002`, both `created_at = 2026-08-20T10:00:00Z`; order key `created_at DESC, id DESC` |
| Steps | 1. Insert the two rows above with the identical timestamp.<br>2. `GET /api/v1/generations` and record the relative order of the two ids.<br>3. Repeat step 2 five times. |
| Expected result | The two ids appear in the same relative order on every one of the six reads — `...0002` before `...0001`, per the `id DESC` tiebreak; neither is ever missing or duplicated. |
| Status | Not run |
