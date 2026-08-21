<!-- COPIED FILE. Source of truth: ProductSpecification/stories/12-my-projects/tests/05_Security_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Мои проекты — Security Tests

Attack surface: one owner-scoped read whose filtering, ordering and searching are all
driven by client input, one write that names a resource by id, and user-authored text
rendered into two new surfaces. Generic 401 handling, security headers, CORS and HTTPS are
cross-cutting and tested globally — not here.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.projects@textery.test` / `Qa!Projects2026`, owner id `11f8c3a5-6d20-4e97-8b41-0c7a25e93d68` |
| Account B (the victim) | `qa.stranger@textery.test` / `Qa!Stranger2026`, owner id `93ad7e04-2c58-4b16-9f83-6d41e0b7c295` |
| Account B's data | 40 projects, including document `Крыжовниковый синтез` and failed generation `6d21b8f4-0c93-4e57-a1d8-5b7e2f460a39` |
| Account A's failed generation | `c72e5a90-3b14-4d6f-9e88-01af4c2d7b65`, `status=failed`, `retryable=true` |
| Account A's document | `3f8b1c07-5a2d-4e91-b6c4-9d0e7a1f2b53`, title `Отчёт по практике` |
| Error body shape | `{"error_code": "<CODE>", "message": "<generic text>"}`; `correlation_id` added on 5xx only |
| Bounds in force | `q` ≤ 200 code points, retry ceiling 5 per source, search cap 1 in-flight per account (`429 SEARCH_BUSY`, `Retry-After` ≤ 10 s), statement deadline 3 s |
| Sentinel value | `ZZQA-SENTINEL-7f31` — planted in the token, the idempotency key, the query, and a document's title and body |

---

## 1. Owner Scoping

### TC-12-SEC-1.1 — No parameter combination reveals another account's rows

| Field | Value |
|---|---|
| Description | `owner_id` is a query predicate, never a parameter — but a filter, a sort or a deep offset is where a missing predicate usually surfaces, not on the default request. |
| Preconditions | Account B owns its 40 projects including `Крыжовниковый синтез`; account A owns 6 of its own. |
| Test data | Each of `sort=created_desc|created_asc|updated_desc|title_asc|type_asc`; `page=1..5`, `limit=100`; `q=Крыжовниковый`. |
| Steps | 1. For each of the 5 sort values, walk pages 1–5 at `limit=100` with account A's token.<br>2. Repeat the walk with `q=Крыжовниковый`.<br>3. Collect every returned `(kind,id)`. |
| Expected result | Every response is `200 OK`; no returned id belongs to account B — in particular `Крыжовниковый синтез` and `6d21b8f4-…` never appear; the `q=Крыжовниковый` walk returns `{"items":[],"total":0}`. |
| Status | Not run |

### TC-12-SEC-1.2 — The reported total counts only the caller's rows

| Field | Value |
|---|---|
| Description | A `total` computed without the owner predicate leaks the size of another account's library even when `items` is correctly scoped. |
| Preconditions | Account B owns 40 projects; account A owns 6. |
| Test data | `GET /api/v1/projects?limit=100` with account A's token. |
| Steps | 1. `GET /api/v1/projects?limit=100` with account A's token.<br>2. Read `total` and the length of `items`. |
| Expected result | `200 OK`; `"total":6` — not `46` and not `40`; `items` holds exactly 6 entries, all owned by account A. |
| Status | Not run |

### TC-12-SEC-1.3 — An owner supplied by the client is ignored

| Field | Value |
|---|---|
| Description | The owner comes from the token and nowhere else; honouring a client-supplied identity in any of the three transports is a one-parameter account takeover of the read path. |
| Preconditions | Account A signed in with 6 projects; account B owns 40. |
| Test data | `?owner_id=93ad7e04-2c58-4b16-9f83-6d41e0b7c295`; the same as a JSON body field; header `X-Owner-Id: 93ad7e04-…`. |
| Steps | 1. `GET /api/v1/projects?owner_id=93ad7e04-…` with account A's token.<br>2. Repeat sending `{"owner_id":"93ad7e04-…"}` as the request body.<br>3. Repeat with the `X-Owner-Id` header. |
| Expected result | All three answer `200 OK` with account A's own 6 items and `"total":6`; none returns any of account B's rows; the supplied identity changes nothing — the three responses are equivalent to the plain request. |
| Status | Not run |

---

## 2. Injection

### TC-12-SEC-2.1 — Search input reaching the query cannot alter it

| Field | Value |
|---|---|
| Description | `q` is concatenated into an `ILIKE` pattern; if it is interpolated rather than bound, a quote ends the literal and the rest of the term becomes SQL. |
| Preconditions | Account A owns 6 projects, one titled `Отчёт по практике`. |
| Test data | `q=' OR 1=1 --`, `q=%'; DROP TABLE documents; --`, `q=" UNION SELECT null,null --`, `q=Отчёт'`. |
| Steps | 1. Issue `GET /api/v1/projects?q=…` for each of the four payloads with account A's token.<br>2. After all four, `GET /api/v1/projects?limit=100` and count the rows. |
| Expected result | Each answers `200 OK` returning only items whose text literally contains the payload — in practice `{"items":[],"total":0}` — and never account A's whole feed via `OR 1=1`; no response body contains SQL text, a table name, a column name or a driver error; step 2 still returns all 6 projects, so nothing was dropped or altered. |
| Status | Not run |

