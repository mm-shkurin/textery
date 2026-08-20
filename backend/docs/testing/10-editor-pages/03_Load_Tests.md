<!-- COPIED FILE. Source of truth: ProductSpecification/stories/10-editor-pages/tests/03_Load_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Editor pages — Load Tests

Profile: **Throughput** (`ProductSpecification/ExpectedLoad.md`) — the binding constraint is
request rate, not per-user data volume. Pagination itself is measured in the browser and
costs the server nothing, so the only surface this story puts under rate pressure is
**export**, which each document now makes strictly more expensive: full geometry, headers,
footers and page numbering on every render, synchronously, holding a request thread.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Load accounts | 50 seeded accounts `qa.load001@textery.test` … `qa.load050@textery.test`, password `Qa!Load2026` |
| Document pool | 200 caller-owned documents of ~8 000 characters, 4 pages at the default preset |
| Configured pool | the same 200 documents saved with settings `S1` |
| Settings `S1` | A5, landscape, margins 35/15/25/40 mm, 11 pt, line height 1.15, header `Кафедра ИВТ`, footer `Текстери`, `show_page_numbers` true |
| Target sustained rate | the project's configured baseline rate for `GET /export` (record the configured value before the run; the runs below use **10 req/s**) |
| Measurement window | 60 s at rate, after a 30 s ramp |
| Error-rate ceiling | < 1 % of responses non-`2xx` over the window |
| Render deadline | the configured per-render wall-clock timeout (story 17), **30 s** |
| Render-concurrency bound | story 17's configured concurrent-render limit / worker pool size, **4** |
| Tool | the project's load runner against the prod-copy environment |

---

## 1. Export Under Rate

### TC-10-LOAD-1.1 — Export sustains its rate with page settings applied

| Field | Value |
|---|---|
| Description | Applying geometry, headers, footers and numbering on every render adds per-request cost; the regression this catches is that cost pushing the instance below the rate it absorbed before this story. |
| Preconditions | Prod-copy running one backend instance; the configured pool of 200 documents carries settings `S1`; no other load on the host. |
| Test data | 10 export req/s sustained over a 60 s window after a 30 s ramp; mix `format=pdf` 70 % / `format=docx` 30 %; error ceiling < 1 %; render deadline 30 s |
| Steps | 1. Ramp export requests against the configured pool to 10 req/s over 30 s.<br>2. Hold 10 req/s for 60 s, recording every response status and duration.<br>3. Compute the achieved rate, the non-`2xx` share and the maximum single-request duration. |
| Expected result | Achieved rate ≥ 10 req/s across the full 60 s window (no sag in any 10 s bucket); non-`2xx` responses < 1 % of the total; the maximum single-request duration is below the 30 s render deadline and no response is a deadline-abort `500`. |
| Status | Not run |

### TC-10-LOAD-1.2 — Concurrent renders stay bounded under sustained export load

| Field | Value |
|---|---|
| Description | Catches both a regression of story 17's concurrency bound and a resource leak on the new geometry/header path — including its failure branch, which this story adds. |
| Preconditions | Prod-copy running one backend instance; in-flight-render gauge and process RSS are sampled once a second; a baseline sample is taken before the load starts. |
| Test data | Arrival rate 25 export req/s (deliberately above what 4 concurrent renders can drain); 60 s window; concurrency bound 4; 120 s cool-down after the load stops |
| Steps | 1. Record baseline in-flight renders and process RSS.<br>2. Drive export requests at 25 req/s for 60 s against the configured pool.<br>3. Sample the in-flight-render gauge every second throughout.<br>4. Record the disposition of the excess requests (queued vs. shed).<br>5. Stop the load, wait 120 s, and re-sample in-flight renders and RSS. |
| Expected result | The in-flight-render gauge never exceeds 4 in any sample; excess requests are handled by the configured policy — queued and served, or shed with a single consistent status — and none is dropped without a response; after the cool-down the gauge reads 0 and RSS is within 10 % of the baseline recorded in step 1. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the configured throughput baseline` | The project's declared sustained-rate baseline from `ExpectedLoad.md` |
| `the render deadline` | The existing per-render wall-clock timeout (story 17 config) |
| `the configured bound` | Story 17's concurrent-render limit / worker pool size |
| `render resources` | In-flight render count and process memory, sampled before and after |
