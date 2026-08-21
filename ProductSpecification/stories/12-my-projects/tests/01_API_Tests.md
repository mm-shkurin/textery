> **Implementation Order**: sequential TDD — feed composition → paging & sorting →
> search → input guards → preview & encoding → retry (side-effect guards) → failure
> handling.

# Мои проекты — API Tests

Endpoints: `GET /api/v1/projects` (read), `POST /api/v1/generations/{id}/retry` (write).
Contracts: `ProductSpecification/api-specs/projects_list.yaml`, `ProductSpecification/api-specs/generations_retry.yaml`.

> **Merge note (backend/frontend spec reconciliation).** The frontend branch's spec set
> named the write `POST /generations/{id}/repeat` and made a *stale* generation repeatable.
> Both readings are rejected here in favour of the implemented backend contract: the route
> is `/retry`, and a non-terminal generation past the stale threshold is `recovering` and
> **not** retryable — the sweep requeues it, and offering a retry there would duplicate work
> that is still running (see TC-12-API-1.5, TC-12-API-7.2, and `06_Integration_Tests.md` TC-12-INT-2.2).

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.projects@textery.test` / `Qa!Projects2026` |
| Account B (a stranger) | `qa.stranger@textery.test` / `Qa!Stranger2026` |
| Access token | `Authorization: Bearer <access token of account A>` |
| Document D1 | id `3f8b1c07-5a2d-4e91-b6c4-9d0e7a1f2b53`, title `Отчёт по практике`, `document_type` `реферат` |
| Document D2 | id `a1c46e2b-9d38-4f57-8b02-6e5c31a9d740`, title `Эссе о Пушкине`, `document_type` `эссе` |
| Generation G-failed | id `c72e5a90-3b14-4d6f-9e88-01af4c2d7b65`, topic `Влияние климата на урожай`, `status=failed` |
| Generation G-orphan | id `e5d90b31-7c62-44a8-b1f3-28ad6e094c17`, topic `История книгопечатания`, `status=completed`, no document links to it |
| Generation G-stale | id `9b3f0d54-1e87-4a2c-8d65-73c1f9e0a4b2`, topic `Экономика Сибири`, `status=in_progress`, `updated_at` 30 minutes ago |
| Account B's failed generation | id `6d21b8f4-0c93-4e57-a1d8-5b7e2f460a39` |
| Error body shape | `{"error_code": "<CODE>", "message": "<generic text>"}`; `correlation_id` added on 5xx only |
| Bounds in force | `page` 1..1000, `limit` 1..100 (default 20), `sort` default `created_desc`, `q` ≤ 200 code points, `preview` ≤ 200 code points, retry ceiling 5 per source, statement deadline 3 s, search-slot TTL 10 s, `GENERATION_STALE_AFTER_MINUTES=10` |

## 1. Feed Composition

### TC-12-API-1.1 — The feed shows the caller's documents and nothing of anyone else's

| Field | Value |
|---|---|
| Description | `owner_id` must be a query predicate, not a parameter. A missing scope here is a cross-account data leak on the story's primary read. |
| Preconditions | Account A owns D1 and D2. Account B owns its own document `f0a92e11-6b47-4c85-9d33-1e7b40c2a856`. |
| Test data | No query parameters (defaults `page=1&limit=20&sort=created_desc`). |
| Steps | 1. `GET /api/v1/projects` with account A's Bearer token. |
| Expected result | `200 OK`; `items` contains exactly the `(kind,id)` pairs `("document","3f8b1c07-…")` and `("document","a1c46e2b-…")`; no item has id `f0a92e11-6b47-4c85-9d33-1e7b40c2a856`; `total` is `2`. |
| Status | Not run |

### TC-12-API-1.2 — A generation that became a document appears once, as the document

| Field | Value |
|---|---|
| Description | A generation is represented by its document; showing both would list one piece of work twice and double every count on the screen. |
| Preconditions | Account A owns generation `4e8a7c02-9f15-4b63-8e07-c31d6a92b508`, `status=completed`, and document D1 was created from it. |
| Test data | No query parameters. |
| Steps | 1. `GET /api/v1/projects` with account A's token. |
| Expected result | `200 OK`; exactly one item derives from that work; it is `{"kind":"document","id":"3f8b1c07-5a2d-4e91-b6c4-9d0e7a1f2b53"}`; no item has `kind:"generation"` with id `4e8a7c02-9f15-4b63-8e07-c31d6a92b508`; `total` counts it once. |
| Status | Not run |

### TC-12-API-1.3 — A completed generation with no document is surfaced

| Field | Value |
|---|---|
| Description | The orphan completed generation is the row this feed exists to rescue — suppressing it loses paid work the user can no longer reach. |
| Preconditions | Account A owns G-orphan; no `Document` links to it. |
| Test data | G-orphan id `e5d90b31-7c62-44a8-b1f3-28ad6e094c17`. |
| Steps | 1. `GET /api/v1/projects` with account A's token. |
| Expected result | `200 OK`; an item `{"kind":"generation","id":"e5d90b31-7c62-44a8-b1f3-28ad6e094c17","status":"completed"}` is present. |
| Status | Not run |

### TC-12-API-1.4 — A failed generation is surfaced and marked retryable

| Field | Value |
|---|---|
| Description | `retryable` is what the «Повторить» button reads. Omitting the key, or leaving it false on a failed row, silently removes the user's only recovery path. |
| Preconditions | Account A owns G-failed; it has had 0 retries. |
| Test data | G-failed id `c72e5a90-3b14-4d6f-9e88-01af4c2d7b65`. |
| Steps | 1. `GET /api/v1/projects` with account A's token. |
| Expected result | `200 OK`; item `{"kind":"generation","id":"c72e5a90-…","status":"failed","retryable":true}` is present; the `retryable` key exists rather than being absent. |
| Status | Not run |

### TC-12-API-1.5 — A generation stuck past the stale threshold is marked recovering and not retryable

| Field | Value |
|---|---|
| Description | `RequeueStaleGenerations` is already re-running the row; a retry button on it runs the same work twice and bills it twice. |
| Preconditions | Account A owns G-stale, `status=in_progress`, `updated_at` 30 minutes ago; `GENERATION_STALE_AFTER_MINUTES=10`. |
| Test data | G-stale id `9b3f0d54-1e87-4a2c-8d65-73c1f9e0a4b2`. |
| Steps | 1. `GET /api/v1/projects` with account A's token. |
| Expected result | `200 OK`; that item reports `"status":"recovering"` and `"retryable":false`; it does not report `in_progress`. |
| Status | Not run |

### TC-12-API-1.6 — Every generation status has a defined feed outcome

| Field | Value |
|---|---|
| Description | A status with no rule is a row that vanishes. Each known status must be either surfaced with a mapped status or suppressed by a stated rule. |
| Preconditions | Account A owns one generation in each of `pending`, `in_progress`, `completed`, `failed`; two further generations (`completed`, `failed`) also have a document. |
| Test data | The six generations above, seeded by the fixture; `GENERATION_STALE_AFTER_MINUTES=10`, all rows fresh. |
| Steps | 1. `GET /api/v1/projects?limit=100` with account A's token.<br>2. Match every seeded generation id against `items`. |
| Expected result | `200 OK`; the two with documents appear only as `kind:"document"`; the other four appear as `kind:"generation"` reporting `pending`, `in_progress`, `completed`, `failed` respectively; no seeded generation is absent from both `items` and the documented suppression rule. |
| Status | Not run |

### TC-12-API-1.7 — An unrecognized generation status fails closed

| Field | Value |
|---|---|
| Description | Mapping an unknown status onto a displayed one flips a row's identity; `unknown` keeps the row visible without lying about it. |
| Preconditions | Account A owns generation `b7c48f30-2e61-4a95-8d0c-73f19b2e5a64` whose stored status is `archived`, a value this contract does not know. |
| Test data | Stored `status = 'archived'`. |
| Steps | 1. `GET /api/v1/projects` with account A's token.<br>2. Read the application log for that request. |
| Expected result | `200 OK`; the item is `{"kind":"generation","id":"b7c48f30-…","status":"unknown","retryable":false}`; `status` is not `pending`/`in_progress`/`completed`/`failed`/`recovering`; one log record carries both `b7c48f30-2e61-4a95-8d0c-73f19b2e5a64` and the literal value `archived`. |
| Status | Not run |

### TC-12-API-1.8 — A document and a generation sharing an id are two distinct items

| Field | Value |
|---|---|
| Description | `documents` and `generations` are separate id spaces. Keying on `id` alone instead of `(kind,id)` would collapse the two rows into one. |
| Preconditions | Account A owns document `d4f27a68-3c90-4b15-a7e2-8f60c93d1b47` and generation `d4f27a68-3c90-4b15-a7e2-8f60c93d1b47` (same uuid, different table). |
| Test data | Shared id `d4f27a68-3c90-4b15-a7e2-8f60c93d1b47`. |
| Steps | 1. `GET /api/v1/projects?limit=100` with account A's token. |
| Expected result | `200 OK`; two items carry that id, one with `"kind":"document"` and one with `"kind":"generation"`; `total` counts both. |
| Status | Not run |

---

### TC-12-API-1.9 — The recovering label flips exactly at the stale threshold, in its declared unit

| Field | Value |
|---|---|
| Description | An off-by-one or a minutes/seconds mix-up here either hides the retry button on live work or offers it on work the sweep is re-running. |
| Preconditions | The injected clock is pinned to `2026-08-20T12:00:00Z`; `GENERATION_STALE_AFTER_MINUTES=10`; account A owns three `in_progress` generations. |
| Test data | `updated_at` values `11:50:01Z` (9 min 59 s old), `11:50:00Z` (exactly 10 min), `11:49:59Z` (10 min 1 s). |
| Steps | 1. `GET /api/v1/projects?limit=100` with account A's token at the pinned instant. |
| Expected result | `200 OK`; the `11:50:00Z` and `11:49:59Z` rows report `"status":"recovering"`; the `11:50:01Z` row reports `"status":"in_progress"` with `"retryable":false`; all three classifications are computed from the injected clock, with no direct system-time read on the path. |
| Status | Not run |

### TC-12-API-1.10 — A missing or unparsable stale threshold fails closed

| Field | Value |
|---|---|
| Description | An unreadable threshold must never make every non-terminal row look retryable — that is fail-open on the one endpoint that spends money. |
| Preconditions | `GENERATION_STALE_AFTER_MINUTES` is unset, then blank, then `abc`; account A owns an `in_progress` generation of any age. |
| Test data | Generation `9b3f0d54-1e87-4a2c-8d65-73c1f9e0a4b2`; threshold values (unset), `""`, `abc`. |
| Steps | 1. For each threshold value, `GET /api/v1/projects` with account A's token.<br>2. `POST /api/v1/generations/9b3f0d54-1e87-4a2c-8d65-73c1f9e0a4b2/retry` with `Idempotency-Key: k-1010`. |
| Expected result | Every feed response reports that row with `"retryable":false`; every retry answers `409 Conflict` with `{"error_code":"NOT_RETRYABLE", …}`; no generation is created. |
| Status | Not run |

### TC-12-API-1.11 — A feed of known statuses emits no unknown-status signal

| Field | Value |
|---|---|
| Description | The fail-closed signal is only useful if it is silent on the normal path; a signal that fires on every read is one nobody will read. |
| Preconditions | Account A owns generations in `pending`, `in_progress`, `completed` and `failed` only. |
| Test data | The four generations above; log capture armed for the unrecognized-status signal. |
| Steps | 1. `GET /api/v1/projects?limit=100` with account A's token.<br>2. Inspect the captured log records for that request. |
| Expected result | `200 OK`; zero records carrying the unrecognized-status signal; no `"status":"unknown"` in `items`. |
| Status | Not run |

### TC-12-API-1.12 — A conversion committing during the read is still counted once

| Field | Value |
|---|---|
| Description | If `items` and the dedup projection are read in different snapshots, a conversion landing mid-read shows the work as both a generation and a document. |
| Preconditions | Account A owns generation `5c17e930-8a24-4f6b-b0e5-92d7c1a3f684`, `status=completed`; a `POST /api/v1/documents/from-generation` for it commits during the feed read. |
| Test data | Generation id above; the conversion commits between the two arms of the feed query. |
| Steps | 1. Start `GET /api/v1/projects?limit=100` with account A's token.<br>2. Commit the conversion while the request is in flight.<br>3. Read the returned page. |
| Expected result | `200 OK`; exactly one item derives from that work — either the generation or the document, never both; `total` matches the number of distinct `(kind,id)` pairs returned for it. |
| Status | Not run |

### TC-12-API-1.13 — A generation converted before the document link existed does not appear twice

| Field | Value |
|---|---|
| Description | Legacy rows whose `generation_id` link was never back-filled must not resurface as duplicate cards for work the user already has as a document. |
| Preconditions | Account A owns document `1a9c5f28-4d73-4e60-b8a1-6c92e05d3b7f` and generation `72b0d4e6-95a1-4c38-8f27-0e61b3d9a52c` from which it was made, but the document's `generation_id` is `NULL`. |
| Test data | The pair above. |
| Steps | 1. `GET /api/v1/projects?limit=100` with account A's token. |
| Expected result | `200 OK`; the work appears exactly once; `total` counts it once. |
| Status | Not run |

### TC-12-API-1.14 — A completed generation whose conversion failed is a retryable feed item

| Field | Value |
|---|---|
| Description | A completed generation whose conversion never landed is precisely the stranded work this feed rescues; it must carry a defined status rather than falling through the rules. |
| Preconditions | Account A owns generation `8f34c1a7-60b9-4d25-9e83-a5c07f2b1d69`, `status=completed`, whose `from-generation` conversion errored and left no document. |
| Test data | Generation id above; retry count 0. |
| Steps | 1. `GET /api/v1/projects?limit=100` with account A's token. |
| Expected result | `200 OK`; item `{"kind":"generation","id":"8f34c1a7-…"}` is present with a status from the contract's enum (not absent, not `unknown`) and carries `"retryable":true`. |
| Status | Not run |

### TC-12-API-1.15 — One arm failing fails the whole request

| Field | Value |
|---|---|
| Description | A half-populated page is worse than an error: the user reads "my generations are gone" and may re-create paid work. |
| Preconditions | Account A owns documents and generations; the generations arm of the feed query is made to raise. |
| Test data | Generations source forced to error; documents source healthy. |
| Steps | 1. `GET /api/v1/projects` with account A's token. |
| Expected result | A `5xx` (`503` `QUERY_TIMEOUT` when the failure is the deadline, otherwise `500`); the body is the `{error_code, message, correlation_id}` envelope; no `200` carrying only the document rows. |
| Status | Not run |

---

## 2. Paging

### TC-12-API-2.1 — Paging a static feed returns every row exactly once

| Field | Value |
|---|---|
| Description | The offset contract's basic promise over a set nobody is writing. A broken `OFFSET` shows a row twice or skips it entirely. |
| Preconditions | Account A owns 47 projects; nothing is written for the duration of the walk. |
| Test data | `limit=10`, pages `1`…`5`. |
| Steps | 1. `GET /api/v1/projects?page=1&limit=10`.<br>2. Repeat for `page=2`…`page=5`.<br>3. Union the returned `(kind,id)` pairs. |
| Expected result | Every page answers `200 OK` with `"limit":10` and its own `page`; the union holds 47 distinct pairs with no duplicate; the collected count equals the reported `"total":47`. |
| Status | Not run |

### TC-12-API-2.2 — The reported total counts the deduplicated feed

| Field | Value |
|---|---|
| Description | `total` must be counted over the same projection as `items`, or the pager offers a page the feed cannot fill. |
| Preconditions | Account A owns 3 plain documents, 2 orphan generations, and 1 generation that has a document. |
| Test data | The 6 rows above; the converted work is one document plus one suppressed generation. |
| Steps | 1. `GET /api/v1/projects?limit=100` with account A's token. |
| Expected result | `200 OK`; `"total":6`, not `7`; `items` has 6 entries; the converted work contributes exactly one. |
| Status | Not run |

### TC-12-API-2.3 — An empty feed reports a total of zero

| Field | Value |
|---|---|
| Description | A fresh account must get an empty page rather than a `404` or a null `items`, so the UI can show «Здесь пока ничего нет». |
| Preconditions | Account A owns no documents and no generations. |
| Test data | No query parameters. |
| Steps | 1. `GET /api/v1/projects` with account A's token. |
| Expected result | `200 OK`; `{"items":[],"page":1,"limit":20,"total":0}`; `items` is an empty array, not `null`. |
| Status | Not run |

### TC-12-API-2.4 — A page past the end is empty, not an error

| Field | Value |
|---|---|
| Description | A client that pages one step too far must see the end of the feed, not a refusal it has to special-case. |
| Preconditions | Account A owns 5 projects. |
| Test data | `page=1&limit=20`, then `page=2&limit=20` (still inside the 1..1000 bound). |
| Steps | 1. `GET /api/v1/projects?page=1&limit=20` and record `total`.<br>2. `GET /api/v1/projects?page=2&limit=20`. |
| Expected result | Step 2 answers `200 OK` with `"items":[]`, `"page":2`, and the same `"total":5` as step 1; it is not `400` and not `404`. |
| Status | Not run |

### TC-12-API-2.5 — The page and its total come from one consistent read

| Field | Value |
|---|---|
| Description | `items` and `total` read in two snapshots produce a pager that disagrees with the rows it is paging. |
| Preconditions | Account A owns 30 projects; a writer inserts and deletes account A's rows continuously during the request. |
| Test data | `page=1&limit=10`; concurrent writer running for the whole request. |
| Steps | 1. `GET /api/v1/projects?page=1&limit=10` with account A's token while the writer runs.<br>2. Compare `total` against the row count in the snapshot the page was read from. |
| Expected result | `200 OK`; `items` and `total` describe the same database snapshot — `total` equals the count of matching deduplicated rows visible in that snapshot; never `"total":0` alongside a non-empty `items`. |
| Status | Not run |

### TC-12-API-2.6 — A just-created project is visible to the very next request

| Field | Value |
|---|---|
| Description | Read-your-own-write. Replica lag or a stale cache here makes a user believe their new document was lost. |
| Preconditions | Account A signed in. |
| Test data | New document title `Свежий документ`. |
| Steps | 1. `POST /api/v1/documents` creating `Свежий документ`; record its id.<br>2. Immediately `GET /api/v1/projects?sort=created_desc` with the same token. |
| Expected result | Step 2 answers `200 OK` and `items[0]` is `{"kind":"document","id":"<the id from step 1>","title":"Свежий документ"}`. |
| Status | Not run |

---

### TC-12-API-2.7 — One page costs a fixed number of storage queries whatever the feed's size

| Field | Value |
|---|---|
| Description | An N+1 behind the union (a per-item preview read, a per-row status lookup) is correct at 5 rows and collapses the rate at 5000. |
| Preconditions | Account A owns 10 projects; account C `qa.bulk@textery.test` owns 5 000; the `ListProjects` repository port is call-counted. |
| Test data | `limit=20` for both accounts; counter reset before each request. |
| Steps | 1. `GET /api/v1/projects?limit=20` as account A; read the port's call count.<br>2. Reset the counter and repeat as account C. |
| Expected result | Both counts are equal and constant (independent of 10 vs 5 000 rows) and do not grow with the 20 items on the page. |
| Status | Not run |

### TC-12-API-2.8 — An insert during paging skips at most one item

| Field | Value |
|---|---|
| Description | The named cost of offset paging: it must be bounded and documented, not unbounded drift or a duplicated row. |
| Preconditions | Account A owns 40 projects sorted `created_desc`. |
| Test data | `limit=10`; one new document created between the page-1 and page-2 reads that sorts onto page 1. |
| Steps | 1. `GET /api/v1/projects?page=1&limit=10`.<br>2. Create one document that sorts onto page 1.<br>3. `GET /api/v1/projects?page=2&limit=10`.<br>4. Compare the two pages' `(kind,id)` sets. |
| Expected result | At most one item present in the pre-insert page 2 is missing from the post-insert page 2; no `(kind,id)` appears in both pages. |
| Status | Not run |

---

## 3. Sorting

### TC-12-API-3.1 — Each sort order returns the feed in that order

| Field | Value |
|---|---|
| Description | Five allowlisted orders, each mapped to a column on both tables. A silently ignored `sort` gives the user a control that does nothing. |
| Preconditions | Account A owns 4 projects differing in `created_at`, `updated_at`, `title` and `document_type`. |
| Test data | `sort=created_desc`, `created_asc`, `updated_desc`, `title_asc`, `type_asc`. |
| Steps | 1. `GET /api/v1/projects?sort=created_desc` and record the id sequence.<br>2. Repeat for each of the other four values. |
| Expected result | Each answers `200 OK`; the returned sequence is non-increasing in `created_at` for `created_desc` and `updated_at` for `updated_desc`, and non-decreasing in `created_at`, `title`/`topic`, `document_type` for `created_asc`, `title_asc`, `type_asc` respectively. |
| Status | Not run |

### TC-12-API-3.2 — Rows sharing a sort key keep a stable order across repeated reads

| Field | Value |
|---|---|
| Description | Without the `(kind,id)` tiebreak the database may return tied rows in any order, and a paging client will duplicate or drop them. |
| Preconditions | Account A owns two documents with identical `created_at = 2026-08-01T09:00:00Z`. |
| Test data | Documents `2b6e0a94-7d15-4c83-9f60-1a4e28b73d09` and `c8d13f57-4b02-4e69-8a15-3d70b96c2e14`; `sort=created_desc`. |
| Steps | 1. `GET /api/v1/projects?sort=created_desc` and record the order.<br>2. Repeat the identical request. |
| Expected result | Both responses are `200 OK` and place the two tied rows in the same relative order, resolved by the `(kind,id)` tiebreak. |
| Status | Not run |

### TC-12-API-3.3 — Untitled projects sort last by title

| Field | Value |
|---|---|
| Description | Postgres puts NULLs first by default under `ASC`; an untitled document leading the title sort would look like a broken feed. |
| Preconditions | Account A owns D1 (`Отчёт по практике`), D2 (`Эссе о Пушкине`), and document `0e5b7d23-8a41-4c96-b3f0-71d2c48e9a05` with `title = null`. |
| Test data | `sort=title_asc`. |
| Steps | 1. `GET /api/v1/projects?sort=title_asc` with account A's token. |
| Expected result | `200 OK`; `items[2]` is the untitled document `0e5b7d23-8a41-4c96-b3f0-71d2c48e9a05`; it is last, not first. |
| Status | Not run |

### TC-12-API-3.4 — Title ordering does not depend on the database's ambient locale

| Field | Value |
|---|---|
| Description | An unpinned collation makes the same feed order differently in development and in production, which is a bug nobody reproduces locally. |
| Preconditions | Account A owns documents titled `Анализ`, `анализ`, `Zebra`, `apple`; the database cluster's default locale is `C`. |
| Test data | `sort=title_asc`; pinned collation `ru-RU-x-icu`; expected sequence `анализ`, `Анализ`, `apple`, `Zebra`. |
| Steps | 1. `GET /api/v1/projects?sort=title_asc` against the `C`-locale database. |
| Expected result | `200 OK`; the returned title sequence is exactly `анализ`, `Анализ`, `apple`, `Zebra` — identical to the sequence produced on a `ru_RU.UTF-8` cluster. |
| Status | Not run |

### TC-12-API-3.5 — Generations are ordered alongside documents, not after them

| Field | Value |
|---|---|
| Description | A union sorted per-arm and then concatenated groups every generation at one end — the feed would stop being chronological. |
| Preconditions | Account A owns documents updated at `10:00` and `12:00` and orphan generations updated at `11:00` and `13:00` on 2026-08-18. |
| Test data | `sort=updated_desc`. |
| Steps | 1. `GET /api/v1/projects?sort=updated_desc` with account A's token. |
| Expected result | `200 OK`; the `kind` sequence is `generation, document, generation, document` (13:00, 12:00, 11:00, 10:00); no run of one kind at the head or the tail. |
| Status | Not run |

### TC-12-API-3.6 — An unrecognized sort order is refused

| Field | Value |
|---|---|
| Description | A silent fallback to the default tells the client its sort was honoured when it was not; the allowlist must refuse, not substitute. |
| Preconditions | Account A signed in with projects whose `created_desc` order is known. |
| Test data | `sort=updated_asc` (not in the allowlist). |
| Steps | 1. `GET /api/v1/projects?sort=updated_asc` with account A's token. |
| Expected result | `400 Bad Request`; body `{"error_code":"INVALID_SORT","message":"<generic text>"}`; no `items` array and no default-ordered feed in the response. |
| Status | Not run |

---

### TC-12-API-3.7 — A sort whose key ties across a page boundary returns each row exactly once

| Field | Value |
|---|---|
| Description | `type_asc` and `title_asc` tie massively by nature; if the tiebreak is not applied, a tie straddling a page edge duplicates and drops rows. |
| Preconditions | Account A owns 25 projects all of `document_type = реферат`, and separately 25 all titled `Реферат`. |
| Test data | `limit=10`; pages 1..3; `sort=type_asc`, then `sort=title_asc`. |
| Steps | 1. Walk pages 1..3 with `sort=type_asc` and union the `(kind,id)` pairs.<br>2. Repeat the same walk.<br>3. Repeat both walks with `sort=title_asc`. |
| Expected result | Each walk returns 25 distinct pairs with no duplicate and none missing; the repeated walk returns the same pairs in the same positions. |
| Status | Not run |

### TC-12-API-3.8 — Ordering is total when a document and a generation collide on both key and id

| Field | Value |
|---|---|
| Description | The last possible tie: same sort key, same uuid, different table. Only `kind` can break it, and if it does not, one of the two rows is served twice or never. |
| Preconditions | Account A owns a document and a generation both with id `d4f27a68-3c90-4b15-a7e2-8f60c93d1b47` and `created_at = 2026-08-05T14:00:00Z`. |
| Test data | `limit=1`, `sort=created_desc`, pages 1 and 2. |
| Steps | 1. Walk `page=1` then `page=2` with `limit=1`.<br>2. Repeat the identical walk. |
| Expected result | Both walks return the same two items in the same order, distinguished by `kind`; neither row appears twice and neither is skipped. |
| Status | Not run |

---

## 4. Search

### TC-12-API-4.1 — Search matches title, generation topic and document content

| Field | Value |
|---|---|
| Description | Three match surfaces in one union. Dropping the content arm makes the search look broken for a user who titled nothing. |
| Preconditions | Account A owns document `Климат и урожай` (title match), generation `c72e5a90-…` with topic `Влияние климата на урожай` (topic match), and document `Заметки` whose body contains `климат` (content match). |
| Test data | `q=климат`. |
| Steps | 1. `GET /api/v1/projects?q=климат` with account A's token. |
| Expected result | `200 OK`; `total` is `3`; `items` contains all three `(kind,id)` pairs — the title match, the generation topic match and the body-only match. |
| Status | Not run |

### TC-12-API-4.2 — Search is case-insensitive and normalization-stable

| Field | Value |
|---|---|
| Description | Compared under an explicit collation and NFC-normalized on both sides, so the result does not depend on the database's ambient locale or the client's keyboard. |
| Preconditions | Account A owns a document titled `Ёлка в Сибири` stored in NFC. |
| Test data | `q=ёлка`, `q=ЁЛКА`, `q=Ёлка`, and `q=Ёлка` typed in NFD (`Е` + U+0308). |
| Steps | 1. `GET /api/v1/projects?q=ёлка`.<br>2. Repeat with `ЁЛКА`.<br>3. Repeat with `Ёлка`.<br>4. Repeat with the NFD spelling. |
| Expected result | All four answer `200 OK` with `"total":1` and the same document id in `items[0]`. |
| Status | Not run |

### TC-12-API-4.3 — Search matches wildcard characters literally

| Field | Value |
|---|---|
| Description | An unescaped `%` in an `ILIKE` pattern matches everything — the user searching for a percent sign would get their whole feed back. |
| Preconditions | Account A owns document `Скидка 50% на подписку` and 4 documents containing no percent sign. |
| Test data | `q=%`. |
| Steps | 1. `GET /api/v1/projects?q=%25` (percent-encoded `%`) with account A's token. |
| Expected result | `200 OK`; `"total":1`; `items` holds only `Скидка 50% на подписку`; the other four documents are absent. |
| Status | Not run |

### TC-12-API-4.4 — A whitespace-only query behaves as no search

| Field | Value |
|---|---|
| Description | A debounced input can send a query of spaces; treating it as a real term would empty the feed with no explanation. |
| Preconditions | Account A owns 5 projects. |
| Test data | `q=%20%20%20` (three spaces). |
| Steps | 1. `GET /api/v1/projects` and record `total`.<br>2. `GET /api/v1/projects?q=%20%20%20`. |
| Expected result | Both answer `200 OK` with `"total":5` and the same 5 `(kind,id)` pairs; step 2 is not empty and is not a `400`. |
| Status | Not run |

### TC-12-API-4.5 — Search combines with sorting and paging

| Field | Value |
|---|---|
| Description | Filter, order and offset must compose; a `total` computed before the filter would offer pages of results that do not exist. |
| Preconditions | Account A owns 25 projects matching `отчёт` and 30 that do not. |
| Test data | `q=отчёт&sort=title_asc&page=2&limit=10`. |
| Steps | 1. `GET /api/v1/projects?q=отчёт&sort=title_asc&page=2&limit=10` with account A's token. |
| Expected result | `200 OK`; `"total":25` (the filtered count, not `55`); `items` holds exactly items 11–20 of the `отчёт` set in `title_asc` order; every returned item matches `отчёт`. |
| Status | Not run |

### TC-12-API-4.8 — Changing the sort under an active search returns the same set from its first page

| Field | Value |
|---|---|
| Description | Reordering must not silently re-filter, and must not leave the caller on a page index that no longer means the same thing. |
| Preconditions | Account A owns 6 projects matching `эссе`. |
| Test data | `q=эссе&sort=created_desc`, then `q=эссе&sort=title_asc&page=1`. |
| Steps | 1. `GET /api/v1/projects?q=эссе&sort=created_desc&limit=20`; record the `(kind,id)` set.<br>2. `GET /api/v1/projects?q=эссе&sort=title_asc&page=1&limit=20`. |
| Expected result | Both answer `200 OK` with `"total":6` and the identical `(kind,id)` set; step 2 reports `"page":1` and orders the set by title. |
| Status | Not run |

### TC-12-API-4.6 — Search never crosses account boundaries

| Field | Value |
|---|---|
| Description | Search is the easiest place to lose the owner predicate, because the filter clause is what the developer is thinking about. |
| Preconditions | Account B owns a document titled `Крыжовниковый синтез` — a term appearing nowhere in account A's data. |
| Test data | `q=Крыжовниковый`. |
| Steps | 1. `GET /api/v1/projects?q=Крыжовниковый` with account A's token. |
| Expected result | `200 OK`; `{"items":[], "total":0}`; account B's document is not returned and nothing hints that it exists. |
| Status | Not run |

---

### TC-12-API-4.7 — Case-folding does not depend on the session's locale

| Field | Value |
|---|---|
| Description | Turkish-locale case folding maps `I` to `ı`, so the same query matches in one session and not in another — an unpinned collation makes search non-deterministic. |
| Preconditions | Account A owns a document titled `INDEX методики`; the database session locale is varied between `C`, `ru_RU.UTF-8` and `tr_TR.UTF-8`. |
| Test data | `q=index`; pinned collation `ru-RU-x-icu`. |
| Steps | 1. `GET /api/v1/projects?q=index` with account A's token.<br>2. Repeat under each of the three session locales. |
| Expected result | All three answer `200 OK` with `"total":1` and the `INDEX методики` document in `items[0]`; the result does not change with the session locale. |
| Status | Not run |

---

## 5. Input Guards

### TC-12-API-5.1 — A page or limit outside its range is refused

| Field | Value |
|---|---|
| Description | `page` bounds the `OFFSET` arithmetic and the deep-scan lever; `limit` bounds the page size. A silent clamp hides that the client asked for something impossible. |
| Preconditions | Account A signed in. |
| Test data | `page=0`, `page=1001`, `limit=0`, `limit=101`. |
| Steps | 1. `GET /api/v1/projects?page=0`.<br>2. `GET /api/v1/projects?page=1001`.<br>3. `GET /api/v1/projects?limit=0`.<br>4. `GET /api/v1/projects?limit=101`. |
| Expected result | Steps 1–2 answer `400 Bad Request` with `{"error_code":"INVALID_PAGE", …}`; steps 3–4 answer `400` with `{"error_code":"INVALID_LIMIT", …}`; the envelope is this project's `{error_code, message}`, not the framework's validation shape. |
| Status | Not run |

### TC-12-API-5.2 — A non-integer page or limit is refused, not truncated

| Field | Value |
|---|---|
| Description | Coercing `2.5` to `2` serves a page the client did not ask for; accepting `1e3` smuggles past a naive bound check. |
| Preconditions | Account A signed in with projects. |
| Test data | `page=2.5`, `page=1e3`, `page=%2B1` (`+1`), `page=0x10`. |
| Steps | 1. `GET /api/v1/projects?page=2.5`.<br>2. Repeat with `1e3`, `+1` and `0x10`. |
| Expected result | Each answers `400 Bad Request` with `{"error_code":"INVALID_PAGE", …}`; no `items` array is returned in any of the four responses. |
| Status | Not run |

### TC-12-API-5.3 — A search query over the length bound is refused, measured in code points

| Field | Value |
|---|---|
| Description | The bound is 200 Unicode code points, not UTF-16 units and not bytes — the three disagree at exactly the boundary this case tests. |
| Preconditions | Account A signed in. |
| Test data | `q` = the Cyrillic letter `я` repeated 200 times (200 code points, 400 bytes), then repeated 201 times. |
| Steps | 1. `GET /api/v1/projects?q=<я×200>` with account A's token.<br>2. `GET /api/v1/projects?q=<я×201>`. |
| Expected result | Step 1 answers `200 OK` with an `items` array; step 2 answers `400 Bad Request` with `{"error_code":"INVALID_QUERY", …}`. |
| Status | Not run |

---

### TC-12-API-5.4 — A page or limit beyond the integer type is refused, not overflowed

| Field | Value |
|---|---|
| Description | A value past the machine integer either raises an internal error (a 500 the client cannot act on) or wraps into a valid-looking small number. |
| Preconditions | Account A signed in. |
| Test data | `page=9223372036854775808` (2^63), `limit=1234567890123456789012345678901234567890` (40 digits). |
| Steps | 1. `GET /api/v1/projects?page=9223372036854775808`.<br>2. `GET /api/v1/projects?limit=1234567890123456789012345678901234567890`. |
| Expected result | Step 1 answers `400` with `{"error_code":"INVALID_PAGE", …}`; step 2 answers `400` with `{"error_code":"INVALID_LIMIT", …}`; neither is a `500` and neither is served as a clamped `page=1000` / `limit=100`. |
| Status | Not run |

### TC-12-API-5.5 — Omitted, empty and repeated parameters have pinned outcomes

| Field | Value |
|---|---|
| Description | Absent, empty and duplicated are three different inputs; leaving any of them to framework default behaviour makes the contract unpredictable across a proxy that reorders query strings. |
| Preconditions | Account A owns projects whose `created_desc` order is known. |
| Test data | (a) no `sort`, no `q`; (b) `sort=&q=`; (c) `sort=title_asc&sort=type_asc`. |
| Steps | 1. `GET /api/v1/projects`.<br>2. `GET /api/v1/projects?sort=&q=`.<br>3. `GET /api/v1/projects?sort=title_asc&sort=type_asc`. |
| Expected result | Step 1 answers `200 OK` ordered `created_desc` with no filtering applied. Step 2 answers `400` with `{"error_code":"INVALID_SORT", …}`; when only `q=` is sent it answers `200 OK` with the full unfiltered feed. Step 3 answers `400` with `{"error_code":"INVALID_SORT", …}` rather than picking either value. |
| Status | Not run |

---

## 6. Preview & Output Encoding

### TC-12-API-6.1 — The list never returns full document content

| Field | Value |
|---|---|
| Description | The page's byte size must not scale with stored document size; a full body per card is what turns a 20-item page into a megabyte. |
| Preconditions | Account A owns document `Длинный отчёт` whose content is 50 000 characters, beginning `Введение. Настоящая работа посвящена…`. |
| Test data | `limit=20`; preview bound 200 code points. |
| Steps | 1. `GET /api/v1/projects?limit=20` with account A's token.<br>2. Measure the length of that item's `preview` in code points. |
| Expected result | `200 OK`; `preview` is at most 200 code points and starts with `Введение. Настоящая работа посвящена`; no `content`, `body` or `html` field appears anywhere in the response. |
| Status | Not run |

### TC-12-API-6.2 — Preview truncation does not split a character

| Field | Value |
|---|---|
| Description | Cutting at byte 200 splits a surrogate pair or a combining sequence and yields `U+FFFD` on the card. |
| Preconditions | Account A owns a document whose content places the emoji `👩‍💻` (a ZWJ sequence) and the sequence `е` + U+0301 astride code point 200. |
| Test data | Content constructed so the grapheme boundary falls at code points 198–203. |
| Steps | 1. `GET /api/v1/projects?limit=20` with account A's token.<br>2. Inspect the last characters of that item's `preview`. |
| Expected result | `200 OK`; `preview` ends on a complete grapheme cluster (the whole ZWJ sequence or nothing of it); it contains no `U+FFFD` and no lone surrogate; its length is ≤ 200 code points. |
| Status | Not run |

### TC-12-API-6.3 — Stored markup is neutralized in every echoed field

| Field | Value |
|---|---|
| Description | Three echoed fields, one rule. Sanitizing the preview but not the title is the classic half-fix that still ships stored XSS. |
| Preconditions | Account A owns a document titled `<script>alert(1)</script>`, a document whose body is `<img src=x onerror=alert(1)>Текст`, and a generation whose topic is `<b>жирный</b>`. |
| Test data | The three payloads above. |
| Steps | 1. `GET /api/v1/projects?limit=20` with account A's token.<br>2. Read the raw JSON bytes of `title`, `preview` and the generation's `title`. |
| Expected result | `200 OK`; none of the three values contains an executable tag — `<script`, `onerror=` and `<b>` are absent from the returned strings (stripped or escaped); the readable text `Текст` and `жирный` survives. |
| Status | Not run |

### TC-12-API-6.4 — Timestamps are returned as UTC instants

| Field | Value |
|---|---|
| Description | A naive local timestamp reorders the feed for anyone not in the server's zone and makes «сегодня» wrong on the card. |
| Preconditions | The server's `TZ` is `Europe/Moscow`; account A owns projects created at `2026-08-17T23:30:00+03:00` and `2026-08-18T00:30:00+03:00`. |
| Test data | `sort=created_desc`. |
| Steps | 1. `GET /api/v1/projects?sort=created_desc` with account A's token. |
| Expected result | `200 OK`; `created_at` values are `2026-08-17T21:30:00Z` and `2026-08-17T20:30:00Z` (ISO-8601 with an explicit offset, never bare `2026-08-17 23:30:00`); the later true instant is `items[0]`. |
| Status | Not run |

---

### TC-12-API-6.5 — Multibyte text survives storage and listing unchanged

| Field | Value |
|---|---|
| Description | An encoding mistake anywhere on the write-store-read path turns a user's title into mojibake or replacement characters. |
| Preconditions | Account A owns a document titled `Отчёт 𝒜 漢字 é 🎓` and a generation whose topic is the same string. |
| Test data | Title/topic `Отчёт 𝒜 漢字 é (e + U+0301) 🎓` — an astral-plane letter, CJK ideographs, a combining accent and an emoji. |
| Steps | 1. `GET /api/v1/projects?limit=20` with account A's token.<br>2. Compare the returned `title` of both items against the stored bytes. |
| Expected result | `200 OK`; both returned strings are code-point-for-code-point equal to the stored value; no `U+FFFD` appears in `title`, `preview` or any other field. |
| Status | Not run |

### TC-12-API-6.6 — Attacker-controlled values cannot forge a log record

| Field | Value |
|---|---|
| Description | A newline in a value that reaches a line-oriented log lets a user write a second, fake record — enough to hide a real one from an operator grepping the log. |
| Preconditions | Account A owns a generation whose stored status is `archived\nlevel=ERROR msg="forged"`. |
| Test data | Search query `климат\nlevel=ERROR msg="forged"`; the stored status above. |
| Steps | 1. `GET /api/v1/projects?q=климат%0Alevel%3DERROR%20msg%3D%22forged%22` with account A's token.<br>2. Read the captured log output for that request. |
| Expected result | Each emitted record is a single structured (JSON) event carrying the value inside one field with the newline escaped as `\n`; no standalone line parses as a second record; no record has `level` `ERROR` with `msg` `forged`. |
| Status | Not run |

---

## 7. Retry — Guards

### TC-12-API-7.1 — Retrying a non-existent or foreign generation is refused indistinguishably

| Field | Value |
|---|---|
| Description | A `403` on a foreign id confirms the id exists; the two refusals must be byte-identical so ids cannot be probed. |
| Preconditions | Account B owns failed generation `6d21b8f4-0c93-4e57-a1d8-5b7e2f460a39`; no generation has id `00000000-0000-4000-8000-000000000000`. |
| Test data | Both ids above; `Idempotency-Key: k-0701`. |
| Steps | 1. `POST /api/v1/generations/6d21b8f4-0c93-4e57-a1d8-5b7e2f460a39/retry` with account A's token and `Idempotency-Key: k-0701a`.<br>2. `POST /api/v1/generations/00000000-0000-4000-8000-000000000000/retry` with `Idempotency-Key: k-0701b`.<br>3. Compare the two responses. |
| Expected result | Both answer `404 Not Found` with the same `{error_code, message}` body bytes and the same headers bar `Date`; neither is `403`; the `generations` row count for both accounts is unchanged. |
| Status | Not run |

### TC-12-API-7.2 — Retrying a generation that is not failed is refused

| Field | Value |
|---|---|
| Description | Only a `failed` source may be retried — a running one is the sweep's job, and a completed one already produced its work. |
| Preconditions | Account A owns generations `p1` (`pending`), `p2` (`in_progress`, fresh) and `p3` (`completed`). |
| Test data | The three ids above; fresh `Idempotency-Key` per call. |
| Steps | 1. `POST /api/v1/generations/{p1}/retry` with `Idempotency-Key: k-0702a`.<br>2. Repeat for `p2` with `k-0702b`.<br>3. Repeat for `p3` with `k-0702c`. |
| Expected result | All three answer `409 Conflict` with `{"error_code":"NOT_RETRYABLE", …}`; the `generations` row count for account A is unchanged after all three. |
| Status | Not run |

### TC-12-API-7.3 — A missing or oversized idempotency key is refused

| Field | Value |
|---|---|
| Description | The key is the only thing standing between a retried click and a second paid generation; it must be required and bounded before any write. |
| Preconditions | Account A owns G-failed `c72e5a90-3b14-4d6f-9e88-01af4c2d7b65`. |
| Test data | No `Idempotency-Key` header; `Idempotency-Key:` (blank); `Idempotency-Key` of 129 characters. |
| Steps | 1. `POST /api/v1/generations/c72e5a90-…/retry` with no `Idempotency-Key` header.<br>2. Repeat with a blank header value.<br>3. Repeat with a 129-character key. |
| Expected result | Steps 1–2 answer `400 Bad Request` with `{"error_code":"MISSING_IDEMPOTENCY_KEY", …}`; step 3 answers `400` with `{"error_code":"INVALID_IDEMPOTENCY_KEY", …}`; no generation is created by any of the three. |
| Status | Not run |

---

### TC-12-API-7.4 — Retrying a generation in an unrecognized status is refused

| Field | Value |
|---|---|
| Description | Fail-closed on a paid operation: a status the code does not understand must not be treated as "probably failed, go ahead". |
| Preconditions | Account A owns generation `b7c48f30-2e61-4a95-8d0c-73f19b2e5a64` whose stored status is `archived`. |
| Test data | Id above; `Idempotency-Key: k-0704`. |
| Steps | 1. `POST /api/v1/generations/b7c48f30-…/retry` with account A's token and that key.<br>2. Read the source row.<br>3. `GET /api/v1/projects?limit=100`. |
| Expected result | Step 1 answers `409 Conflict` with `{"error_code":"NOT_RETRYABLE", …}`; no generation is created; the source row's `status`, `updated_at` and parameters are byte-identical to before; the feed reports that item with `"status":"unknown","retryable":false`. |
| Status | Not run |

### TC-12-API-7.5 — Retrying a generation that has since become a document is refused with its current status

| Field | Value |
|---|---|
| Description | The card in the browser is a snapshot; by the time the click lands the work may be done, and the refusal must tell the client what actually happened so it can refresh instead of dead-ending. |
| Preconditions | Account A's generation `5c17e930-8a24-4f6b-b0e5-92d7c1a3f684` was `failed` when the card rendered and is now `completed` with a document created from it. |
| Test data | Id above; `Idempotency-Key: k-0705`. |
| Steps | 1. Render the feed while the generation is `failed`.<br>2. Move the generation to `completed` and create its document.<br>3. `POST /api/v1/generations/5c17e930-…/retry` with that key. |
| Expected result | `409 Conflict` with `{"error_code":"NOT_RETRYABLE", …}` whose `message` names the source's current status `completed`; no generation is created. |
| Status | Not run |

---

## 8. Retry — Side-Effect Safety

### TC-12-API-8.1 — A retry creates a new generation from the source's stored parameters

| Field | Value |
|---|---|
| Description | Parameters are copied server-side from the row, so there is no field a client could over-bind — and the source must be left intact for the feed to keep showing it. |
| Preconditions | Account A owns G-failed with `document_type=реферат`, `topic=Влияние климата на урожай`, `volume_pages=10`. |
| Test data | Source id `c72e5a90-3b14-4d6f-9e88-01af4c2d7b65`; `Idempotency-Key: k-0801`; no request body. |
| Steps | 1. `POST /api/v1/generations/c72e5a90-…/retry` with account A's token and that key.<br>2. Read the source row afterwards. |
| Expected result | `201 Created`; body `{"id":"<new uuid>","status":"pending","document_type":"реферат","topic":"Влияние климата на урожай","volume_pages":10,"created_at":"<now>"}`; the new row's owner is account A; the source's `status`, `topic`, `volume_pages` and `updated_at` are unchanged. |
| Status | Not run |

### TC-12-API-8.2 — The failed source stays in the feed beside the new generation

| Field | Value |
|---|---|
| Description | Nothing is deleted or mutated by a retry, so the user never watches a card vanish with nothing in its place. |
| Preconditions | Account A has retried G-failed once; the new generation `n1` exists. |
| Test data | Source `c72e5a90-…`; new generation id from the `201`. |
| Steps | 1. `GET /api/v1/projects?limit=100` with account A's token. |
| Expected result | `200 OK`; both `{"kind":"generation","id":"c72e5a90-…","status":"failed"}` and `{"kind":"generation","id":"<n1>","status":"pending"}` are present in `items`. |
| Status | Not run |

### TC-12-API-8.3 — A duplicate retry produces one generation (inbound)

| Field | Value |
|---|---|
| Description | A double click, a retried fetch or an impatient user must not buy two generations. |
| Preconditions | Account A owns G-failed; no retry has been made. |
| Test data | `Idempotency-Key: k-0803`, sent twice against the same source. |
| Steps | 1. `POST /api/v1/generations/c72e5a90-…/retry` with `Idempotency-Key: k-0803`.<br>2. Send the identical request again. |
| Expected result | Step 1 answers `201 Created`; step 2 answers `200 OK`; both bodies carry the same `id`; exactly one new `generations` row exists for account A. |
| Status | Not run |

### TC-12-API-8.4 — A retry whose response was lost creates no second generation (outbound)

| Field | Value |
|---|---|
| Description | The client cannot tell "never arrived" from "answer lost"; only a server-side key makes the safe resend safe. |
| Preconditions | Account A owns G-failed; a retry with `k-0804` reached the server and committed, but the response was dropped in transit. |
| Test data | `Idempotency-Key: k-0804`. |
| Steps | 1. Issue the retry and drop the response before the client reads it.<br>2. Re-send the identical request with `Idempotency-Key: k-0804`. |
| Expected result | Step 2 answers `200 OK` with the `id` the first attempt created; the `generations` count for account A grew by exactly one across both calls. |
| Status | Not run |

### TC-12-API-8.5 — Concurrent retries across instances produce one generation

| Field | Value |
|---|---|
| Description | An in-process lock bounds nothing across replicas; only the `(owner_id, Idempotency-Key)` unique index does. |
| Preconditions | Account A owns G-failed; two application instances are running behind the load balancer. |
| Test data | `Idempotency-Key: k-0805`, sent simultaneously to instance 1 and instance 2. |
| Steps | 1. Release both requests at the same instant, one per instance. |
| Expected result | One answers `201 Created` and the other `200 OK` (never a `500` from a raw unique-violation); both bodies carry the same `id`; exactly one new `generations` row exists. |
| Status | Not run |

### TC-12-API-8.6 — One account's key never matches another account's record

| Field | Value |
|---|---|
| Description | Keying the replay on the header alone short-circuits before any ownership logic and returns another account's generation — a cross-account disclosure. |
| Preconditions | Account B has retried its own failed generation with `Idempotency-Key: k-0806`; account A owns G-failed and has used no key. |
| Test data | `Idempotency-Key: k-0806` reused by account A. |
| Steps | 1. `POST /api/v1/generations/c72e5a90-…/retry` with account A's token and `Idempotency-Key: k-0806`. |
| Expected result | `201 Created`; the returned `id` is a new generation owned by account A; it is not the id account B's retry created; nothing from account B appears in the body. |
| Status | Not run |

### TC-12-API-8.7 — A fresh key after a terminal outcome starts a new generation

| Field | Value |
|---|---|
| Description | Without the fresh-key rule the button goes silently dead on the second failure — the user clicks and gets the old failed run back. |
| Preconditions | Account A retried G-failed with `k-0807a`; that retry itself reached `failed`. |
| Test data | `Idempotency-Key: k-0807b` (fresh); source still under the ceiling of 5. |
| Steps | 1. `POST /api/v1/generations/c72e5a90-…/retry` with `Idempotency-Key: k-0807b`. |
| Expected result | `201 Created` with `"status":"pending"` and an `id` different from the `k-0807a` generation; a third `generations` row now exists for that source. |
| Status | Not run |

### TC-12-API-8.8 — The same key against a different source is refused

| Field | Value |
|---|---|
| Description | Answering `200` with the first source's generation would silently retry the wrong work; detecting it is what `source_generation_id` exists for. |
| Preconditions | Account A retried source `c72e5a90-…` with `k-0808`; account A also owns a second failed generation `1f6c3b85-92d0-47ae-b4c1-08e5d7a26f39`. |
| Test data | `Idempotency-Key: k-0808` against the second source. |
| Steps | 1. `POST /api/v1/generations/1f6c3b85-…/retry` with account A's token and `Idempotency-Key: k-0808`. |
| Expected result | `409 Conflict` with `{"error_code":"IDEMPOTENCY_KEY_REUSED", …}`; no generation is created for the second source; the first source's retry is not returned. |
| Status | Not run |

### TC-12-API-8.9 — Retries of one source are capped

| Field | Value |
|---|---|
| Description | The fresh-key rule means idempotency bounds nothing; the ceiling is the only thing stopping a scripted client retrying one row forever, and this is the endpoint that spends money. |
| Preconditions | Account A has retried G-failed 5 times, each with a fresh key. |
| Test data | `Idempotency-Key: k-0809f` (a 6th fresh key); ceiling 5. |
| Steps | 1. `POST /api/v1/generations/c72e5a90-…/retry` with `Idempotency-Key: k-0809f`.<br>2. `GET /api/v1/projects?limit=100`. |
| Expected result | Step 1 answers `429 Too Many Requests` with `{"error_code":"RETRY_LIMIT_REACHED", …}`; no 6th generation row exists; the feed reports the source with `"retryable":false`. |
| Status | Not run |

---

### TC-12-API-8.10 — Idempotency keys are compared exactly

| Field | Value |
|---|---|
| Description | A key folded to lower case or NFC-normalized would collapse two distinct client keys into one and swallow a legitimate second retry. |
| Preconditions | Account A owns G-failed under the ceiling; a retry was accepted with key `Key-ABC`. |
| Test data | `Key-abc` (case differs), `Ké` in NFC vs NFD, and a key of 128 Cyrillic characters (128 code points). |
| Steps | 1. Retry the same source with `Idempotency-Key: Key-abc`.<br>2. Retry with the NFC spelling of `Ké…`, then with the NFD spelling.<br>3. Retry with the 128-code-point Cyrillic key. |
| Expected result | Each byte-distinct key is treated as new: it answers `201 Created` while the source is under the ceiling, and `429 RETRY_LIMIT_REACHED` once past it — never `200` replaying `Key-ABC`; the 128-code-point key is accepted (not `400 INVALID_IDEMPOTENCY_KEY`). |
| Status | Not run |

### TC-12-API-8.11 — The retry at the ceiling is accepted and only the next is refused

| Field | Value |
|---|---|
| Description | An off-by-one on the ceiling either steals the user's fifth legitimate retry or grants a sixth. |
| Preconditions | Account A's source `c72e5a90-…` has 4 recorded retries; ceiling is 5. |
| Test data | Fresh keys `k-0811e` then `k-0811f`. |
| Steps | 1. `POST /api/v1/generations/c72e5a90-…/retry` with `k-0811e`.<br>2. `POST /api/v1/generations/c72e5a90-…/retry` with `k-0811f`. |
| Expected result | Step 1 answers `201 Created` with `"status":"pending"`; step 2 answers `429` with `{"error_code":"RETRY_LIMIT_REACHED", …}` and creates nothing; the recorded retry count is exactly `5`. |
| Status | Not run |

### TC-12-API-8.12 — Concurrent retries at the ceiling cannot exceed it

| Field | Value |
|---|---|
| Description | A read-then-write count check is a race: two requests both read 4 and both write, and the account pays for six generations against a ceiling of five. |
| Preconditions | Account A's source has 4 recorded retries; two requests are held together between the count read and the write. |
| Test data | Distinct fresh keys `k-0812a` and `k-0812b`; ceiling 5. |
| Steps | 1. Release both requests simultaneously.<br>2. Read the source's recorded retry count. |
| Expected result | Exactly one answers `201 Created`; the other answers `429 RETRY_LIMIT_REACHED`; exactly one new `generations` row was written; the stored retry count is exactly `5`, never `6`. |
| Status | Not run |

### TC-12-API-8.13 — A retry's generation starts in the initial status, not the source's

| Field | Value |
|---|---|
| Description | Copying `status=failed` onto the new row would create a generation nothing ever runs — and copying the source's id or timestamps would let a client fix server-owned values. |
| Preconditions | Account A owns G-failed, created `2026-08-01T08:00:00Z`. |
| Test data | Source `c72e5a90-…`; `Idempotency-Key: k-0813`. |
| Steps | 1. `POST /api/v1/generations/c72e5a90-…/retry` with that key.<br>2. Read the created row. |
| Expected result | `201 Created` with `"status":"pending"` (not `failed`); the `id` differs from the source's; `created_at` is the current instant, not `2026-08-01T08:00:00Z`; `owner_id` is account A and `source_generation_id` is `c72e5a90-…`; only `document_type`, `topic` and `volume_pages` equal the source's. |
| Status | Not run |

### TC-12-API-8.14 — A retry that fails on its last write leaves no orphan

| Field | Value |
|---|---|
| Description | A committed idempotency record without its generation makes the key permanently dead; a committed generation without the record makes a resend buy a second one. |
| Preconditions | Account A owns G-failed with a known retry count; the retry's final write is made to fail after the earlier statements. |
| Test data | `Idempotency-Key: k-0814`; recorded retry count before the call. |
| Steps | 1. `POST /api/v1/generations/c72e5a90-…/retry` with `k-0814` against the fault-injected write.<br>2. Query `generations` for `k-0814` and for its source.<br>3. Read the source's recorded retry count. |
| Expected result | The response is a `5xx` from the `{error_code, message, correlation_id}` envelope; no `generations` row and no idempotency record exists for `k-0814`; the recorded retry count equals the value from before the call. |
| Status | Not run |

### TC-12-API-8.15 — A source whose retry already succeeded can be retried again

| Field | Value |
|---|---|
| Description | Retryability is a property of the failed source, not of what happened downstream; a user unhappy with the successful retry may still spend another of the five. |
| Preconditions | Account A retried G-failed once; that retry completed and became a document; the source still reports `failed` with 1 recorded retry. |
| Test data | `Idempotency-Key: k-0815` (fresh). |
| Steps | 1. `POST /api/v1/generations/c72e5a90-…/retry` with `k-0815`. |
| Expected result | `201 Created` with `"status":"pending"` and an `id` different from the completed retry's; the completed retry's generation is not returned in its place; the recorded retry count becomes `2`. |
| Status | Not run |

---

## 9. Create Generation — Newly Enforced Idempotency

### TC-12-API-9.1 — A replayed create key returns the existing generation

| Field | Value |
|---|---|
| Description | `POST /generations` already advertised the header without honouring it; a replay must return the first generation rather than buy a second. |
| Preconditions | Account A signed in; no generation exists for key `k-0901`. |
| Test data | Body `{"document_type":"реферат","topic":"Влияние климата на урожай","volume_pages":10}`; `Idempotency-Key: k-0901`. |
| Steps | 1. `POST /api/v1/generations` with that body and key.<br>2. Send the identical request again. |
| Expected result | Step 1 answers `201 Created`; step 2 answers `200 OK` with the same `id`; exactly one `generations` row exists for account A. |
| Status | Not run |

### TC-12-API-9.2 — Pre-existing generations without a key are unaffected

| Field | Value |
|---|---|
| Description | `idempotency_key` is nullable precisely so legacy rows survive; NULLs are distinct in Postgres, so they must neither collide nor be constrained. |
| Preconditions | Account A owns three generations created before enforcement, all with `idempotency_key = NULL`. |
| Test data | New create with `Idempotency-Key: k-0902`. |
| Steps | 1. `POST /api/v1/generations` with `Idempotency-Key: k-0902`.<br>2. `GET /api/v1/generations`.<br>3. `GET /api/v1/projects?limit=100`. |
| Expected result | Step 1 answers `201 Created`; steps 2–3 answer `200 OK` and list all three legacy generations plus the new one; no unique-violation error is raised. |
| Status | Not run |

---

### TC-12-API-9.3 — The create endpoint ignores server-owned fields and does not rebind on replay

| Field | Value |
|---|---|
| Description | Mass assignment on create, and mutation-on-replay, are two ways one request can overwrite what the server owns. |
| Preconditions | Account A signed in; key `k-0903` unused. |
| Test data | Body `{"document_type":"реферат","topic":"Тема A","volume_pages":10,"owner_id":"<account B's id>","id":"11111111-1111-4111-8111-111111111111","status":"completed","created_at":"2000-01-01T00:00:00Z"}`; replay body identical but `"topic":"Тема Б","volume_pages":25`. |
| Steps | 1. `POST /api/v1/generations` with the first body and `Idempotency-Key: k-0903`.<br>2. `POST /api/v1/generations` with the second body and the same key.<br>3. Read the stored row and the enqueued job. |
| Expected result | Step 1 answers `201` with a server-assigned `id` (not `11111111-…`), `"status":"pending"` (not `completed`), `created_at` = now (not `2000-01-01`), and `owner_id` = account A. Step 2 answers `200 OK` describing that same row with `"topic":"Тема A","volume_pages":10`; the stored row and the enqueued job still carry `Тема A` / `10`. |
| Status | Not run |

### TC-12-API-9.4 — The deprecated list endpoints keep their behaviour

| Field | Value |
|---|---|
| Description | Marking a contract `deprecated: true` must not change it; a client on the old endpoints has to keep working through this story's deploy. |
| Preconditions | Account A owns documents and generations with `idempotency_key = NULL`. |
| Test data | `GET /api/v1/documents`, `GET /api/v1/generations`, no new parameters. |
| Steps | 1. `GET /api/v1/documents` with account A's token.<br>2. `GET /api/v1/generations` with account A's token. |
| Expected result | Both answer `200 OK` with their previous response shape field for field (no added required field, no removed one); neither returns `400` for a missing new parameter; the keyless generations are listed. |
| Status | Not run |

---

## 10. Failure Handling & Disclosure

### TC-12-API-10.1 — A query that exceeds the deadline fails generically

| Field | Value |
|---|---|
| Description | The 3 s deadline sits below the gateway read timeout so the client is never told `504` while the scan runs on; the body must carry a handle without carrying internals. |
| Preconditions | Account A owns content large enough that the search scan exceeds 3 s (or the statement timeout is lowered to force it). |
| Test data | `q=климат`; statement deadline 3 s applied with `SET LOCAL`. |
| Steps | 1. `GET /api/v1/projects?q=климат` with account A's token. |
| Expected result | `503 Service Unavailable`; body `{"error_code":"QUERY_TIMEOUT","message":"<generic text>","correlation_id":"<uuid>"}`; the body contains no SQL text, no table or column name, no stack frame and no file path. |
| Status | Not run |

### TC-12-API-10.2 — The deadline does not leak onto the shared connection

| Field | Value |
|---|---|
| Description | A bare `SET statement_timeout` on a pooled connection outlives the request; the next borrower inherits 3 s, and the sweep's contended `UPDATE` is the first thing to start failing. |
| Preconditions | The pool is sized to 1 so the next request provably reuses the same connection. |
| Test data | Feed request first; then a deliberately 8-second write (e.g. the sweep's `UPDATE` under contention). |
| Steps | 1. `GET /api/v1/projects` with account A's token and let it complete.<br>2. On the same pooled connection, run the 8-second write. |
| Expected result | The write completes successfully after ~8 s; it is not cancelled at 3 s and raises no `QueryCanceled`; `SHOW statement_timeout` on that connection outside a transaction is the cluster default, not `3s`. |
| Status | Not run |

### TC-12-API-10.3 — A second concurrent search for one account is shed

| Field | Value |
|---|---|
| Description | The content scan is unindexed; a browser debounce does nothing for a second tab or a scripted client, so the cap has to live in the database. |
| Preconditions | Account A has one search in flight and holding its slot. |
| Test data | `q=климат` twice, overlapping; cap is 1 in-flight searching request per account. |
| Steps | 1. Start `GET /api/v1/projects?q=климат`; do not let it finish.<br>2. Start a second `GET /api/v1/projects?q=климат` with the same token. |
| Expected result | The second answers `429 Too Many Requests` with `{"error_code":"SEARCH_BUSY", …}`; the first still answers `200 OK` with its results and is not cancelled. |
| Status | Not run |

### TC-12-API-10.4 — A shed slot is released on every exit path

| Field | Value |
|---|---|
| Description | A slot released only on the success path means one timed-out search locks the account out of searching until the TTL expires. |
| Preconditions | Account A's previous search ended with `503 QUERY_TIMEOUT`. |
| Test data | `q=климат`; statement deadline 3 s; TTL 10 s (not waited out). |
| Steps | 1. Issue a search that trips the 3 s deadline and returns `503`.<br>2. Immediately issue `GET /api/v1/projects?q=климат` again. |
| Expected result | Step 2 answers `200 OK` (or `503` on its own merits); it is not `429 SEARCH_BUSY`. |
| Status | Not run |

### TC-12-API-10.5 — An abandoned slot is reclaimed

| Field | Value |
|---|---|
| Description | A pod killed mid-scan would otherwise hold the account's only slot forever; the TTL is what makes the cap survive a crash. |
| Preconditions | Account A's slot was claimed by an instance that was killed without releasing it. |
| Test data | Slot TTL 10 s. |
| Steps | 1. Claim the slot and kill the holder.<br>2. Wait 11 s.<br>3. `GET /api/v1/projects?q=климат` with account A's token. |
| Expected result | Step 3 answers `200 OK`; it is not `429 SEARCH_BUSY`. |
| Status | Not run |

### TC-12-API-10.6 — The feed is not stored by shared caches

| Field | Value |
|---|---|
| Description | The body is account-specific; a shared cache holding it would serve one user's projects to another. |
| Preconditions | Account A signed in with projects. |
| Test data | No query parameters. |
| Steps | 1. `GET /api/v1/projects` with account A's token.<br>2. Read the response headers. |
| Expected result | `200 OK` with `Cache-Control: no-store`; the header is not `public`, not `max-age=…` and not absent. |
| Status | Not run |

### TC-12-API-10.7 — A request whose authorization cannot be resolved is denied

| Field | Value |
|---|---|
| Description | Fail closed: an unresolvable owner must never be served as an unscoped feed or an empty-but-`200` one, either of which reads as "you have no projects". |
| Preconditions | Token validation or owner resolution is made to raise (e.g. the key store is unreachable). |
| Test data | A syntactically valid Bearer token; validation forced to fail. |
| Steps | 1. `GET /api/v1/projects` with that token. |
| Expected result | `401 Unauthorized` with the `{error_code, message}` envelope; no `items` array in the body; not `200` with `"items":[]`. |
| Status | Not run |

### TC-12-API-10.8 — The search slot is held for its whole lifetime and no longer

| Field | Value |
|---|---|
| Description | A TTL that expires early re-opens the cap under load; one that never expires locks the account out. The boundary is what pins it. |
| Preconditions | The injected clock is pinned; account A's slot was claimed at `T0` by a holder that stopped without releasing it. |
| Test data | TTL 10 s; probes at `T0+9.9s` and `T0+10.1s`. |
| Steps | 1. At `T0+9.9s`, `GET /api/v1/projects?q=климат`.<br>2. Advance the clock to `T0+10.1s` and repeat. |
| Expected result | Step 1 answers `429` with `{"error_code":"SEARCH_BUSY", …}`; step 2 answers `200 OK`. |
| Status | Not run |

### TC-12-API-10.9 — Two searches claiming the slot at once yield exactly one holder

| Field | Value |
|---|---|
| Description | An in-process check bounds nothing across replicas; the exclusion must be the storage layer's unique constraint or conditional write. |
| Preconditions | Account A holds no slot; two searches are held together at the moment of claiming. |
| Test data | `q=климат` from two instances, released simultaneously. |
| Steps | 1. Release both claims at the same instant.<br>2. Inspect which layer produced the refusal. |
| Expected result | Exactly one answers `200 OK`; the other answers `429 SEARCH_BUSY`; the losing claim was rejected by the database (unique-violation / zero-rows-updated on the conditional write), not by an in-process counter. |
| Status | Not run |

### TC-12-API-10.10 — Repeated failures return every acquired resource to baseline

| Field | Value |
|---|---|
| Description | A leak of one connection or one slot per failure is invisible at ten requests and fatal at ten thousand. |
| Preconditions | Baseline gauges recorded: checked-out pooled connections and outstanding search slots. |
| Test data | 200 iterations each of `400 INVALID_SORT`, `429 SEARCH_BUSY`, `503 QUERY_TIMEOUT`, `404` retry and `409 NOT_RETRYABLE`. |
| Steps | 1. Record both gauges.<br>2. Drive each refusal path 200 times.<br>3. Record both gauges again after the last request settles. |
| Expected result | Both gauges equal their step-1 values; neither shows a monotonic climb across the 1 000 requests. |
| Status | Not run |

### TC-12-API-10.11 — A shed request tells the caller when to retry

| Field | Value |
|---|---|
| Description | A `429` with no hint invites a client to hammer immediately; a hint longer than the TTL leaves the user waiting after the slot is already free. |
| Preconditions | Account A already holds a search slot. |
| Test data | Slot TTL 10 s. |
| Steps | 1. Issue a second concurrent search and read the response headers. |
| Expected result | `429 Too Many Requests` with `{"error_code":"SEARCH_BUSY", …}` and a `Retry-After` header present whose value is an integer between `1` and `10` seconds inclusive. |
| Status | Not run |

### TC-12-API-10.12 — A caller that gives up leaves no scan running

| Field | Value |
|---|---|
| Description | Discarding a response client-side does not cancel the server's scan — a user typing twelve characters would otherwise hold twelve scans and twelve connections. |
| Preconditions | Account A issues a search over large content and disconnects mid-scan. |
| Test data | `q=климат`; disconnect ~500 ms after the request starts. |
| Steps | 1. Start the search and close the client socket.<br>2. Inspect `pg_stat_activity` for that query.<br>3. Inspect the account's search slot immediately. |
| Expected result | The query is gone from `pg_stat_activity` (cancelled) rather than still running to completion; the search slot is released at the moment the disconnect is observed, not only at the 10 s TTL — a new search by that account is accepted at once. |
| Status | Not run |

### TC-12-API-10.13 — The correlation id in the response is the one in the log

| Field | Value |
|---|---|
| Description | The correlation id is the only internal handle in the body; if it does not match the log record, it is decoration and the failure is undiagnosable. |
| Preconditions | A projects request is made to exceed the 3 s statement deadline. |
| Test data | `q=климат`; log capture armed. |
| Steps | 1. Issue the search and record `correlation_id` from the `503` body.<br>2. Search the captured log for that value. |
| Expected result | `503` with `{"error_code":"QUERY_TIMEOUT", …,"correlation_id":"<id>"}`; exactly one log record carries the same `<id>`, and that record carries the underlying failure detail (the driver's cancellation error) which the response body does not. |
| Status | Not run |

### TC-12-API-10.14 — Each degraded path emits a distinguishable signal

| Field | Value |
|---|---|
| Description | One shared "error" counter cannot tell an operator whether the system is shedding load, has lost its database, or cannot enqueue paid work. |
| Preconditions | Metrics capture armed for `search_shed`, `db_unavailable`, `enqueue_failed`. |
| Test data | A shed search (`429 SEARCH_BUSY`), a feed request during database unavailability, a retry whose enqueue raises; then one successful feed request. |
| Steps | 1. Trigger each of the three degraded paths once.<br>2. Read the three counters.<br>3. Issue one successful `GET /api/v1/projects` and read them again. |
| Expected result | Each path increments its own counter by exactly 1, attributed to account A; step 3 leaves all three counters unchanged. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `an authenticated user` | Valid access JWT in the `Authorization: Bearer` header |
| `they request their projects` | `GET /api/v1/projects` |
| `sorted by {key}` | `?sort=created_desc\|created_asc\|updated_desc\|title_asc\|type_asc` |
| `they search for {term}` | `?q={term}` |
| `the retry ceiling` | 5 retries per source generation (`endpoints.md`) |
| `the stale threshold` | `GENERATION_STALE_AFTER_MINUTES`, default 10 |
| `the preview bound` | 200 Unicode code points |
| `the maximum page` | 1000 |
| `they retry it` | `POST /api/v1/generations/{id}/retry` with an `Idempotency-Key` header |
| `refused as a bad request` | 400 with `{error_code, message}` |
| `refused as not found` | 404, byte-identical for absent and foreign |
| `refused as a conflict` | 409 (`NOT_RETRYABLE`, `IDEMPOTENCY_KEY_REUSED`) |
| `refused as too many requests` | 429 (`SEARCH_BUSY`, `RETRY_LIMIT_REACHED`) |
| `refused as unavailable` | 503 `QUERY_TIMEOUT` |
| `forbids shared-cache storage` | `Cache-Control: no-store` |
| `the clock is fixed` | Injected clock pinned to a stated instant; no direct system-time read on the path |
| `the slot's lifetime` | 10 s search-slot TTL |
| `the projects repository` | The `ListProjects` repository port, call-counted |
| `a retry-after hint` | `Retry-After` header on 429 |
| `its own named counter` | A metric named per degraded path (`search_shed`, `db_unavailable`, `enqueue_failed`) |
| `the deprecated documents list` / `generations list` | `GET /api/v1/documents`, `GET /api/v1/generations` |