### TC-12-SEC-2.2 — Wildcards cannot widen the search

| Field | Value |
|---|---|
| Description | `%`, `_` and the escape character are pattern operators; unescaped, a one-character query returns the caller's entire feed and the search silently stops filtering. |
| Preconditions | Account A owns document `Скидка 50% на подписку`, document `Файл_отчёт`, document `C:\путь` and 3 documents containing none of those characters. |
| Test data | `q=%`, `q=_`, `q=\`, `q=%_\`. |
| Steps | 1. `GET /api/v1/projects?q=%25`.<br>2. Repeat with `_`, `\` and `%_\`. |
| Expected result | Each answers `200 OK` returning only the documents whose text literally contains those characters — `q=%` returns just `Скидка 50% на подписку`, `q=_` just `Файл_отчёт`, `q=\` just `C:\путь`, `q=%_\` returns `{"items":[],"total":0}`; no query returns all 6 projects. |
| Status | Not run |

### TC-12-SEC-2.3 — A sort value cannot reach the query as a column name

| Field | Value |
|---|---|
| Description | `sort` maps through a server-side allowlist to a column; anything that reaches `ORDER BY` as text is injection into a place bound parameters cannot protect. |
| Preconditions | Account A signed in with projects. |
| Test data | `sort=documents.owner_id`, `sort=title_asc; DROP TABLE generations`, `sort=(SELECT password_hash FROM users)`. |
| Steps | 1. `GET /api/v1/projects?sort=documents.owner_id`.<br>2. Repeat with each of the other two payloads. |
| Expected result | Each answers `400 Bad Request` with `{"error_code":"INVALID_SORT","message":"<generic text>"}`; no `items` array is returned and no ordering derived from the payload is applied; the message names no database column and no table. |
| Status | Not run |

---

## 3. Stored Cross-Site Scripting and Output Encoding

### TC-12-SEC-3.1 — Markup stored in any echoed field is neutralized

| Field | Value |
|---|---|
| Description | Three echoed fields, one rule — sanitizing the preview but not the title is the half-fix that still ships stored XSS onto the feed. |
| Preconditions | Account A owns a document titled `<script>alert(1)</script>`, a document whose body is `<img src=x onerror=alert(1)>Текст`, and a generation whose topic is `<svg onload=alert(1)>`. |
| Test data | The three payloads above; dialog listener armed in the browser. |
| Steps | 1. `GET /api/v1/projects?limit=20` and read the raw JSON for `title` and `preview`.<br>2. Render `/projects` in grid view.<br>3. Switch to list view. |
| Expected result | `200 OK`; none of `<script`, `onerror=`, `<svg` or `onload=` appears as live markup in the returned strings (stripped or escaped); in both views the payloads render as visible text, no `<script>`/`<img>`/`<svg>` node is created from them, and no dialog fires. |
| Status | Not run |

### TC-12-SEC-3.2 — A preview cut from stored markup cannot reopen a tag

| Field | Value |
|---|---|
| Description | Truncating sanitized HTML at 200 code points can end mid-tag and leave an unbalanced element that swallows the rest of the card; deriving the preview as plain text removes the class of bug entirely. |
| Preconditions | Account A owns a document whose stored content places `<a href="http://evil.example/…` astride code point 200. |
| Test data | Content constructed so the 200-code-point cut falls inside a tag. |
| Steps | 1. `GET /api/v1/projects?limit=20` with account A's token.<br>2. Inspect that item's `preview`. |
| Expected result | `200 OK`; `preview` contains no `<`, no `>` and no attribute fragment — it is plain text only; its length is ≤ 200 code points; rendering it creates no element. |
| Status | Not run |

