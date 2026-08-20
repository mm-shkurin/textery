# Мои проекты — Integration Tests

The feed itself calls nothing external. «Повторить» does. Covers the three seams this story
adds outside its own request handler: «Повторить» → background job queue → worker (the
outbound half of the idempotency guarantee asserted inbound in `01_API_Tests.md` section 8),
the retry path running beside the existing stale-generation sweep, which writes the same
rows continuously, and the retry reaching the model provider itself. Those overlaps are the
integration risk this story introduces, so they are tested here, not left to the two
components' own suites.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.projects@textery.test` / `Qa!Projects2026` |
| Source generation S | id `c72e5a90-3b14-4d6f-9e88-01af4c2d7b65`, `status=failed`, `document_type=реферат`, `topic=Влияние климата на урожай`, `volume_pages=10` |
| Second source S2 | id `1f6c3b85-92d0-47ae-b4c1-08e5d7a26f39`, `status=failed`, `topic=История книгопечатания` |
| Queue | arq generation queue; one job per generation, keyed by the generation id |
| Provider | the model provider behind generation (story 1), driven through the existing Fake with a call counter |
| Stale sweep | `RequeueStaleGenerations`, `GENERATION_STALE_AFTER_MINUTES=10` |
| Retry ceiling | 5 per source generation, else `429` `{"error_code":"RETRY_LIMIT_REACHED"}` |
| Error body shape | `{"error_code": "<CODE>", "message": "<generic text>"}`; `correlation_id` added on 5xx only |

---

## 1. Retry → Job Queue

### TC-12-INT-1.1 — An accepted retry enqueues exactly one job for the new generation

| Field | Value |
|---|---|
| Description | The job must name the row that is actually going to run; enqueuing the source id would re-run the failed generation and overwrite its record. |
| Preconditions | Account A owns source S; the queue is empty. |
| Test data | Source `c72e5a90-…`; `Idempotency-Key: k-int11`. |
| Steps | 1. `POST /api/v1/generations/c72e5a90-…/retry` with account A's token and that key.<br>2. Read the queue's contents. |
| Expected result | `201 Created` with a new generation id `N`; exactly one job is on the generation queue; its payload names `N`, not `c72e5a90-3b14-4d6f-9e88-01af4c2d7b65`. |
| Status | Not run |

### TC-12-INT-1.2 — A replayed retry key enqueues no second job

| Field | Value |
|---|---|
| Description | Inbound idempotency that still enqueues a second job buys the generation twice at the provider — the row is deduplicated and the money is not. |
| Preconditions | A retry with `k-int12` was already accepted against source S and created generation `N`. |
| Test data | `Idempotency-Key: k-int12`, replayed against the same source. |
| Steps | 1. Re-send `POST /api/v1/generations/c72e5a90-…/retry` with `k-int12`.<br>2. Count the jobs on the queue for generation `N`. |
| Expected result | `200 OK` describing generation `N`; the job count for `N` is still exactly 1; no new job was published. |
| Status | Not run |

### TC-12-INT-1.3 — A retry whose enqueue fails leaves no generation the worker will never pick up

| Field | Value |
|---|---|
| Description | A committed `pending` row with no job behind it shows in the feed as running forever, and is not retryable while it sits there. |
| Preconditions | Account A owns source S; the queue client is made to raise on enqueue. |
| Test data | `Idempotency-Key: k-int13`; queue unavailable. |
| Steps | 1. `POST /api/v1/generations/c72e5a90-…/retry` with that key.<br>2. Query `generations` for rows created by that key.<br>3. `GET /api/v1/projects?limit=100`. |
| Expected result | The response is a `5xx` in the `{error_code, message, correlation_id}` envelope; no `generations` row exists for `k-int13`; the feed shows no new non-terminal generation for that source. |
| Status | Not run |

### TC-12-INT-1.4 — A retry that stored its generation but lost the response is not enqueued twice

| Field | Value |
|---|---|
| Description | The safe client resend must be safe at the queue too, or every dropped response costs one extra provider call. |
| Preconditions | A retry with `k-int14` committed generation `N` and published its job; the response never reached the client. |
| Test data | `Idempotency-Key: k-int14`. |
| Steps | 1. Re-send the identical retry with `k-int14`.<br>2. Count the jobs for generation `N`. |
| Expected result | `200 OK` describing generation `N`; the job count for `N` is exactly 1; no second generation row exists. |
| Status | Not run |

