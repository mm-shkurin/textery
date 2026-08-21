<!-- COPIED FILE. Source of truth: ProductSpecification/stories/07-authorization/tests/extended/03_Load_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Authorization — Load Tests (Extended)

Targets the **Throughput** profile from `ProductSpecification/ExpectedLoad.md`, using the
same baseline as `03_Load_Tests.md`.

Shared test data and thresholds:

| Name | Value |
|---|---|
| Load tool / target | k6 (or Locust) against the prod-copy backend on the port declared in `infra/.env` |
| Throughput baseline | 200 concurrent virtual users, 100 requests/second sustained |
| Baseline window | 5 minutes |
| Error-rate ceiling | < 1% beyond the by-design rejections |
| Account under test | `qa.load.verify@textery.test`, pending, active code `042917` |

---

## TC-07-LOAD-E1 — Verify-code endpoint under concurrent load for the same account

| Field | Value |
|---|---|
| Description | Hammering one account's verify endpoint is where a non-atomic transition shows itself: either duplicate transitions, or a burst of `409`/`500` produced by the concurrency rather than by any client mistake. |
| Preconditions | `qa.load.verify@textery.test` exists, is pending, and holds active code `042917`; the backend is at rest and pool metrics are baselined. |
| Test data | `POST /api/v1/auth/verify` with `{"email": "qa.load.verify@textery.test", "code": "042917"}`, 200 VUs, 100 req/s, 5 minutes |
| Steps | 1. Run the verify traffic at 100 req/s for 5 minutes, all against the one account.<br>2. Record the distribution of response statuses.<br>3. Count recorded verification transitions for the account.<br>4. Sample the connection pool after the run. |
| Expected result | Step 3 counts exactly one transition regardless of how many requests landed; every response is `200 OK` with `{"is_verified": true}` (the idempotent re-run contract), with under 1% falling outside that — no `409`, no `500`, no error-rate spike attributable to the concurrency; the achieved rate holds at ≥ 100 req/s for the full window and `checkedout` returns to its idle baseline afterwards. |
| Status | Not run |