### TC-12-SEC-3.3 — The echoed search query renders as text

| Field | Value |
|---|---|
| Description | The query is echoed into the results header, the empty state and the input; reflected XSS here needs only a crafted link. |
| Preconditions | Account A on `/projects`; no project matches the payload. |
| Test data | `q=<img src=x onerror=alert(1)>`; dialog listener armed. |
| Steps | 1. Search for the payload through the UI.<br>2. Inspect `[data-testid='projects-empty-search']` and the search input. |
| Expected result | The payload is shown as literal text inside «Ничего не найдено.» and as the input's value; no `<img>` node is created from it and no dialog fires. |
| Status | Not run |

---

## 4. Broken Object-Level Authorization

### TC-12-SEC-4.1 — Retrying another account's generation is refused indistinguishably

| Field | Value |
|---|---|
| Description | A `403` on a foreign id confirms the id exists, turning the retry endpoint into an id oracle; the two refusals must be byte-identical. |
| Preconditions | Account B owns failed generation `6d21b8f4-0c93-4e57-a1d8-5b7e2f460a39`; no generation has id `00000000-0000-4000-8000-000000000000`. |
| Test data | Both ids; fresh `Idempotency-Key` per call. |
| Steps | 1. `POST /api/v1/generations/6d21b8f4-…/retry` with account A's token and `Idempotency-Key: k-sec41a`.<br>2. `POST /api/v1/generations/00000000-0000-4000-8000-000000000000/retry` with `k-sec41b`.<br>3. Compare status line, headers and body bytes. |
| Expected result | Both answer `404 Not Found` with identical `{error_code, message}` bodies and identical headers bar `Date`; neither is `403`; the `generations` row count is unchanged for account A and for account B. |
| Status | Not run |

### TC-12-SEC-4.2 — An idempotency key cannot reach another account's record

| Field | Value |
|---|---|
| Description | Keying the replay on the header alone short-circuits before ownership is checked, and a colliding key returns another account's generation. |
| Preconditions | Account B has retried its own failed generation with `Idempotency-Key: k-shared-9`; account A owns `c72e5a90-…` and has used no key. |
| Test data | `Idempotency-Key: k-shared-9` reused by account A. |
| Steps | 1. `POST /api/v1/generations/c72e5a90-…/retry` with account A's token and `Idempotency-Key: k-shared-9`.<br>2. Compare the returned `id` with account B's retry generation. |
| Expected result | `201 Created` with a new generation owned by account A; its `id` differs from the generation account B's retry created; no field of account B's row (id, topic, timestamps) appears in the body. |
| Status | Not run |

---

## 5. Mass Assignment

### TC-12-SEC-5.1 — The retry cannot set server-owned fields