### TC-12-INT-1.5 — The enqueued job carries the source's stored parameters, not client input

| Field | Value |
|---|---|
| Description | Parameters are copied server-side from the row precisely so the browser cannot choose what the worker runs; a job built from the request would reopen the mass-assignment hole the endpoint was designed to close. |
| Preconditions | Account A owns source S with `document_type=реферат`, `topic=Влияние климата на урожай`, `volume_pages=10`. |
| Test data | `Idempotency-Key: k-int15`; request body `{"topic":"Другая тема","volume_pages":99,"document_type":"эссе"}`. |
| Steps | 1. `POST /api/v1/generations/c72e5a90-…/retry` with that key and that body.<br>2. Read the enqueued job's payload. |
| Expected result | `201 Created`; the job payload carries `document_type=реферат`, `topic=Влияние климата на урожай`, `volume_pages=10`; none of `Другая тема`, `99` or `эссе` appears in the job or in the stored row. |
| Status | Not run |

---

### TC-12-INT-1.6 — A retry whose commit fails leaves no job behind

| Field | Value |
|---|---|
| Description | The mirror of 1.3: a published job whose generation was rolled back sends the worker after a row that does not exist, which is a crash loop on the queue. |
| Preconditions | Account A owns source S; the retry's transaction is made to fail after the point where the job would be enqueued. |
| Test data | `Idempotency-Key: k-int16`; fault injected at commit. |
| Steps | 1. `POST /api/v1/generations/c72e5a90-…/retry` with that key.<br>2. Inspect the queue.<br>3. Let the worker drain for 30 s and read its log. |
| Expected result | The response is a `5xx` in the sanctioned envelope; no job exists on the queue for that generation; the worker logs no "generation not found" and never picks up a non-existent id. |
| Status | Not run |

### TC-12-INT-1.7 — An enqueue that times out resolves to a defined outcome

| Field | Value |
|---|---|
| Description | A blocking enqueue with no timeout hangs the HTTP request until the gateway kills it, and the client never learns whether it paid. |
| Preconditions | Account A owns source S; the queue blocks past the configured enqueue timeout. |
| Test data | `Idempotency-Key: k-int17`; finite enqueue timeout; the same key replayed afterwards once the queue recovers. |
| Steps | 1. `POST /api/v1/generations/c72e5a90-…/retry` with `k-int17` against the blocked queue; measure the elapsed time.<br>2. Restore the queue and replay the identical request with `k-int17`.<br>3. Count jobs for that source's retry. |
| Expected result | Step 1 returns within the request budget (well under the gateway read timeout) with a stated failure from the `{error_code, message, correlation_id}` envelope — not a hang and not a bare internal error; after step 2, exactly one job exists for that retry. |
| Status | Not run |

### TC-12-INT-1.8 — A generation whose enqueue was lost is still picked up

| Field | Value |
|---|---|
| Description | A committed generation with a lost job is invisible work; recovery must deliver the job once — twice would bill the provider twice. |
| Preconditions | Account A's retry committed generation `N` in `pending`, but its job was never published. |
| Test data | Generation `N`; recovery = outbox drain or the stale sweep. |
| Steps | 1. Run recovery.<br>2. Count the jobs delivered for `N`.<br>3. Let the worker run and read `N`'s final status. |
| Expected result | Exactly one job is delivered for `N` (not zero, not two); `N` reaches a terminal status (`completed` or `failed`) and stops being reported as running in the feed. |
| Status | Not run |

---

## 2. Retry ↔ Stale-Generation Sweep

### TC-12-INT-2.1 — The sweep does not requeue a generation the user has already retried

| Field | Value |
|---|---|
| Description | The sweep and the retry are two paths to the same rerun; both firing on one source runs the work twice and bills it twice. |
| Preconditions | Account A retried source S, producing generation `N` in `pending`; S remains `failed`. |
| Test data | Source `c72e5a90-…`; sweep tick with `GENERATION_STALE_AFTER_MINUTES=10`. |
| Steps | 1. Run one `RequeueStaleGenerations` tick.<br>2. Read S's status and the queue. |
| Expected result | S is still `failed` and was not requeued — no job names `c72e5a90-…`; only generation `N` is on the queue and processed. |
| Status | Not run |

