<!-- COPIED FILE. Source of truth: ProductSpecification/stories/12-my-projects/tests/extended/01_API_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Мои проекты — API Tests (Extended)

Shared test data is inherited from `01_API_Tests.md` (account A `qa.projects@textery.test`,
error body `{"error_code","message"}`, `page` 1..1000, `limit` 1..100, `q` ≤ 200 code points,
preview 200 code points, retry ceiling 5). Cases that need their own values name them below.

---

## 1. Search Edges

### TC-12-API-EXT-1.1 — A search query of exactly the length bound is accepted

| Field | Value |
|---|---|
| Description | The bound is inclusive; refusing at exactly 200 steals a legal query and is the classic off-by-one on a limit written as `>` instead of `>=`. |
| Preconditions | Account A signed in with projects. |
| Test data | `q` = the Latin letter `a` repeated exactly 200 times (200 code points). |
| Steps | 1. `GET /api/v1/projects?q=<a×200>` with account A's token. |
| Expected result | `200 OK` with an `items` array and a `total`; not `400 INVALID_QUERY`. |
| Status | Not run |

### TC-12-API-EXT-1.2 — Combining diacritics in the query match their precomposed stored form

| Field | Value |
|---|---|
| Description | macOS keyboards produce NFD, Windows produces NFC; without normalizing both sides the same visible word matches on one machine and not the other. |
| Preconditions | Account A owns a document titled `Résumé проекта` stored in NFC (`é` = U+00E9). |
| Test data | `q=Résumé` typed in NFD (`e` + U+0301, twice). |
| Steps | 1. `GET /api/v1/projects?q=<NFD spelling of Résumé>` with account A's token. |
| Expected result | `200 OK` with `"total":1`; `items[0]` is the `Résumé проекта` document. |
| Status | Not run |

### TC-12-API-EXT-1.3 — Leading and trailing whitespace in the query is trimmed before matching

| Field | Value |
|---|---|
| Description | A user pasting a term brings the surrounding spaces with it; matching them literally makes the search fail on input that looks identical on screen. |
| Preconditions | Account A owns a document titled `Отчёт по практике`. |
| Test data | `q=%20%20отчёт%20%20` (two spaces either side). |
| Steps | 1. `GET /api/v1/projects?q=%20%20отчёт%20%20` with account A's token. |
| Expected result | `200 OK` with `"total":1`; `items[0]` is `Отчёт по практике` — the same result as `q=отчёт`. |
| Status | Not run |

### TC-12-API-EXT-1.4 — A whitespace-only query is treated as no query

| Field | Value |
|---|---|
| Description | Once the query is trimmed, an all-space term must fall back to "no search" rather than becoming an empty literal that matches everything or nothing by accident. |
| Preconditions | Account A owns 6 projects. |
| Test data | `q=%20%20%20%20` (four spaces). |
| Steps | 1. `GET /api/v1/projects` and record the items and `total`.<br>2. `GET /api/v1/projects?q=%20%20%20%20`. |
| Expected result | Both answer `200 OK` with `"total":6` and the same 6 `(kind,id)` pairs; step 2 is not empty and is not `400`. |
| Status | Not run |

### TC-12-API-EXT-1.5 — A query consisting only of escaped metacharacters matches literally

| Field | Value |
|---|---|
| Description | The escape must apply to the query as a whole, not only when it is embedded in other text; a bare `%` is the shortest possible way to unwrap an unescaped pattern. |
| Preconditions | Account A owns document `Скидка 50% на подписку` and 5 documents with no percent sign. |
| Test data | `q=%25` (a single `%`). |
| Steps | 1. `GET /api/v1/projects?q=%25` with account A's token. |
| Expected result | `200 OK` with `"total":1`; only `Скидка 50% на подписку` is returned; the other 5 documents are absent. |
| Status | Not run |

### TC-12-API-EXT-1.6 — Search spans both sources in one query

| Field | Value |
|---|---|
| Description | The filter must be applied inside both arms of the union before deduplication, not to one arm and then merged. |
| Preconditions | Account A owns document `Климат и урожай` and orphan generation with topic `Влияние климата на урожай`. |
| Test data | `q=климат`, `limit=20`. |
| Steps | 1. `GET /api/v1/projects?q=климат&limit=20` with account A's token. |
| Expected result | `200 OK` with `"total":2`; `items` holds both the `kind:"document"` and the `kind:"generation"` match on the same page. |
| Status | Not run |

### TC-12-API-EXT-1.7 — A term matching a document only through its body still pages correctly

| Field | Value |
|---|---|
| Description | The content arm is the expensive, unindexed one; if its filter is applied after the `LIMIT` rather than before, deep pages of body-only matches lose rows. |
| Preconditions | Account A owns 25 documents whose bodies contain `фотосинтез` and whose titles do not. |
| Test data | `q=фотосинтез&limit=10`, pages 1..3. |
| Steps | 1. Walk `page=1`, `page=2`, `page=3` at `limit=10`.<br>2. Union the returned `(kind,id)` pairs. |
| Expected result | Every page answers `200 OK` with `"total":25`; the union holds 25 distinct pairs with no duplicate and none missing. |
| Status | Not run |

