<!-- COPIED FILE. Source of truth: ProductSpecification/stories/12-my-projects/tests/extended/03_Load_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Мои проекты — Load Tests (Extended)

Same throughput profile as the main file: 200 req/s sustained over a 60 s window, non-2xx
share < 0.1 %, statement deadline 3 s (`SET LOCAL`), search cap 1 in-flight per account
(`429 SEARCH_BUSY`), retry ceiling 5 per source (`429 RETRY_LIMIT_REACHED`).

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Seeded accounts | 200 accounts `qa.load001@textery.test` … `qa.load200@textery.test`, each with a per-account Bearer token |
| Target rate / window | 200 req/s sustained over 60 s |
| Error-rate ceiling | < 0.1 % non-2xx (deliberate `429` shedding counted separately where a case expects it) |
| Page bound | `page` ≤ 1000, `limit` ≤ 100 |
| Provider | the model provider Fake with a configured downstream rate limit and a call-rate counter |
| Measured signals | throughput counter, non-2xx share, connection-pool checked-out gauge, provider call rate |

---

## TC-12-LOAD-EXT-1 — Deep pages sustain the rate as well as the first page

| Field | Value |
|---|---|
| Description | Catches offset scans whose cost grows with page depth until deep pages dominate the pool — a query that is fast on page 1 and unusable on page 900. |
| Preconditions | Seeded accounts each hold enough projects to reach the page bound at `limit=100`. |
| Test data | 200 req/s for 60 s of `GET /api/v1/projects?page={950..1000}&limit=100`; baseline = the first-page run from `03_Load_Tests.md` TC-12-LOAD-1.1. |
| Steps | 1. Run the deep-page load at 200 req/s for 60 s.<br>2. Sample the throughput counter and the non-2xx share.<br>3. Compare against the recorded first-page baseline. |
| Expected result | Sustained throughput ≥ 200 req/s for the whole window, within threshold of the first-page baseline; non-2xx share < 0.1 %; no `503 QUERY_TIMEOUT` from the deep pages. |
| Status | Not run |

## TC-12-LOAD-EXT-2 — Accounts with large histories do not degrade the shared rate

| Field | Value |
|---|---|
| Description | Catches a query whose cost scales with one owner's row count and starves unrelated callers — the noisy-neighbour failure that only appears once real accounts diverge in size. |
| Preconditions | 20 of the 200 seeded accounts hold ~10 000 projects each; the remaining 180 hold the standard ~70. |
| Test data | 200 req/s for 60 s, requests distributed across all 200 accounts; rate measured across all accounts, not per account. |
| Steps | 1. Run the mixed-history load for 60 s.<br>2. Measure the aggregate throughput and the non-2xx share.<br>3. Measure the small accounts' throughput separately. |
| Expected result | Aggregate throughput ≥ 200 req/s across the window; non-2xx share < 0.1 %; the small accounts' own rate is not depressed by the large ones — their share of the throughput is proportional to their share of the requests. |
| Status | Not run |

## TC-12-LOAD-EXT-3 — Retry bursts do not displace feed reads

| Field | Value |
|---|---|
| Description | Catches retries consuming the same connection pool the reads need, so one burst of «Повторить» clicks makes the feed itself unavailable. |
| Preconditions | Each seeded account owns several failed generations under the retry ceiling of 5. |
| Test data | Feed load at 200 req/s for 60 s; a burst of `POST /api/v1/generations/{id}/retry` with distinct `Idempotency-Key`s layered on top for 20 s of that window. |
| Steps | 1. Start the feed load and hold it.<br>2. Layer the retry burst on for 20 s.<br>3. Measure the feed's throughput during and after the burst, and classify the retry responses. |
| Expected result | The feed's sustained rate stays ≥ 200 req/s throughout the burst, unchanged from the pre-burst measurement; retries past the ceiling answer `429` with `{"error_code":"RETRY_LIMIT_REACHED"}` immediately rather than queueing. |
| Status | Not run |

## TC-12-LOAD-EXT-4 — Search load does not starve the plain feed

| Field | Value |
|---|---|
| Description | Catches the expensive unindexed path monopolising the connection pool, leaving the cheap read — which most users are making — queued behind it. |
| Preconditions | Seeded accounts as above, with realistic document content. |
| Test data | Search requests (`q=климат`) and unfiltered feed requests issued together for 60 s; the unfiltered arm targeted at 200 req/s. |
| Steps | 1. Run both arms concurrently for 60 s.<br>2. Measure the unfiltered arm's throughput separately from the search arm's.<br>3. Sample the connection-pool checked-out gauge. |
| Expected result | The unfiltered feed holds ≥ 200 req/s for the whole window while search runs concurrently; its non-2xx share stays < 0.1 %; pool utilisation stays below its configured ceiling. |
| Status | Not run |

## TC-12-LOAD-EXT-5 — Retry bursts respect the provider's rate limit

| Field | Value |
|---|---|
| Description | Catches a retry path that bypasses the queueing the generation flow already applies — a burst would then be rejected wholesale by the provider, and the users' retries would silently disappear. |
| Preconditions | Each seeded account owns failed generations under the ceiling; the provider Fake enforces the configured downstream rate limit and counts calls. |
| Test data | 200 accounts each issuing one retry within a 5 s window, with distinct `Idempotency-Key`s; the provider's configured rate limit. |
| Steps | 1. Fire the simultaneous retry burst.<br>2. Measure the provider call rate over the following window.<br>3. Reconcile accepted retries (`201`) against generations that eventually reached a terminal status. |
| Expected result | The measured provider call rate never exceeds the configured downstream limit; every `201`-accepted retry eventually reaches a terminal status (`completed` or `failed`) — none is silently dropped or left non-terminal. |
| Status | Not run |

---

## DSL Technical Reference

Inherits `03_Load_Tests.md`.
