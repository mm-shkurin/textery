# Auto-generate: доклад — Integration Tests

> **Provider and worker: read as GigaChat + `BackgroundTasks`, not OpenRouter + arq.**
> Written before 2026-07-09, when the engine was still planned as Claude via OpenRouter
> and the queue as `arq`. Neither shipped: generation goes through a direct `httpx`
> client to GigaChat (`backend/adapters/generation_provider/`), runs inline via
> FastAPI `BackgroundTasks`, and stale jobs are recovered by a periodic DB sweep —
> there is no worker process. `OPENROUTER_*` reads as the `GIGACHAT_*` credentials,
> "a stub OpenRouter server" as a stub GigaChat server. Behaviour is unchanged; the
> vendor and the transport are not. Source of truth: `ProductSpecification/technology.md`,
> `known-debt.md` #11 and #13. Verified against the code 2026-08-15.

Covers the worker ↔ external generation-provider integration (arq job → OpenRouter →
Document/status), including the outbound half of the idempotency guarantee from
`01_API_Tests.md` section 3 — re-run safety is mandatory in both files whenever an
external system is involved.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the owner) | `qa.doklad@textery.test` / `Qa!Doklad2026` |
| Generation G1 | id `3f8a1d02-9c47-4b6e-8e10-5d2c7a91f430`, `topic` `Влияние искусственного интеллекта на образование`, `volume_pages` 5, `document_type` `доклад` |
| Stub provider | a stub GigaChat server that records every request body and its own call count |
| Stub success body | `Доклад о влиянии ИИ на образование. Введение...` |
| Attempt budget | `MAX_PROVIDER_ATTEMPTS = 2` |
| Backoff | `1.0 s` base, doubling per retry, plus uniform jitter in `[0, 0.5 s]` |
| Generic failure text | `Не удалось сгенерировать документ. Попробуйте позже.` |

---

## 1. Generation Provider — Success Flow

### TC-01-INT-1.1 — A successful provider call produces a completed document

| Field | Value |
|---|---|
| Description | The end-to-end contract of the background job: a `200` from the provider must land as stored content and a `completed` status, not just a status with nothing behind it. |
| Preconditions | Generation G1 is `pending`; the stub provider returns `200` with the success body. |
| Test data | G1 id `3f8a1d02-9c47-4b6e-8e10-5d2c7a91f430`; stub response `200`, body = the stub success body |
| Steps | 1. Run the background job for G1.<br>2. `GET /api/v1/generations/3f8a1d02-9c47-4b6e-8e10-5d2c7a91f430`.<br>3. Read the stored document for G1. |
| Expected result | The stub records exactly 1 call; `status` is `"completed"`; `content` equals the stub success body character for character; a document row exists for G1 carrying that same content; `error_message` is `null`. |
| Status | Not run |

### TC-01-INT-1.2 — The requested volume converts to a pinned, tested prompt budget for Cyrillic text

| Field | Value |
|---|---|
| Description | The pages-to-budget conversion is the only link between what the user asked for and what is paid for. Assuming Latin-script density silently halves a Cyrillic document, because the same character count costs more tokens. |
| Preconditions | Two pending generations exist for account A, identical apart from volume; the stub provider records each request body. |
| Test data | G-min: `volume_pages: 1`; G-max: `volume_pages: 10`; both with `topic` = `Влияние искусственного интеллекта на образование` and `requirements` = `Три раздела, обязательно вывод, только на русском`; the documented pages→budget constant |
| Steps | 1. Run the background job for G-min and capture the request the stub received.<br>2. Run the background job for G-max and capture its request.<br>3. Compute the expected budget for 1 and for 10 pages from the pinned conversion constant.<br>4. Compare each captured request's length budget against its expected value. |
| Expected result | Each captured request carries the length budget the pinned constant yields for its `volume_pages` — exact equality, not a range; the two budgets differ by the constant's own factor between 1 and 10 pages; the expected values were derived for Cyrillic text and are asserted as such, not inherited from a Latin-script assumption. |
| Status | Not run |

---

## 2. Generation Provider — Error Handling

### TC-01-INT-2.1 — Permanent and transient provider errors are handled differently

| Field | Value |
|---|---|
| Description | Retrying a `4xx` re-sends the identical unacceptable request and cannot succeed; not retrying a `5xx` fails a generation a one-second wait would have completed. Treating both the same is wrong in one direction or the other. |
| Preconditions | Two pending generations exist; the stub provider is scripted per case and counts calls. |
| Test data | G-perm: stub always `400`. G-trans: stub `503` then `200`. Budget 2 attempts; backoff `1.0 s` + jitter |
| Steps | 1. Reset the stub counter and run the job for G-perm.<br>2. Read G-perm's status and the stub's call count.<br>3. Reset the counter and run the job for G-trans, timing the gap between the two calls.<br>4. Read G-trans's status and call count. |
| Expected result | G-perm: exactly 1 call — the retry budget is not consumed — and `status` is `"failed"` immediately. G-trans: exactly 2 calls separated by at least the `1.0 s` backoff, and `status` is `"completed"` with the second call's content. |
| Status | Not run |