---

## 2. Sorting Edges

### TC-12-API-EXT-2.1 — Sorting by type groups documents and generations of the same type together

| Field | Value |
|---|---|
| Description | `document_type` is NOT NULL on both tables, so `type_asc` must order across the union; a per-kind sort would split each type into two runs. |
| Preconditions | Account A owns documents and orphan generations of types `доклад`, `реферат` and `эссе`, at least two of each kind per type. |
| Test data | `sort=type_asc&limit=100`. |
| Steps | 1. `GET /api/v1/projects?sort=type_asc&limit=100` with account A's token.<br>2. Read the `(document_type, kind)` sequence. |
| Expected result | `200 OK`; all items of one `document_type` are contiguous regardless of `kind`; no `document_type` value appears in two separate runs. |
| Status | Not run |

### TC-12-API-EXT-2.2 — Every item is untitled under a title sort

| Field | Value |
|---|---|
| Description | "Nulls last" over a set that is entirely null is where a nulls-handling branch usually raises or returns an arbitrary order. |
| Preconditions | Account A owns 5 documents, all with `title = null`. |
| Test data | `sort=title_asc&limit=100`. |
| Steps | 1. `GET /api/v1/projects?sort=title_asc&limit=100`.<br>2. Repeat the identical request. |
| Expected result | Both answer `200 OK` with 5 items and no error; the id sequence is identical across the two reads, resolved by the `(kind,id)` tiebreak. |
| Status | Not run |

### TC-12-API-EXT-2.3 — Updated ordering reflects an edit

| Field | Value |
|---|---|
| Description | `updated_desc` is the default mental model of "what I was working on"; if `updated_at` is not written on save, the order silently mirrors creation order. |
| Preconditions | Account A owns document `Старый` created `2026-08-01T10:00:00Z` and document `Новый` created `2026-08-02T10:00:00Z`. |
| Test data | An edit-and-save of `Старый` at `2026-08-03T10:00:00Z`; `sort=updated_desc`. |
| Steps | 1. Save an edit to `Старый`.<br>2. `GET /api/v1/projects?sort=updated_desc` with account A's token. |
| Expected result | `200 OK`; `items[0]` is `Старый` with `updated_at` `2026-08-03T10:00:00Z`; `Новый` is second. |
| Status | Not run |

---

## 3. Paging Edges

### TC-12-API-EXT-3.1 — A limit of 1 pages the whole feed one item at a time

| Field | Value |
|---|---|
| Description | `limit=1` maximises the number of page boundaries, so any tiebreak weakness surfaces on every single step. |
| Preconditions | Account A owns 7 projects with two pairs sharing a `created_at`. |
| Test data | `limit=1&sort=created_desc`, pages 1..7. |
| Steps | 1. Walk pages 1..7 at `limit=1`.<br>2. Concatenate the returned ids. |
| Expected result | Each page answers `200 OK` with exactly one item; the 7 ids are distinct and their order equals the order of a single `limit=100` request under the same sort. |
| Status | Not run |

### TC-12-API-EXT-3.2 — The minimum and maximum limits are both accepted

| Field | Value |
|---|---|
| Description | Both ends of the inclusive range must be legal; the top end is also the one place a hidden lower cap (a default of 20 applied after validation) would show. |
| Preconditions | Account A owns 150 projects. |
| Test data | `limit=1`, then `limit=100`. |
| Steps | 1. `GET /api/v1/projects?limit=1`.<br>2. `GET /api/v1/projects?limit=100`. |
| Expected result | Step 1 answers `200 OK` with `"limit":1` and exactly 1 item; step 2 answers `200 OK` with `"limit":100` and exactly 100 items — not 20 and not `400 INVALID_LIMIT`. |
| Status | Not run |

### TC-12-API-EXT-3.3 — The deepest allowed page answers as fast as the first

| Field | Value |
|---|---|
| Description | `OFFSET 99900` scans and discards every preceding row; if the query has no index support the deep page is the lever that holds the pool open. |
| Preconditions | Account A owns enough projects to fill page 1000 at `limit=100`; the statement deadline is 3 s. |
| Test data | `page=1000&limit=100` versus `page=1&limit=100`; both measured over 5 runs. |
| Steps | 1. Time `GET /api/v1/projects?page=1&limit=100` five times and take the median.<br>2. Time `GET /api/v1/projects?page=1000&limit=100` five times and take the median. |
| Expected result | Both answer `200 OK`; the deep page's median duration is within the same bound as the first page's and stays under the 3 s statement deadline — it never returns `503 QUERY_TIMEOUT`. |
| Status | Not run |

