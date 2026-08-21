<!-- COPIED FILE. Source of truth: ProductSpecification/stories/05-manual-mode/tests/extended/04_Infrastructure_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Manual input mode (non-AI document creation) — Infrastructure Tests (Extended)

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the owner) | `qa.manual@textery.test` / `Qa!Manual2026` |
| Document A1 | id `3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3`, `content` `<p>Первый абзац.</p>`, `version` `2` |
| Save request | `PUT /api/v1/documents/{document_id}` `{"content": "<p>Абзац</p>", "version": <current>}` |
| Connection count | `SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();` |
| Fault injection | A transient Postgres error raised at the adapter boundary for each save |

## 1. Resource Cleanup

### TC-05-INFRA-EXT-1.1 — Repeated failed saves do not leak database connections

| Field | Value |
|---|---|
| Description | An error path that returns before releasing its connection leaks one per failure. The service keeps working until the pool is exhausted, then fails every request at once with no new trigger to point at. |
| Preconditions | Backend and Postgres up and idle; document A1 exists; the connection-pool ceiling is read from `infra/.env`. |
| Test data | 100 sequential `PUT /api/v1/documents/{A1}` requests, each made to fail with a transient database error; baseline connection count taken before the run; settle period 30 s after the last failure |
| Steps | 1. Record the baseline connection count with `SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();`.<br>2. Issue the 100 failing save requests in sequence.<br>3. Wait 30 s for connections to settle.<br>4. Re-run the connection count query.<br>5. Issue one normal save with the fault injection removed. |
| Expected result | All 100 requests answer `500` with `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}` and none hangs; the step-4 count equals the step-1 baseline (no monotonic growth across the run) and stays well under the pool ceiling; step 5 answers `200 OK`, proving the pool is still usable. |
| Status | Not run |