### TC-01-INT-2.2 — A malformed or empty provider response is treated as a failure

| Field | Value |
|---|---|
| Description | A `200` with nothing usable in it is the worst outcome to accept: the user gets an empty document marked "completed" and no error anywhere. |
| Preconditions | Two pending generations exist; the stub provider returns the malformed shapes below. |
| Test data | G-empty: `200` with body `""`. G-malformed: `200` with body `not json at all`. Both with `Content-Type: application/json` |
| Steps | 1. Run the job for G-empty.<br>2. Run the job for G-malformed.<br>3. `GET /api/v1/generations/{id}` for each.<br>4. Check whether a document row was created for either. |
| Expected result | Both reach `status: "failed"` with `error_message` = `Не удалось сгенерировать документ. Попробуйте позже.`; neither is `"completed"`; no document row exists for either, and neither carries empty-string content. |
| Status | Not run |

### TC-01-INT-2.3 — Each failure family is recorded with a distinguishable category server-side

| Field | Value |
|---|---|
| Description | The client-facing `failed` is deliberately opaque, which leaves operations with no way to tell a rate limit from a content-policy rejection unless the category is recorded server-side. |
| Preconditions | Four pending generations exist; log capture enabled; the stub provider is scripted with one failure shape per generation. |
| Test data | G-rate: stub `429`. G-policy: stub `400` with a content-policy body. G-timeout: stub holds past the read timeout. G-malformed: stub `200` with an unparseable body |
| Steps | 1. Run the job for each of the four generations.<br>2. Read the captured log records for each generation id.<br>3. `GET /api/v1/generations/{id}` for all four and read `status`. |
| Expected result | Each generation's log records carry a failure category distinguishable from the other three (rate-limit, content-policy, timeout, malformed-response are four different values, not one shared string); every one of the four API responses reports the same bare `status: "failed"` with the identical generic `error_message`, so the category is visible server-side only. |
| Status | Not run |

---

## 3. Generation Provider — Timeout Handling

### TC-01-INT-3.1 — A hung provider call is cancelled at the job deadline

| Field | Value |
|---|---|
| Description | A client-side timeout that abandons the response while the socket stays open leaks a connection per hung call and still bills for the completion. The call has to be cancelled, not merely stopped waiting on. |
| Preconditions | Generation G1 is `pending`; the stub provider accepts the connection and never responds; the stub reports open connections. |
| Test data | Stub holds the connection open indefinitely; the job's configured deadline; open-socket count sampled before and after |
| Steps | 1. Record the stub's open-connection count.<br>2. Run the background job for G1 against the hanging stub.<br>3. Wait until the job returns at its deadline.<br>4. Re-read the stub's open-connection count and `GET /api/v1/generations/{G1}`. |
| Expected result | The job returns at its deadline rather than hanging; the stub observes the connection closed by the client at that moment — the open-connection count returns to its pre-run value, so nothing is left running server-side; G1's `status` is `"failed"` with the generic `error_message`, not `"in_progress"`. |
| Status | Not run |

---

## 4. Job Redelivery — Idempotency (outbound half)

### TC-01-INT-4.1 — Redelivering the same background job does not call the provider twice

| Field | Value |
|---|---|
| Description | The inbound key stops a duplicate POST; this is the outbound half — a redelivered job for a generation already finished must not re-spend at the provider or write a second document. |
| Preconditions | Generation G1 is `completed` with its document committed; the stub provider's counter is reset to 0 after that. |
| Test data | G1 id `3f8a1d02-9c47-4b6e-8e10-5d2c7a91f430`, `status = completed`; identical job dispatched again |
| Steps | 1. Run G1's job to completion and record its content.<br>2. Reset the stub's call counter to 0.<br>3. Dispatch the identical job for G1 again.<br>4. Read the stub's call count and count the documents for G1. |
| Expected result | The stub's call count is still `0` after the redelivery — the status gate refuses the claim before any provider call; exactly one document exists for G1 and its content is unchanged; `status` remains `"completed"`. |
| Status | Not run |

### TC-01-INT-4.2 — Redelivering a job for an already-failed generation does not reprocess it

| Field | Value |
|---|---|
| Description | `failed` is terminal. A redelivery that resets it would restart paid work the system already gave up on, and would flip a user's error screen back to a spinner. |
| Preconditions | Generation G1 reached `failed` via retry exhaustion; the stub provider's counter is reset to 0 afterwards. |
| Test data | G1 `status = failed`, `error_message` = the generic failure text; identical job dispatched again |
| Steps | 1. Drive G1 to `failed` by exhausting the 2-attempt budget.<br>2. Reset the stub's counter to 0.<br>3. Dispatch the identical job for G1 again.<br>4. `GET /api/v1/generations/{G1}` and read the stub's counter. |
| Expected result | The stub's call count is still `0`; `status` is still `"failed"` — not reset to `"pending"` or `"in_progress"`, not reprocessed; `error_message` is unchanged; no document is created. |
| Status | Not run |

---

## 5. Transaction Atomicity