| Field | Value |
|---|---|
| Description | The endpoint takes no body precisely so there is no field to over-bind; a request that carries one must be ignored rather than allowlisted. |
| Preconditions | Account A owns `c72e5a90-…`, `status=failed`, `document_type=реферат`, `topic=Влияние климата на урожай`, `volume_pages=10`. |
| Test data | Body `{"owner_id":"93ad7e04-…","status":"completed","id":"11111111-1111-4111-8111-111111111111","created_at":"2000-01-01T00:00:00Z"}`; `Idempotency-Key: k-sec51`. |
| Steps | 1. `POST /api/v1/generations/c72e5a90-…/retry` with account A's token, that key and that body.<br>2. Read the created row. |
| Expected result | `201 Created`; the new row's owner is account A (`11f8c3a5-…`), not `93ad7e04-…`; `"status":"pending"` not `completed`; the `id` is server-assigned and is not `11111111-…`; `created_at` is the current instant, not `2000-01-01T00:00:00Z`. |
| Status | Not run |

### TC-12-SEC-5.2 — Server-owned list fields cannot be supplied by the caller

| Field | Value |
|---|---|
| Description | `preview`, `kind` and the owner are derived, not accepted; a client that could set `kind` could make a generation card open as a document. |
| Preconditions | Account A owns document `3f8b1c07-…` with a real stored body. |
| Test data | `?preview=ВЗЛОМ&kind=generation&owner_id=93ad7e04-…`, and the same three as body fields. |
| Steps | 1. `GET /api/v1/projects?preview=ВЗЛОМ&kind=generation&owner_id=93ad7e04-…` with account A's token.<br>2. Repeat sending the three as a JSON body. |
| Expected result | Both answer `200 OK` with account A's own feed; `3f8b1c07-…` is returned with `"kind":"document"` and a `preview` derived from its stored content; the string `ВЗЛОМ` appears in no field; no item belongs to `93ad7e04-…`. |
| Status | Not run |

---

## 6. Abuse Limits

### TC-12-SEC-6.1 — One source generation cannot be retried without bound

| Field | Value |
|---|---|
| Description | The fresh-key rule that keeps the button alive after a second failure also means idempotency bounds nothing; the ceiling is the only limit on the one endpoint that spends money. |
| Preconditions | Account A owns `c72e5a90-…`, `status=failed`, with 0 recorded retries; ceiling 5. |
| Test data | 7 retries with distinct fresh keys `k-sec61-1` … `k-sec61-7`. |
| Steps | 1. Issue the 7 retries in sequence.<br>2. Count the `generations` rows created for that source. |
| Expected result | The first 5 answer `201 Created`; the 6th and 7th answer `429 Too Many Requests` with `{"error_code":"RETRY_LIMIT_REACHED", …}`; exactly 5 new generation rows exist; the feed reports the source with `"retryable":false`. |
| Status | Not run |

### TC-12-SEC-6.2 — Search cannot be used to occupy the database

| Field | Value |
|---|---|
| Description | The content scan is unindexed; one scripted account holding several of them at once is a denial of service against every other account on the same pool. |
| Preconditions | Account A owns large content; account B is issuing normal feed requests throughout. |
| Test data | 10 concurrent `GET /api/v1/projects?q=климат` from account A; cap 1 in-flight per account; deadline 3 s. |
| Steps | 1. Fire the 10 concurrent searches as account A.<br>2. Record each response and its duration.<br>3. Issue account B's feed requests during the burst. |
| Expected result | At most 1 search is accepted at a time; the excess answer `429` with `{"error_code":"SEARCH_BUSY", …}` and `Retry-After` ≤ 10 s; every accepted request returns `200` or `503 QUERY_TIMEOUT` within 3 s; account B's requests all answer `200 OK` and are never shed. |
| Status | Not run |

---

## 7. Information Disclosure

### TC-12-SEC-7.1 — Failures expose nothing internal

