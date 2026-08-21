# Мои проекты — Load Tests

Targets the project's declared **Throughput** profile (`ProductSpecification/ExpectedLoad.md`):
capacity per second under concurrent users, not per-request latency percentiles and not
full-table volume scale. This story adds the product's first typing-frequency endpoint —
a debounced search running `ILIKE` over document content — so the scenarios assert
sustained rate and the bounds that keep one expensive query from holding capacity.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Seeded accounts | 200 accounts `qa.load001@textery.test` … `qa.load200@textery.test`, each owning ~50 documents and ~20 generations |
| Target rate / window | 200 req/s sustained over 60 s |
| Error-rate ceiling | < 0.1 % non-2xx (429 shedding counted per the case that expects it) |
| Statement deadline | 3 s, applied per transaction with `SET LOCAL` |
| Search concurrency cap | 1 in-flight searching request per account; refusal `429` `{"error_code":"SEARCH_BUSY"}` with `Retry-After` |
| Search-slot TTL | 10 s |
| Endpoint under load | `GET /api/v1/projects?page=…&limit=20&sort=…&q=…` with a per-account Bearer token |
| Measured signals | throughput counter, non-2xx share, connection-pool checked-out gauge, per-request duration |

---

## 1. Feed Request Rate

### TC-12-LOAD-1.1 — The projects feed sustains its request rate under concurrent users

| Field | Value |
|---|---|
| Description | Catches a regression that makes the merge query cost grow per request — an in-Python merge, a per-row preview read, a lost `LIMIT` pushdown, or a per-item query behind the union. All of them show up here as rate collapse, not as a wrong answer. |
| Preconditions | The 200 seeded accounts exist with their realistic document/generation mix; the backend runs at its configured replica count; the pool is at its baseline checkout level. |
| Test data | 200 req/s sustained for 60 s; `limit=20`, `sort=created_desc`, no `q`; each virtual user pages only its own feed. |
| Steps | 1. Ramp to 200 req/s of `GET /api/v1/projects?page={1..5}&limit=20` across the 200 accounts.<br>2. Hold the rate for 60 s.<br>3. Sample the throughput counter and the non-2xx share over the window.<br>4. Spot-check 100 responses against the issuing account. |
| Expected result | Measured throughput ≥ 200 req/s for the whole 60 s window with no dip below it; non-2xx share < 0.1 %; every spot-checked response contains only `(kind,id)` pairs owned by the account whose token issued it. |
| Status | Not run |

---

## 2. Search Under Concurrency

### TC-12-LOAD-2.1 — Concurrent searches do not degrade the unsearched feed's rate

| Field | Value |
|---|---|
| Description | Catches the scenario the story names as its scaling risk — unindexed scans over maximum-size content holding pooled connections until unrelated requests queue behind them; correct at one request per second and collapsing at typing rate. |
| Preconditions | 50 of the seeded accounts hold documents at the maximum stored content size; the remaining 150 hold the standard mix. |
| Test data | 200 req/s total for 60 s; 25 % of virtual users searching at debounced-input rate (~1 search per 300 ms of typing), 75 % paging without `q`; statement deadline 3 s. |
| Steps | 1. Start the mixed load and hold it for 60 s.<br>2. Measure the throughput of the unsearched (`q`-less) requests separately.<br>3. Measure the non-2xx share and the maximum request duration. |
| Expected result | The unsearched feed sustains ≥ 200 req/s for the window; non-2xx share < 0.1 %; every request terminates within the 3 s statement deadline with a status (`200` or `503 QUERY_TIMEOUT`) — none is left unanswered past the deadline. |
| Status | Not run |

### TC-12-LOAD-2.2 — Excess concurrent searches are shed rather than queued

| Field | Value |
|---|---|
| Description | Catches a cap implemented per-process — which bounds nothing across replicas — and a cap that queues instead of shedding, turning a burst into pool exhaustion. |
| Preconditions | Seeded accounts as above; the per-account cap of 1 in-flight search is in force and stored in the database. |
| Test data | 60 s window; each searching account issues 4 concurrent searches at a time (3 above its allowance); pool ceiling as configured in `infra/.env`. |
| Steps | 1. Run the over-subscribed search load for 60 s.<br>2. Count `429` responses and their `error_code`.<br>3. Sample the connection-pool checked-out gauge throughout.<br>4. Measure the duration of the accepted searches. |
| Expected result | Excess searches answer `429` with `{"error_code":"SEARCH_BUSY"}` and a `Retry-After` header (≤ 10 s) rather than waiting; pool utilisation stays below its configured ceiling for the whole window and never saturates; every accepted search completes within the 3 s deadline. |
| Status | Not run |

### TC-12-LOAD-2.3 — Abandoned searches do not accumulate

| Field | Value |
|---|---|
| Description | Catches the leak the story names explicitly — discarding a response client-side does not cancel the server's scan, so a user typing twelve characters holds twelve scans and twelve connections. |
| Preconditions | Pool checked-out gauge recorded at baseline before the run. |
| Test data | 2 000 searches issued and the client socket closed ~200 ms into each; measured over 60 s; recovery window = one 3 s deadline. |
| Steps | 1. Record the baseline checked-out gauge.<br>2. Issue and abandon the 2 000 searches.<br>3. Wait one deadline window (3 s) after the last abandon.<br>4. Re-read the gauge and query `pg_stat_activity`. |
| Expected result | The checked-out-connection gauge returns to its baseline value within 3 s of the last abandon; `pg_stat_activity` shows no query from an abandoned search still executing. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the configured throughput baseline` | The load suite's standard concurrency and seeded accounts (`ExpectedLoad.md`) |
| `the target rate` / `the measurement window` | The suite's configured sustained rate and window (200 req/s over 60 s) |
| `sustains the target rate over the window` | Throughput counter over the run, asserted against the annotated rate |
| `the error rate ceiling` | The suite's configured non-2xx share (< 0.1%) |
| `refused as too many requests` | 429 `SEARCH_BUSY` |
| `the statement deadline` | 3 s, `SET LOCAL` per request |
| `the pool's checked-out connections` | Connection-pool gauge sampled before and after the run |
| `abandoned before they answer` | Client disconnects before the response |