### TC-12-INT-2.2 — A row the sweep is currently requeueing cannot be retried by the user

| Field | Value |
|---|---|
| Description | The `recovering` label and the `409` are the same rule seen from the read and the write side; letting the user in here duplicates work that is still running. |
| Preconditions | Account A owns generation `9b3f0d54-1e87-4a2c-8d65-73c1f9e0a4b2`, `status=in_progress`, `updated_at` 30 minutes ago; the sweep is requeueing it. |
| Test data | `Idempotency-Key: k-int22`. |
| Steps | 1. `POST /api/v1/generations/9b3f0d54-…/retry` with that key.<br>2. Let the sweep tick and inspect the queue. |
| Expected result | The retry answers `409 Conflict` with `{"error_code":"GENERATION_NOT_FAILED", …}`; no generation is created; the sweep's requeue is the only job published for that row. |
| Status | Not run |

### TC-12-INT-2.3 — A retry and a sweep requeue racing on one source produce one running generation

| Field | Value |
|---|---|
| Description | The two paths can interleave in the window where the source is still `failed` but the sweep has already selected it; the race must resolve to one run, not two documents. |
| Preconditions | Account A owns source S; a sweep tick and a user retry are released against it at the same instant. |
| Test data | `Idempotency-Key: k-int23`; sweep tick released simultaneously. |
| Steps | 1. Release both operations at once.<br>2. Drain the queue and let the worker finish.<br>3. Count the non-terminal/new runs for S and the documents produced. |
| Expected result | Exactly one new run exists for source S (the other path is refused or is a no-op); exactly one document is produced; the provider Fake records one call. |
| Status | Not run |

---

### TC-12-INT-2.4 — A generation whose document was written but never marked terminal is not run again

| Field | Value |
|---|---|
| Description | A crash between "document written" and "status = completed" leaves a row the sweep will re-run; without an idempotent worker the user gets two cards for one piece of work. |
| Preconditions | Retried generation `N` has a document written but its terminal-status write did not land; `N` is still non-terminal and past the stale threshold. |
| Test data | Generation `N`; one sweep tick; the worker runs it again. |
| Steps | 1. Run the sweep tick so `N` is requeued.<br>2. Let the worker process it.<br>3. Count documents for `N` and read the feed. |
| Expected result | Exactly one document exists for `N`; `GET /api/v1/projects?limit=100` shows one card for that work, not two; `N` ends in a terminal status. |
| Status | Not run |

### TC-12-INT-2.5 — One row failing mid-sweep neither rolls back nor blocks the rest

| Field | Value |
|---|---|
| Description | A batch that rolls back on one bad row re-attempts everything next tick; one that stops on it strands every later row, and a count-only outcome tells the operator nothing about which row is poisoned. |
| Preconditions | A sweep batch of 5 stale generations in which the 3rd row's requeue is made to fail. |
| Test data | Rows `g1`…`g5`; failure injected on `g3`; two consecutive ticks. |
| Steps | 1. Run the sweep tick.<br>2. Read the statuses of `g1`…`g5` and the run's outcome record.<br>3. Run the next tick and check whether `g1`/`g2` are re-attempted. |
| Expected result | `g1` and `g2` stay requeued and are not re-attempted on the next tick; `g4` and `g5` are requeued in the same run; the run's outcome names `g3` by id, not only a failure count. |
| Status | Not run |

### TC-12-INT-2.6 — Two sweep activations do disjoint work

| Field | Value |
|---|---|
| Description | The sweep runs from every replica's lifespan, so overlapping activations are the normal case; without a lease each stale row is requeued once per replica. |
| Preconditions | One sweep activation is still running when the next starts; a lease with expiry guards the batch. |
| Test data | 20 stale rows; two overlapping activations; a third activation started after the first holder is killed. |
| Steps | 1. Start activation 1 and, while it runs, start activation 2.<br>2. Count requeues and published jobs per row.<br>3. Kill the lease holder mid-run and start activation 3 after the lease expires. |
| Expected result | No row is requeued twice and no generation is re-triggered twice across the two activations; activation 3 proceeds once the lease expires, with no operator action. |
| Status | Not run |

### TC-12-INT-2.7 — An always-failing generation stops being requeued and does not stall the queue

