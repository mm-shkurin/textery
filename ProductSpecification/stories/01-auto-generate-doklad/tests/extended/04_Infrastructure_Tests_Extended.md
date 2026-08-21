> These are additional edge case tests. Implement after core tests pass.

# Auto-generate: доклад — Infrastructure Tests (Extended)

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.doklad@textery.test` / `Qa!Doklad2026` |
| Valid create body | `{"document_type": "доклад", "topic": "Влияние искусственного интеллекта на образование", "volume_pages": 5}` |
| Error body shape | `{"error_code": "<CODE>", "message": "<text>"}` |
| Staleness window | `GENERATION_STALE_AFTER_MINUTES`, default `10` |
| Queue | in-process `BackgroundTasks` today; its backing store once `arq`/Redis lands (`known-debt.md` #13) |

## 1. Redis Unavailability

### TC-01-INFRA-1.1 — Generation submission fails cleanly when the job queue is unreachable

| Field | Value |
|---|---|
| Description | If the row commits and the enqueue then fails silently, the caller is told `201` and the generation waits for a job that was never created — visible to the user only as a spinner that never ends. |
| Preconditions | Backend running; account A signed in; the job queue's backing store made unreachable (port blocked). |
| Test data | Valid create body; queue store refusing every connection; `GENERATION_STALE_AFTER_MINUTES = 10` |
| Steps | 1. Block the queue's backing store.<br>2. `POST /api/v1/generations` with the valid body.<br>3. Read the status and body of the response.<br>4. `GET /api/v1/generations` and note any row created.<br>5. Restore the store, wait past the staleness window, and let the sweep run. |
| Expected result | Step 3 answers `500` with exactly `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}` — never a `201` for a generation with no job; the failure detail is in the server log, not the body; and any row that did commit is picked up by the sweep in step 5 rather than being left permanently `pending` with no job. |
| Status | Not run |

## 2. Worker Restart

### TC-01-INFRA-2.1 — In-flight generations are picked up again after a worker restart

| Field | Value |
|---|---|
| Description | `BackgroundTasks` dies with its process. Without an age-based recovery, every restart during a deploy silently abandons every generation running at that moment. |
| Preconditions | Generation G1 is `in_progress` with its job actively running; the stub GigaChat server is available and returns `200`. |
| Test data | G1 id `3f8a1d02-9c47-4b6e-8e10-5d2c7a91f430`; backend restarted mid-processing; G1 then aged past the 10-minute window |
| Steps | 1. Start G1's job and confirm `status: "in_progress"`.<br>2. Restart the backend instance while the job is running.<br>3. Confirm no job is running for G1 after the restart.<br>4. Age G1 past the staleness window and let the periodic sweep run.<br>5. Poll `GET /api/v1/generations/{G1}`. |
| Expected result | After the restart G1 is momentarily `in_progress` with no job behind it; the sweep then reclaims it and drives it to a terminal state — `completed` with content, or `failed` with `Не удалось сгенерировать документ. Попробуйте позже.`; it is never left silently abandoned in `in_progress`, and no duplicate document is produced. |
| Status | Not run |
