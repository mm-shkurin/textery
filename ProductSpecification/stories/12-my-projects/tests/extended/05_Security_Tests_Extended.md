> These are additional edge case tests. Implement after core tests pass.

# Мои проекты — Security Tests (Extended)

Shared test data is inherited from `05_Security_Tests.md`: account A `qa.projects@textery.test`
(owner id `11f8c3a5-6d20-4e97-8b41-0c7a25e93d68`), account B `qa.stranger@textery.test`
(owner id `93ad7e04-2c58-4b16-9f83-6d41e0b7c295`) with 40 projects and failed generation
`6d21b8f4-0c93-4e57-a1d8-5b7e2f460a39`, error body `{"error_code","message"}` (plus
`correlation_id` on 5xx), `q` ≤ 200 code points, retry ceiling 5.

---

## 1. Credentials

### TC-12-SEC-EXT-1.1 — A token for a deleted or disabled account cannot read the feed

| Field | Value |
|---|---|
| Description | A still-valid signature is not a still-valid account; resolving the owner from the claim alone serves a deleted user's feed until the token expires. |
| Preconditions | Account `qa.gone@textery.test` was issued an access token and then deleted; the token has not yet expired. |
| Test data | The unexpired access token of the deleted account. |
| Steps | 1. `GET /api/v1/projects` with that token. |
| Expected result | `401 Unauthorized` with the `{error_code, message}` envelope; no `items` array in the body; not `200` with `"items":[]` and not `500`. |
| Status | Not run |

### TC-12-SEC-EXT-1.2 — A refresh token presented as an access token is refused

| Field | Value |
|---|---|
| Description | Both tokens are signed by the same key; without a token-type check a long-lived refresh token becomes a long-lived API credential. |
| Preconditions | Account A holds a valid refresh token from `POST /api/v1/auth/login`. |
| Test data | `Authorization: Bearer <account A's refresh token>`. |
| Steps | 1. `GET /api/v1/projects` with the refresh token as the bearer credential. |
| Expected result | `401 Unauthorized` with the `{error_code, message}` envelope; no feed is returned; the response does not distinguish "wrong token type" in a way that aids an attacker beyond the generic refusal. |
| Status | Not run |

---

## 2. Input Handling

### TC-12-SEC-EXT-2.1 — Control characters in a query cannot forge a log line

| Field | Value |
|---|---|
| Description | A newline in a value that reaches a line-oriented log lets a user write a second, fake record — enough to hide a real one from an operator grepping the log. |
| Preconditions | Log capture armed for the request. |
| Test data | `q=отчёт%0D%0Alevel%3DERROR%20msg%3D%22forged%22` (CR+LF then a forged record prefix). |
| Steps | 1. `GET /api/v1/projects?q=…` with that payload and account A's token.<br>2. Read every log record emitted for that request. |
| Expected result | Exactly one structured record is emitted for the request; the term appears inside a single field with `\r\n` escaped; no standalone line parses as a second record and no record carries `level=ERROR` with `msg=forged`. |
| Status | Not run |

### TC-12-SEC-EXT-2.2 — An oversized query is rejected before any search runs

| Field | Value |
|---|---|
| Description | Validating after the scan means the attacker still gets the expensive unindexed work for free — the refusal has to come before the database is touched. |
| Preconditions | Account A signed in; database query counter/log armed. |
| Test data | `q` = 10 000 Cyrillic characters (bound is 200 code points). |
| Steps | 1. Reset the database query counter.<br>2. `GET /api/v1/projects?q=<я×10000>` with account A's token.<br>3. Read the counter and the query log. |
| Expected result | `400 Bad Request` with `{"error_code":"INVALID_QUERY", …}`; zero search queries were issued against `documents` or `generations` for that request. |
| Status | Not run |

### TC-12-SEC-EXT-2.3 — Error responses for refused sorts do not enumerate internal column names

| Field | Value |
|---|---|
| Description | An error listing the allowed columns hands an attacker the schema for free, and turns a validation message into reconnaissance. |
| Preconditions | Account A signed in. |
| Test data | `sort=owner_id`, `sort=documents.title`. |
| Steps | 1. `GET /api/v1/projects?sort=owner_id` with account A's token.<br>2. Repeat with `sort=documents.title`.<br>3. Read both message strings. |
| Expected result | Both answer `400` with `{"error_code":"INVALID_SORT","message":"<generic text>"}`; the message names the `sort` parameter but contains no column name (`owner_id`, `title`, `created_at`, `document_type`) and no table name (`documents`, `generations`). |
| Status | Not run |

---

## 3. Enumeration