| Field | Value |
|---|---|
| Description | The story's named open gap: with no attempt cap the sweep requeues a permanently broken row forever, and the feed shows it running indefinitely while healthy work waits behind it. |
| Preconditions | Account A owns generation `X` whose worker raises on every attempt, and a valid generation `Y` queued behind it. |
| Test data | `X` fails on every attempt; `Y` is a normal generation; drain the queue over several sweep ticks. |
| Steps | 1. Enqueue `X`, then `Y`.<br>2. Drain the queue across several sweep ticks.<br>3. Read `Y`'s status and `X`'s handling. |
| Expected result | `Y` reaches `completed` and produces its document — it is never blocked behind `X`; `X` stops being requeued after its bounded attempt count and is either dead-lettered or driven to terminal `failed`, rather than requeued without end. |
| Status | Not run |

---

## 3. Worker Outcome Reaching the Feed

### TC-12-INT-3.1 — A retried generation that completes replaces its card with a document

| Field | Value |
|---|---|
| Description | The end-to-end payoff of the retry: the new work must appear as a document (so it is openable) while the failed source stays put (so nothing vanished). |
| Preconditions | Account A retried source S producing generation `N`; the worker processes `N` successfully and its document is created. |
| Test data | Source `c72e5a90-…`; generation `N`; resulting document `D`. |
| Steps | 1. Let the worker complete `N`.<br>2. `GET /api/v1/projects?limit=100` with account A's token. |
| Expected result | `200 OK`; an item `{"kind":"document","id":"<D>"}` is present; no `kind:"generation"` item with id `N` is present; `{"kind":"generation","id":"c72e5a90-…","status":"failed"}` is still listed beside it. |
| Status | Not run |

### TC-12-INT-3.2 — A retried generation that fails again is retryable once more within the cap

| Field | Value |
|---|---|
| Description | A second failure must not dead-end the user, and each attempt must draw from the source's budget rather than resetting it. |
| Preconditions | Account A retried source S once (budget consumed: 1 of 5); the worker fails generation `N`. |
| Test data | `N`, now `status=failed`; a fresh `Idempotency-Key: k-int32`. |
| Steps | 1. `GET /api/v1/projects?limit=100` and read `N`'s item.<br>2. Retry with `k-int32` and read the source's recorded retry count. |
| Expected result | `N` is listed as `{"status":"failed","retryable":true}`; the retry answers `201 Created`; the source's recorded retry count becomes `2` of the ceiling of 5, not `1`. |
| Status | Not run |

### TC-12-INT-3.3 — A worker outcome written while the caller is paging does not corrupt the page

| Field | Value |
|---|---|
| Description | A completion mid-read changes which arm of the union a row belongs to; if the page is not read in one snapshot, an item can come back with a `kind` that contradicts its id. |
| Preconditions | Account A owns 40 projects; the worker completes a generation while the second page is being read. |
| Test data | `page=2&limit=20`; a completion landing inside the request. |
| Steps | 1. Start `GET /api/v1/projects?page=2&limit=20`.<br>2. Let the worker write its completion and document during the request.<br>3. Read the returned page. |
| Expected result | `200 OK` with no error; every item's `kind` matches the table its id actually belongs to; no item carries `kind:"generation"` with a document id or vice versa. |
| Status | Not run |

### TC-12-INT-3.4 — A job delivered twice for one generation produces one document

| Field | Value |
|---|---|
| Description | At-least-once delivery is the queue's contract; without an idempotent worker every redelivery is a second document and a second provider bill. |
| Preconditions | Account A's generation `N` is `pending`; the same job is delivered twice. |
| Test data | Generation `N`; provider Fake call counter reset before the run. |
| Steps | 1. Deliver the job for `N`.<br>2. Deliver the identical job again after the first is processed.<br>3. Count documents for `N` and read the provider Fake's call count. |
| Expected result | Exactly one document exists for `N`; the provider Fake records exactly 1 call; the second delivery is a no-op that raises nothing and leaves `N`'s status and document unchanged. |
| Status | Not run |

---

## 4. Retry Reaching the Model Provider

### TC-12-INT-4.1 — A retry produces a real generation with the source's parameters

