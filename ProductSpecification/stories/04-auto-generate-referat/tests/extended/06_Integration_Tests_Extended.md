# Auto-generate: реферат — Integration Tests (Extended)

> These are additional edge case tests. Implement after core tests pass.

Boundary under test: the worker/queue re-delivery path, the stale-generation sweep
(`RequeueStaleGenerations`), and the GigaChat stub's failure surface.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.referat@textery.test` / `Qa!Referat2026` |
| Generation R1 | id `3d7a41f6-8c02-4e19-b5aa-71f0c2d94e83`, `document_type=реферат`, topic `Влияние цифровизации на образование` |
| Completed content | `Реферат о цифровизации образования.` |
| Terminal failure state | `status: "failed"`, `error_message: "Не удалось сгенерировать документ. Попробуйте позже."` |
| Client read | `GET /api/v1/generations/{generation_id}` |

---

## 1. Re-delivery

### TC-04-INT-EXT-1.1 — A redelivered job does not generate twice

| Field | Value |
|---|---|
| Description | Story 1 established the compare-and-swap guard on status transitions. This asserts it still holds for a реферат, where the only difference is which template built the prompt. |
| Preconditions | Account A signed in; generation R1 already `completed` with the content above; the provider stub's call counter reset to zero after that completion. |
| Test data | Generation R1's id, re-enqueued once |
| Steps | 1. Re-enqueue generation R1's id so a worker picks the same job again.<br>2. Wait for the worker to finish handling it.<br>3. Read the provider stub's call count.<br>4. `GET /api/v1/generations/{R1}`. |
| Expected result | The stub recorded zero calls after the reset; the `GET` answers `200 OK` with `status: "completed"` and `content: "Реферат о цифровизации образования."` unchanged — the row is not rewritten and never re-enters `in_progress`. |
| Status | Not run |

### TC-04-INT-EXT-1.2 — A generation abandoned mid-flight is swept to failed

| Field | Value |
|---|---|
| Description | `BackgroundTasks` is not durable across a process restart, so a реферат left `in_progress` by a crashed worker would sit there forever without the sweep. |
| Preconditions | Account A signed in; generation R1 written directly to storage as `in_progress` with an `updated_at` older than the staleness window. |
| Test data | Generation R1 stamped `in_progress` at `now − 2 × staleness window`; the sweep invoked with `older_than = now − staleness window` |
| Steps | 1. Seed generation R1 as stale `in_progress`.<br>2. Run `RequeueStaleGenerations.execute(older_than)`.<br>3. Let the re-triggered dispatch run to its end with the provider stub failing.<br>4. `GET /api/v1/generations/{R1}`. |
| Expected result | The sweep claims the row exactly once (a second replica racing it loses the compare-and-swap and logs, not errors); after the re-triggered dispatch exhausts the attempt budget the `GET` answers `200 OK` with `status: "failed"` and `error_message: "Не удалось сгенерировать документ. Попробуйте позже."` — the row does not stay `in_progress`. |
| Status | Not run |
| Note | The sweep itself resets a stale row to `pending` and hands it back for re-execution; `failed` is the state reached by the re-execution, not written by the sweep. If the deployment expects the sweep to terminate a row directly, record which of the two behaviours is contracted before running this case. |

---

## 2. Extended Failure Surface

### TC-04-INT-EXT-2.1 — A provider rate-limit response is distinguishable from other failures

| Field | Value |
|---|---|
| Description | A rate limit is an operational signal, not a bug in the request; collapsing it into the same record as a malformed body hides a quota problem from whoever is on call. |
| Preconditions | Account A signed in; the GigaChat stub answers `429 Too Many Requests` to every completion request; server logs captured. |
| Test data | Generation R1; stub status `429`; attempt budget `MAX_PROVIDER_ATTEMPTS = 2` |
| Steps | 1. Let the worker dispatch generation R1.<br>2. Read the captured server log records.<br>3. `GET /api/v1/generations/{R1}`. |
| Expected result | The server-side records name the rate-limit category (`429` / rate limit), distinguishably from the timeout and malformed-body categories; the client's `GET` answers `200 OK` with a bare `status: "failed"` and `error_message: "Не удалось сгенерировать документ. Попробуйте позже."` — no upstream status code, quota figure or category name reaches the client. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `its job is delivered again` | Same job re-enqueued / redelivered to a worker |
| `the staleness window` | Story 1's reconciliation threshold for pending / in-progress rows |
| `the recorded failure category` | Server-side category field, not the client-facing `status` |