### TC-01-INT-5.1 — The document and the completed status commit together, never one without the other

| Field | Value |
|---|---|
| Description | Two separate commits give two ways to be wrong: a document nobody can reach because the status never moved, or a `completed` status the client polls into with no content behind it. |
| Preconditions | Generation G1 is `in_progress`; the provider call has already returned content; a fault is injectable between the document insert and the status write. |
| Test data | Fault injected after the document insert and before the status write, within the same unit of work |
| Steps | 1. Run the job for G1 with the fault armed.<br>2. After the job returns, query the documents table for rows referencing G1.<br>3. `GET /api/v1/generations/{G1}` and read `status` and `content`. |
| Expected result | Either both writes are present (`status: "completed"` **and** its document row) or neither is — never one alone; specifically, no document row exists for a G1 that is not `completed`, and G1 is never `"completed"` with `content` null or its document row missing. |
| Status | Not run |

### TC-01-INT-5.2 — A commit failure after a successful provider call does not trigger a duplicate call

| Field | Value |
|---|---|
| Description | A result obtained and then lost on commit is the case where a naive retry pays the provider twice for text the system already had. Whatever the policy, it must be deliberate and it must reach a correct terminal state. |
| Preconditions | Generation G1 is `in_progress`; the provider returns `200`; the DB write raises before commit; the stub counts calls. |
| Test data | Stub `200` with the success body; commit aborted on the first pass; stub counter read after each pass |
| Steps | 1. Run the job for G1 with the commit fault armed and record the stub's call count.<br>2. Let the generation be retried (by the sweep or the retry path).<br>3. Read the stub's call count again and `GET /api/v1/generations/{G1}`. |
| Expected result | The stub is not called again to reproduce a result that was already obtained, unless the system re-attempts by explicit design — and if it does, that re-attempt is the documented behaviour, not an accident; G1 ends in a correct terminal state (`completed` with content, or `failed` with the generic message), never `in_progress`, and the provider spend for G1 is bounded and accounted for. |
| Status | Not run |

---

## 6. Deadline Budget Composition

### TC-01-INT-6.1 — The bounded retry sequence fits within the job's overall deadline

| Field | Value |
|---|---|
| Description | If the sum of per-call timeouts and backoffs can exceed the job deadline, the deadline fires mid-retry and cancels the sequence at an arbitrary point — the retry policy then only ever half-runs. |
| Preconditions | Generation G1 is `pending`; the stub provider times out on every call; the job deadline is at its configured value. |
| Test data | Per-call read timeout × 2 attempts + backoff (`1.0 s` + up to `0.5 s` jitter) summed against the job deadline |
| Steps | 1. Compute per-call-timeout × 2 + maximum backoff and compare it with the configured job deadline.<br>2. Run the job for G1 against the always-timing-out stub, timing it.<br>3. After the job returns, check for any still-running provider call. |
| Expected result | The computed worst-case sum is strictly less than the job deadline (margin, not equality); the measured run finishes inside the deadline and ends with `status: "failed"`; no provider call is still in flight after the job returns. |
| Status | Not run |

---

## 7. Failure Isolation

### TC-01-INT-7.1 — A permanently failing generation does not block other generations from completing

| Field | Value |
|---|---|
| Description | Holding a concurrency slot for the full retry budget of a job that can never succeed lets a handful of bad requests starve every good one behind them. |
| Preconditions | Two pending generations exist; the stub provider answers `400` for the first and `200` for the second. |
| Test data | G-bad: stub always `400`. G-good: stub `200` with the success body. Both dispatched within the same second |
| Steps | 1. Dispatch the jobs for G-bad and G-good at the same time.<br>2. Wait for both to reach a terminal state, timing each.<br>3. `GET /api/v1/generations/{id}` for both. |
| Expected result | G-good reaches `"completed"` with its content, and does so without waiting on G-bad's retry sequence; G-bad reaches `"failed"` on its first attempt and releases its slot immediately rather than holding it for the full budget. |
| Status | Not run |

---

## 8. Retry Timing Spread

### TC-01-INT-8.1 — Concurrent retries after a shared transient outage do not all retry at the same instant

| Field | Value |
|---|---|
| Description | A shared provider blip fails every in-flight generation at once. With a fixed backoff they all retry on the same instant, re-creating the burst that caused the outage against an already-struggling paid API. |
| Preconditions | 20 pending generations are dispatched together; the stub provider returns `503` to all of them at the same moment, then `200`, and timestamps every call. |
| Test data | 20 generations; backoff `1.0 s` base plus uniform jitter in `[0, 0.5 s]`; stub timestamps at millisecond resolution |
| Steps | 1. Dispatch all 20 jobs together.<br>2. Let the stub fail all 20 first calls at the same instant.<br>3. Record the timestamp of each generation's second call.<br>4. Compute the spread and the count of identical timestamps. |
| Expected result | The 20 retry timestamps are spread across a window of roughly the jitter range (about 500 ms), not clustered on one instant; no more than a couple share the same millisecond; the earliest retry is at least the `1.0 s` base after its failure. |
| Status | Not run |