| Field | Value |
|---|---|
| Description | The full seam, end to end: the parameters copied from the row must be the ones that reach the provider, not defaults picked up along the way. |
| Preconditions | Account A owns source S (`реферат` / `Влияние климата на урожай` / 10 pages); the provider Fake answers successfully. |
| Test data | `Idempotency-Key: k-int41`; provider Fake configured to succeed. |
| Steps | 1. `POST /api/v1/generations/c72e5a90-…/retry` with that key.<br>2. Let the worker run.<br>3. Read the provider Fake's recorded request and the finished generation. |
| Expected result | `201 Created`; the provider was called with `document_type=реферат`, `topic=Влияние климата на урожай`, `volume_pages=10`; the new generation reaches `completed` carrying those same three values. |
| Status | Not run |

### TC-12-INT-4.2 — A retry whose provider call fails leaves a failed generation, not a lost one

| Field | Value |
|---|---|
| Description | A provider error that leaves the row non-terminal shows in the feed as work still running, and the retry button stays hidden behind `retryable:false`. |
| Preconditions | Account A owns source S; the provider Fake returns an error. |
| Test data | `Idempotency-Key: k-int42`; provider Fake configured to error. |
| Steps | 1. Retry source S with that key.<br>2. Let the worker run to completion.<br>3. `GET /api/v1/projects?limit=100`. |
| Expected result | The new generation `N` is recorded with `status=failed` (terminal, not `pending`/`in_progress`); the feed lists it as `{"status":"failed","retryable":true}`. |
| Status | Not run |

### TC-12-INT-4.3 — A retry whose provider call times out does not hang the request

| Field | Value |
|---|---|
| Description | The HTTP retry only enqueues; if it waits on the provider, one slow model call blocks a request thread and the user's click appears to do nothing. |
| Preconditions | Account A owns source S; the provider Fake never answers. |
| Test data | `Idempotency-Key: k-int43`; provider Fake hangs past its timeout. |
| Steps | 1. `POST /api/v1/generations/c72e5a90-…/retry` with that key and measure the elapsed time.<br>2. Let the provider timeout elapse in the worker.<br>3. `GET /api/v1/projects?limit=100`. |
| Expected result | Step 1 answers `201 Created` promptly — within the normal request budget, not held for the provider timeout; once the worker's call times out, the feed reports that generation in its resolved terminal state (`failed`, `retryable:true`), not indefinitely running. |
| Status | Not run |

---

## 5. Feed Consistency With the Conversion Flow

### TC-12-INT-5.1 — A document created from a generation replaces it in the feed

| Field | Value |
|---|---|
| Description | The dedup rule seen through the endpoint that actually creates the link — the case that makes a completed generation stop being an orphan. |
| Preconditions | Account A owns completed generation `e5d90b31-7c62-44a8-b1f3-28ad6e094c17` shown in the feed as an orphan. |
| Test data | `POST /api/v1/documents/from-generation` with that generation id. |
| Steps | 1. `GET /api/v1/projects?limit=100` and confirm the generation item is present.<br>2. `POST /api/v1/documents/from-generation` for `e5d90b31-…`; record the new document id.<br>3. `GET /api/v1/projects?limit=100` again. |
| Expected result | After step 2 the feed shows the work exactly once, as `{"kind":"document","id":"<new document id>"}`; no `kind:"generation"` item with id `e5d90b31-…` remains; `total` is unchanged from step 1. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `one background job is enqueued` | One arq job on the generation queue |
| `the job queue is unavailable` | Queue client raises on enqueue |
| `refused as not-failed` | 409 `GENERATION_NOT_FAILED` |
| `the stale threshold` | `GENERATION_STALE_AFTER_MINUTES` (default 10) |
| `the stale-generation sweep` | `RequeueStaleGenerations` scheduled job |
| `the source's retry budget` | 5 retries per source generation, else 429 `RETRY_LIMIT_REACHED` |
| `the enqueue timeout` | Finite timeout on the arq enqueue call |
| `recovery` | Outbox drain or the stale-generation sweep, whichever the design adopts |
| `set aside` | Dead-lettered, or driven to terminal `failed` by a bounded attempt count (story 1 owns the cap) |
| `a holder that disappears` | Sweep lease with expiry, released without operator action |
| `the provider` | The model provider behind generation (story 1), driven through the existing Fake |
| `the provider is called once` | Call count asserted on the Fake |
| `converted into a document` | `POST /api/v1/documents/from-generation` |