### TC-12-API-EXT-3.4 — Repeating an identical list request returns an identical page

| Field | Value |
|---|---|
| Description | Over a static set the endpoint must be deterministic; any non-determinism here is an unstable order that paging cannot survive. |
| Preconditions | Account A owns 30 projects; nothing writes to them during the test. |
| Test data | `page=2&limit=10&sort=title_asc`. |
| Steps | 1. `GET /api/v1/projects?page=2&limit=10&sort=title_asc`.<br>2. Repeat the identical request.<br>3. Compare the two response bodies. |
| Expected result | Both answer `200 OK`; the JSON bodies are equal field for field — same items in the same order, same `page`, `limit` and `total`. |
| Status | Not run |

---

## 4. Preview Edges

### TC-12-API-EXT-4.1 — The preview of a document shorter than the preview bound is returned whole

| Field | Value |
|---|---|
| Description | Truncation logic that always cuts would clip a short document, and a card would show an ellipsis on text that fits. |
| Preconditions | Account A owns a document whose content is exactly `Короткая заметка о погоде.` (26 code points). |
| Test data | Content above; preview bound 200 code points. |
| Steps | 1. `GET /api/v1/projects?limit=20` with account A's token.<br>2. Read that item's `preview`. |
| Expected result | `200 OK`; `preview` is exactly `Короткая заметка о погоде.` — the full content, with no trailing ellipsis and nothing removed. |
| Status | Not run |

---

## 5. Retry Edges

### TC-12-API-EXT-5.1 — A retry issued after the source has reached its cap is refused before any write

| Field | Value |
|---|---|
| Description | The ceiling check must precede the insert; a row written and then rolled back still consumes an id and can leave an idempotency record behind. |
| Preconditions | Account A's source `c72e5a90-3b14-4d6f-9e88-01af4c2d7b65` has 5 recorded retries (at the cap). |
| Test data | Fresh `Idempotency-Key: k-ext51`. |
| Steps | 1. Record `SELECT count(*) FROM generations` for account A.<br>2. `POST /api/v1/generations/c72e5a90-…/retry` with `k-ext51`.<br>3. Re-read the count and query for `k-ext51`. |
| Expected result | `429 Too Many Requests` with `{"error_code":"RETRY_LIMIT_REACHED", …}`; the generation count is unchanged; no row and no idempotency record exists for `k-ext51`. |
| Status | Not run |

### TC-12-API-EXT-5.2 — A retry of a retry carries the original's parameters

| Field | Value |
|---|---|
| Description | Parameters must survive the chain; a copy that reads from the immediate parent rather than the stored fields would drift if any step normalized a value. |
| Preconditions | Source S (`реферат` / `Влияние климата на урожай` / 10 pages) failed; its retry `N1` also failed. |
| Test data | Retry `N1` with fresh `Idempotency-Key: k-ext52`. |
| Steps | 1. `POST /api/v1/generations/{N1}/retry` with `k-ext52`.<br>2. Read the created generation `N2`. |
| Expected result | `201 Created`; `N2` carries `document_type=реферат`, `topic=Влияние климата на урожай`, `volume_pages=10` — identical to source S's stored values. |
| Status | Not run |

### TC-12-API-EXT-5.3 — A retry request with a body is answered as if it had none

| Field | Value |
|---|---|
| Description | The endpoint declares no request body; an unexpected one must be ignored rather than parsed, or the mass-assignment surface the design removed comes back. |
| Preconditions | Account A owns source S with its stored parameters. |
| Test data | Body `{"topic":"Совершенно другая тема","volume_pages":99,"document_type":"эссе"}`; `Idempotency-Key: k-ext53`. |
| Steps | 1. `POST /api/v1/generations/c72e5a90-…/retry` with that key and that body.<br>2. Read the created generation. |
| Expected result | `201 Created` (not `400` for an unexpected body); the created generation carries `реферат` / `Влияние климата на урожай` / `10`; none of `Совершенно другая тема`, `99` or `эссе` is stored. |
| Status | Not run |

### TC-12-API-EXT-5.4 — A retry of a generation that is already a fresh child is refused

| Field | Value |
|---|---|
| Description | The child is `pending`, so it falls under the not-failed rule; retrying it would run the same work a third time while the second run is still going. |
| Preconditions | Account A retried source S seconds ago, producing generation `N` in `pending` and still fresh (well inside the 10-minute stale threshold). |
| Test data | Generation `N`; `Idempotency-Key: k-ext54`. |
| Steps | 1. `POST /api/v1/generations/{N}/retry` with that key.<br>2. Count account A's generations. |
| Expected result | `409 Conflict` with `{"error_code":"NOT_RETRYABLE", …}`; no third generation is created; `N` is still `pending` and unchanged. |
| Status | Not run |

---

## DSL Technical Reference

Inherits `01_API_Tests.md`.