### TC-12-SEC-EXT-3.1 — Paging parameters cannot be used to infer another account's row count

| Field | Value |
|---|---|
| Description | If `total` or the point at which pages go empty reflects the whole table rather than the caller's rows, paging becomes a side channel for another account's library size. |
| Preconditions | Account A owns 6 projects; account B owns 40. |
| Test data | `page=1..20` at `limit=20` with account A's token. |
| Steps | 1. Walk pages 1 through 20 at `limit=20` as account A.<br>2. Read `items` and `total` on every page.<br>3. Compare the responses for pages 2..20. |
| Expected result | Page 1 returns account A's 6 items; pages 2–20 all return `"items":[]`; every page reports `"total":6`, never `46` or `40`; the responses for pages 2–20 are indistinguishable from one another, so nothing indicates where another account's rows would have been. |
| Status | Not run |

### TC-12-SEC-EXT-3.2 — Retry timing does not distinguish absent from foreign

| Field | Value |
|---|---|
| Description | Byte-identical bodies are undone by a timing gap: a foreign id that costs an extra ownership lookup is still an id oracle, just a slower one. |
| Preconditions | Account B owns failed generation `6d21b8f4-…`; no generation has id `00000000-0000-4000-8000-000000000000`. |
| Test data | 200 retries against each id, distinct fresh keys, timings recorded. |
| Steps | 1. Issue 200 retries against the foreign id and record the durations.<br>2. Issue 200 against the absent id and record the durations.<br>3. Compare the two distributions and the response bytes. |
| Expected result | All 400 answer `404` with identical `{error_code, message}` bodies and identical headers bar `Date`; the two median durations differ by no more than the measurement noise of repeated identical requests — no systematic gap separates foreign from absent. |
| Status | Not run |

### TC-12-SEC-EXT-3.3 — Retry cannot be aimed at a document id

| Field | Value |
|---|---|
| Description | `documents` and `generations` are separate id spaces; if the retry lookup is not scoped to `generations`, a document id becomes a probe that answers differently from an unused one. |
| Preconditions | Account A owns document `3f8b1c07-5a2d-4e91-b6c4-9d0e7a1f2b53`; no generation carries that id. |
| Test data | Document id above; unused id `00000000-0000-4000-8000-000000000000`; fresh keys. |
| Steps | 1. `POST /api/v1/generations/3f8b1c07-…/retry` with account A's token and `Idempotency-Key: k-ext331`.<br>2. `POST /api/v1/generations/00000000-…/retry` with `k-ext332`.<br>3. Compare the two responses. |
| Expected result | Both answer `404 Not Found` with identical bodies and headers bar `Date`; neither is `409`, `422` or `500`; the document is not touched and no generation is created. |
| Status | Not run |

### TC-12-SEC-EXT-3.4 — An idempotency key is not echoed back to a caller that did not send it

| Field | Value |
|---|---|
| Description | Keys are chosen by clients and can carry meaning; echoing any stored key into a response body would leak another account's — and would make key guessing verifiable. |
| Preconditions | Account A and account B each have stored retry records with keys `k-A-secret` and `k-B-secret`. |
| Test data | `GET /api/v1/projects?limit=100`; a `201` retry; a replayed `200`; a `409 IDEMPOTENCY_KEY_REUSED`. |
| Steps | 1. Issue each of the four requests above as account A.<br>2. Search every response body for `k-A-secret` and `k-B-secret`. |
| Expected result | No response body contains `k-B-secret`; no feed or retry response body carries an `idempotency_key` field at all — the key is never part of the returned representation. |
| Status | Not run |

---

## 4. Rendering

### TC-12-SEC-EXT-4.1 — A title carrying right-to-left overrides cannot reorder the card

| Field | Value |
|---|---|
| Description | An unterminated `U+202E` re-orders everything after it in the same text run, so a crafted title can visually rewrite the labels and the date around it. |
| Preconditions | Account A owns a document whose title is `Отчёт‮серетни` (an RLO with no matching PDF). |
| Test data | Title containing `U+202E`; card labels «Реферат» and the date `18.08.2026`. |
| Steps | 1. Open `/projects` through the navigation.<br>2. Read the rendered `project-card-type`, `project-card-title` and `project-card-date` of that card and of a neighbouring card. |
| Expected result | The card's own labels stay in place: `project-card-type` still reads «Реферат» and `project-card-date` still reads `18.08.2026`, both in their normal order; the override's effect is confined to the title element and does not reach the neighbouring card. |
| Status | Not run |

---

## DSL Technical Reference

Inherits `05_Security_Tests.md`.