| Field | Value |
|---|---|
| Description | The correlation id is the only internal handle the body may carry; a driver message or a query fragment hands an attacker the schema. |
| Preconditions | The projects query is made to fail at the database (statement deadline tripped). |
| Test data | `q=климат`; deadline 3 s. |
| Steps | 1. `GET /api/v1/projects?q=климат` with account A's token.<br>2. Read the full response body. |
| Expected result | `503` with exactly `{"error_code":"QUERY_TIMEOUT","message":"<generic text>","correlation_id":"<uuid>"}` and no other key; the body contains no SQL text, no `documents`/`generations` table name, no column name, no stack frame and no file path. |
| Status | Not run |

### TC-12-SEC-7.2 — Credentials, keys and user text never reach the log

| Field | Value |
|---|---|
| Description | Failure paths are where whole request objects get logged; a token or a user's document body in the log is a breach that outlives the incident. |
| Preconditions | Log capture armed; the deadline path and the database-unavailable path are both reproducible. |
| Test data | Sentinel `ZZQA-SENTINEL-7f31` planted in the bearer token, the `Idempotency-Key`, `q`, and a document's title and body. |
| Steps | 1. Trigger the statement-deadline failure with the sentinel-bearing request.<br>2. Stop the database and repeat the request.<br>3. Search both response bodies and the captured log for `ZZQA-SENTINEL-7f31`. |
| Expected result | Zero occurrences of `ZZQA-SENTINEL-7f31` in either response body and zero in the captured log; each redacted field appears in the log as a fixed redaction token (e.g. `***`) alongside the request's `correlation_id`. |
| Status | Not run |

### TC-12-SEC-7.3 — An unmapped failure returns the sanctioned envelope

| Field | Value |
|---|---|
| Description | The default handler is what an unforeseen exception meets; if it is the framework's, the response ships a traceback. |
| Preconditions | An unmapped exception (e.g. `TypeError`) is raised while the feed is built. |
| Test data | Fault injected in the feed assembly path. |
| Steps | 1. `GET /api/v1/projects` with account A's token against the fault.<br>2. Read the full body. |
| Expected result | `500` with `{"error_code":"<CODE>","message":"<generic text>","correlation_id":"<uuid>"}` and no other key; the body contains no traceback, no `TypeError`, no `select`/`sqlalchemy`/`asyncpg` keyword, no internal class name and no file path. |
| Status | Not run |

---

## 8. Server-Derived Fields

### TC-12-SEC-8.1 — A client-supplied preview is ignored

| Field | Value |
|---|---|
| Description | `preview` is read as a bounded SQL prefix of stored content; accepting one from the client would let a user put arbitrary text on their own card and, worse, make the field a rendering surface the server never sanitized. |
| Preconditions | Account A owns 6 documents with real stored bodies. |
| Test data | `?preview=<script>alert(1)</script>` and `?preview=ПОДДЕЛКА`. |
| Steps | 1. `GET /api/v1/projects?preview=ПОДДЕЛКА&limit=20` with account A's token.<br>2. Repeat with the script payload.<br>3. Inspect every returned `preview`. |
| Expected result | Both answer `200 OK`; every `preview` is a prefix of that item's own stored content, ≤ 200 code points; neither `ПОДДЕЛКА` nor `<script>` appears in any `preview` or any other field. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `supplying another account's owner identity` | `?owner_id=…` as query param, body field, and `X-Owner-Id` header — must be ignored, not honoured |
| `refused as a bad request` | 400 `INVALID_SORT` with `{error_code, message}` |
| `refused as too many requests` | 429 `SEARCH_BUSY` / `RETRY_LIMIT_REACHED` |
| `byte-identical` | Same status, headers and body bytes for absent and foreign (404) |
| `pattern metacharacters` | `%`, `_`, and the `ESCAPE` character |
| `no script executes` | Rendered as escaped text; no dialog, no injected node |
| `a sentinel value` | A marker string planted in the DB error path and in document content |
| `a fixed redaction marker` | Fixed redaction token plus a correlation id |
| `the statement deadline` | 3 s, `SET LOCAL` per request |
| `the ceiling` | 5 retries per source generation |
