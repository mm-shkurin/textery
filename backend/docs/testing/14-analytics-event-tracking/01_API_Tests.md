<!-- COPIED FILE. Source of truth: ProductSpecification/stories/14-analytics-event-tracking/tests/01_API_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> **Implementation Order**: sequential TDD — ingest guards → ingest happy path → re-run
> safety on the ingest key → registration context → the server-side emitters, each bound to
> its transition → ordering → deletion → isolation of the analytics path from the product.

# Analytics Event Tracking — API Tests

Endpoints: `POST /api/v1/analytics/events` (new), `POST /api/v1/auth/register` and
`GET /api/v1/auth/oauth/{provider}/start` (both extended). Contracts: `endpoints.md`,
`api-specs/analytics_events_create.yaml`, `api-specs/auth_register.yaml`,
`api-specs/oauth_start.yaml`.

> **Persistence assertions re-read in a separate session.** `create_session_factory` sets
> `expire_on_commit=False`, so a same-session re-read is served from the identity map and
> passes on a row Postgres never received. Wherever a case says «a fresh read», that is
> the requirement, not a phrasing choice.

> **A refusal is only ever an option on the new endpoint.** `POST /api/v1/analytics/events` is
> this story's own route and may refuse whatever it must. `POST /auth/register` and
> `GET /auth/oauth/{provider}/start` are existing routes that Story 14 only rides along on:
> no case in this file may require them to answer a status code or an `error_code` they do
> not answer today. Where analytics input is unusable there, the assertion is on what was
> **stored**, never on what was **answered** — the Governing Decision in
> `14_AnalyticsEventTracking.md`, agreed 2026-08-19.

> **«An event is recorded» never means «the call answered 200».** Every emitter in this story
> hangs off a path that returns success without writing. Cases below assert the stored
> row, never the response code, unless the response is what is under test.

> **Single-process green is not green.** The backend runs as multiple instances
> (`.claude/rules/coding-rules.md`). Every dedupe, rate-limit and handshake case below
> that says «another instance» means exactly that: a second session/process sharing only the
> database. A per-process dictionary satisfies the single-instance phrasing and fails in
> production.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Events endpoint | `POST /api/v1/analytics/events` |
| Register endpoint | `POST /api/v1/auth/register` |
| Handshake endpoint | `GET /api/v1/auth/oauth/yandex/start` |
| Event body | `{"event_name": …, "visitor_id": …, "occurrence_key": …, "payload": {}, "degraded": false}` |
| Browser-origin event names | `SITE_VISITED`, `REGISTRATION_STARTED`, `EDITOR_OPENED` |
| Server-only / subscription names (refused from a client) | `REGISTRATION_COMPLETED`, `LOGIN_SUCCESS`, `GENERATION_STARTED`, `GENERATION_COMPLETED`, `DOCUMENT_SAVED`, `SUBSCRIPTION_ACTIVATED` (and the rest of the twelve-name catalogue) |
| Visitor V1 | `7b1f2c40-6d83-4a19-9e52-0c4a7d18b3f6` |
| Visitor V2 | `2e94a06d-51b7-4c38-8fa1-6d0b93c27e45` |
| Occurrence key K1 | `c0d51e73-84b2-4f16-9a07-3e5b18d6c294` |
| Occurrence key K2 | `48f7a3b1-2c69-4d05-8e73-1b906fa2c5d8` |
| Account A (the caller) | `qa.analytics@textery.test` / `Qa!Analytics2026` |
| Account B (a stranger) | `qa.stranger@textery.test` / `Qa!Stranger2026`, id `9f3c1a58-7e04-4b62-8d19-5a2f07c3b6e1` |
| Access token | `Authorization: Bearer <access token of account A>` |
| Error body shape | `{"error_code": "<CODE>", "message": "<generic text>"}`; `correlation_id` added on 5xx only; the value that was rejected is never echoed |
| `error_code` set on the events route | `UNKNOWN_EVENT_NAME`, `INVALID_VISITOR_ID`, `INVALID_OCCURRENCE_KEY`, `INVALID_PAYLOAD` (400); `UNAUTHORIZED` (401); `OCCURRENCE_KEY_CONFLICT` (409); `REQUEST_BODY_TOO_LARGE` (413); `RATE_LIMITED` (429) |
| Unauthorized body | `{"error_code": "UNAUTHORIZED", "message": "A valid access token is required."}` |
| Bounds in force | `payload` serialized ≤ 4096 bytes; `payload` depth ≤ 8 levels; `payload` keys ≤ 64; request body ≤ 16384 bytes measured on bytes actually read; each `utm_*` ≤ 200 code points after NFC; rate limit 120 requests per 60 s per bucket; `GEOLOCATION_TIMEOUT_SECONDS=1.5`; `TRUSTED_PROXY_HOPS=1` |
| Attribution set | `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term` — stored as one set or not at all |
| Frozen attribution fixture | `utm_source=vk`, `utm_medium=cpc`, `utm_campaign=spring2026`, `utm_content=banner_a`, `utm_term=диплом` |
| Account context columns | `accounts.registration_ip`, `registration_country`, `device_type`, `operating_system`, `device_language` plus the five `utm_*` — ten nullable `text` columns added by migration `d6e7f8a9b0c1`, all server-derived, never read from a request body |
| Event table | `analytics_events` — `id`, `visitor_id` (`uuid`, nullable), `user_id` (FK `accounts.id`, `ON DELETE SET NULL`), `event_name`, `event_time` (timezone-aware), `sequence`, `payload` (`NOT NULL` default `{}`), occurrence key |

---

## 1. Ingest Guards — Identity

### TC-14-API-1.1 — An event with no token is recorded as anonymous

| Field | Value |
|---|---|
| Description | `SITE_VISITED` happens before an account exists. If the route required a token the product's top-of-funnel event could never be reported at all. |
| Preconditions | Database reachable; no rows in `analytics_events` for visitor V1. |
| Test data | As shared. No `Authorization` header. Body `{"event_name":"SITE_VISITED","visitor_id":"7b1f2c40-6d83-4a19-9e52-0c4a7d18b3f6","occurrence_key":"c0d51e73-84b2-4f16-9a07-3e5b18d6c294"}`. |
| Steps | 1. `POST /api/v1/analytics/events` with the body above and no `Authorization` header.<br>2. Read the response status.<br>3. In a fresh session, select the `analytics_events` rows for visitor V1. |
| Expected result | `204 No Content` with an empty body; exactly one row exists for V1; its `event_name` is `SITE_VISITED`, its `user_id` **IS NULL**, and its `payload` is `{}`. |
| Status | Not run |

### TC-14-API-1.2 — An event from a signed-in caller is attributed to that account

| Field | Value |
|---|---|
| Description | The join between the anonymous and the signed-in halves of the funnel is made here; an ignored token makes every conversion measurement unanswerable. |
| Preconditions | Account A registered and verified, holding a live access token. |
| Test data | As shared; `Authorization: Bearer <access token of account A>`; `event_name` `EDITOR_OPENED`, `visitor_id` V1, `occurrence_key` K1. |
| Steps | 1. Sign in as account A and obtain an access token.<br>2. `POST /api/v1/analytics/events` with that token and the body above.<br>3. In a fresh session, select the `analytics_events` row for occurrence key K1. |
| Expected result | `204 No Content`; the stored row's `user_id` equals account A's id; its `visitor_id` equals `7b1f2c40-6d83-4a19-9e52-0c4a7d18b3f6` exactly as sent; its `event_name` is `EDITOR_OPENED`. |
| Status | Not run |

### TC-14-API-1.3 — A present but unusable token is refused, never downgraded to anonymous

| Field | Value |
|---|---|
| Description | Silently downgrading a bad token to anonymous hides an expired session behind a `204` and writes an unattributed row where an attributed one belonged. All three token kinds are one case because one code path decides all three. |
| Preconditions | Account A exists. An expired access token, a valid refresh token and a structurally invalid string are prepared. |
| Test data | (a) expired access token; (b) a refresh token used in the `Authorization` header; (c) `Authorization: Bearer not.a.token`. Body: `SITE_VISITED`, visitor V1, occurrence keys K1 / K2 / `f31c8e02-4a76-4d59-b8e0-27c591a4f036`. |
| Steps | 1. `POST` the event carrying the expired access token.<br>2. `POST` the event carrying the refresh token.<br>3. `POST` the event carrying `Bearer not.a.token`.<br>4. Read all three response statuses and bodies.<br>5. In a fresh session, count `analytics_events` rows for visitor V1. |
| Expected result | All three answer `401` with `{"error_code": "UNAUTHORIZED", "message": "A valid access token is required."}`; none answers `204`; the row count for V1 is `0` — in particular no row was written with `user_id IS NULL`. |
| Status | Not run |

---

## 2. Ingest Guards — What May Be Reported

### TC-14-API-2.1 — Only browser-origin event names are accepted

| Field | Value |
|---|---|
| Description | The three names a browser legitimately produces must all be reachable; a route that accepts only the one the first test used ships two dead emitters. |
| Preconditions | No rows for visitor V1. |
| Test data | Three requests, `event_name` `SITE_VISITED`, `REGISTRATION_STARTED`, `EDITOR_OPENED`; visitor V1; a distinct `occurrence_key` per request. |
| Steps | 1. `POST` the `SITE_VISITED` event with no token.<br>2. `POST` the `REGISTRATION_STARTED` event with a fresh occurrence key.<br>3. `POST` the `EDITOR_OPENED` event with a fresh occurrence key.<br>4. In a fresh session, read the `event_name` values stored for V1. |
| Expected result | Each request answers `204`; three rows exist for V1; their `event_name` values are exactly the set `{SITE_VISITED, REGISTRATION_STARTED, EDITOR_OPENED}`. |
| Status | Not run |

### TC-14-API-2.2 — Server-only and subscription event names are refused from a client

| Field | Value |
|---|---|
| Description | This is a tokenless write. If the route accepted the whole twelve-name catalogue, anyone with `curl` could insert `SUBSCRIPTION_ACTIVATED` rows into the table Story 15 computes revenue from, and forge `GENERATION_COMPLETED` and `LOGIN_SUCCESS` in the same move. |
| Preconditions | No rows for visitor V1. |
| Test data | Three requests with `event_name` `SUBSCRIPTION_ACTIVATED`, `GENERATION_COMPLETED`, `LOGIN_SUCCESS`; visitor V1; a distinct occurrence key each. |
| Steps | 1. `POST` the event named `SUBSCRIPTION_ACTIVATED`.<br>2. `POST` the event named `GENERATION_COMPLETED`.<br>3. `POST` the event named `LOGIN_SUCCESS`.<br>4. Read the three statuses and bodies.<br>5. In a fresh session, count `analytics_events` rows for visitor V1. |
| Expected result | Each answers `400` with `error_code` `UNKNOWN_EVENT_NAME`; no response body repeats the submitted name; the row count for V1 is `0`. |
| Status | Not run |

### TC-14-API-2.3 — A malformed visitor identifier is refused and never stored raw

| Field | Value |
|---|---|
| Description | The column is a native `uuid`. A value it cannot parse must be refused at the edge, not coerced to an empty string or NULL — a NULL `visitor_id` means «server-emitted during the migration window» and must not be spelled by a browser. |
| Preconditions | `analytics_events` empty of rows written by this case. |
| Test data | `visitor_id` `not-a-uuid`; `event_name` `SITE_VISITED`; `occurrence_key` K1. |
| Steps | 1. `POST` the event with `visitor_id` set to `not-a-uuid`.<br>2. Read the status and body.<br>3. In a fresh session, count rows with `occurrence_key` = K1.<br>4. In the same read, count rows whose `visitor_id` is NULL or an empty value. |
| Expected result | `400` with `error_code` `INVALID_VISITOR_ID`; the message does not contain the string `not-a-uuid`; no row exists for K1; the count of rows with a NULL or empty `visitor_id` is unchanged from before step 1. |
| Status | Not run |

### TC-14-API-2.4 — The same visitor written in any accepted form is one visitor

| Field | Value |
|---|---|
| Description | If the column were text, four accepted spellings of one UUID would be four visitors and every unique-visitor figure would be silently multiplied. |
| Preconditions | No rows for the UUID under test. |
| Test data | One UUID in four spellings — upper case `7B1F2C40-6D83-4A19-9E52-0C4A7D18B3F6`, lower case `7b1f2c40-6d83-4a19-9e52-0c4a7d18b3f6`, braced `{7b1f2c40-6d83-4a19-9e52-0c4a7d18b3f6}`, urn `urn:uuid:7b1f2c40-6d83-4a19-9e52-0c4a7d18b3f6`. A distinct occurrence key per request. |
| Steps | 1. `POST` a `SITE_VISITED` under the upper-case spelling.<br>2. Repeat under the lower-case spelling.<br>3. Repeat under the braced spelling.<br>4. Repeat under the urn spelling.<br>5. In a fresh session, count distinct `visitor_id` values across the four rows.<br>6. Query `information_schema.columns` for the declared type of `analytics_events.visitor_id`. |
| Expected result | All four answer `204`; four rows exist; `COUNT(DISTINCT visitor_id)` is exactly `1`; `information_schema.columns.data_type` for `visitor_id` is `uuid`. |
| Status | Not run |

---

## 3. Ingest Guards — Payload Boundaries

### TC-14-API-3.1 — A payload at the size limit is accepted and one byte over is refused

| Field | Value |
|---|---|
| Description | A bound is only a bound if it is tested on both sides of its own edge; an off-by-one here either refuses legitimate context or admits an unbounded write. |
| Preconditions | No rows for visitor V1. |
| Test data | `payload` whose serialized form is exactly 4096 bytes; the same payload at 4097 bytes. ASCII fill. Distinct occurrence keys. |
| Steps | 1. `POST` a `SITE_VISITED` for V1 carrying the 4096-byte payload.<br>2. Read the status; in a fresh session read the stored row.<br>3. `POST` a `SITE_VISITED` for V1 carrying the 4097-byte payload under a fresh occurrence key.<br>4. Read the status and body.<br>5. In a fresh session, look for a row under the second occurrence key. |
| Expected result | Step 1 answers `204` and the stored `payload` equals the 4096-byte object sent; step 3 answers `400` with `error_code` `INVALID_PAYLOAD` and does not echo the payload; no row exists under the second occurrence key. |
| Status | Not run |

### TC-14-API-3.2 — A payload that is small but deeply nested or wide is refused, not crashed

| Field | Value |
|---|---|
| Description | 4 KiB of `[[[[…]]]]` is under the size limit and still meets Python's decoder as a `RecursionError` — a `500` on a request that passed validation. Depth and key count are separate bounds for exactly this reason. |
| Preconditions | Events route reachable; response times measurable. |
| Test data | (a) a payload nested 9 levels deep, well under 4096 bytes; (b) a payload with 65 keys, well under 4096 bytes. Distinct occurrence keys; visitor V1. |
| Steps | 1. `POST` a `SITE_VISITED` carrying payload (a) and time the response.<br>2. `POST` a `SITE_VISITED` carrying payload (b) and time the response.<br>3. Read both statuses, `error_code`s and elapsed times. |
| Expected result | Both answer `400` with `error_code` `INVALID_PAYLOAD`; neither answers `500` and neither body carries a `correlation_id`; both respond within the endpoint's normal response budget (no `RecursionError`, no stack unwinding delay). |
| Status | Not run |

### TC-14-API-3.3 — A payload containing characters the store cannot hold is refused cleanly

| Field | Value |
|---|---|
| Description | Postgres `jsonb` refuses `U+0000` and a lone surrogate. Without an edge guard these surface as a `500` on an anonymous endpoint whose errors reach anyone. |
| Preconditions | No rows for visitor V1. |
| Test data | (a) `{"note": "a\u0000b"}`; (b) `{"note": "a\ud800b"}` (unpaired surrogate). Distinct occurrence keys; visitor V1. |
| Steps | 1. `POST` a `SITE_VISITED` carrying payload (a).<br>2. `POST` a `SITE_VISITED` carrying payload (b).<br>3. Read both statuses and bodies.<br>4. In a fresh session, count rows under both occurrence keys. |
| Expected result | Both answer `400` with `error_code` `INVALID_PAYLOAD`; neither answers `500`; neither body echoes the submitted text; zero rows exist under either occurrence key. |
| Status | Not run |

### TC-14-API-3.4 — An oversized body is refused on bytes read, not on the declared length

| Field | Value |
|---|---|
| Description | A chunked body carries no `Content-Length`, so a check on the declared length lets an unbounded upload walk straight past it — the scar recorded in `avatar_router.py`. |
| Preconditions | A client able to send `Transfer-Encoding: chunked`. |
| Test data | A body of 20000 bytes (over `ANALYTICS_MAX_BODY_BYTES=16384`) sent chunked with no `Content-Length`. |
| Steps | 1. Open a request to the events endpoint with `Transfer-Encoding: chunked` and no `Content-Length`.<br>2. Stream the 20000-byte body.<br>3. Read the status and body.<br>4. Inspect peak bytes buffered by the handler for that request. |
| Expected result | `413` with `{"error_code": "REQUEST_BODY_TOO_LARGE", "message": …}` in the canonical shape; the connection is cut at the cap rather than after the whole body; peak buffered bytes do not exceed the 16384-byte cap plus one read chunk. |
| Status | Not run |

### TC-14-API-3.5 — The payload limit is measured in bytes, not in characters

| Field | Value |
|---|---|
| Description | With an ASCII fixture the byte count and the character count are the same number, so an implementation counting the wrong unit passes TC-14-API-3.1 unchanged. §7.12 is this case's mirror on the other unit. |
| Preconditions | No rows for visitor V1. |
| Test data | A payload built from astral-plane code points (4 bytes each) serializing to exactly 4096 bytes — roughly 1000 characters; and the same one code point longer, 4100 bytes and still ~1001 characters. Distinct occurrence keys. |
| Steps | 1. `POST` a `SITE_VISITED` carrying the at-the-limit astral payload.<br>2. Read the status; in a fresh session read the stored payload.<br>3. `POST` a `SITE_VISITED` carrying the over-the-limit astral payload.<br>4. Read the status and body.<br>5. In a fresh session, look for a row under the second occurrence key. |
| Expected result | Step 1 answers `204` and the stored payload is byte-identical to what was sent; step 3 answers `400` with `error_code` `INVALID_PAYLOAD`; no row exists under the second occurrence key — the refusal fires on bytes, not on the ~1001 characters. |
| Status | Not run |

### TC-14-API-3.6 — A payload survives store and read with its values unchanged

| Field | Value |
|---|---|
| Description | JSON's exact-integer range stops at 2^53; a float round-trip silently rewrites a large id and drops a decimal's scale. Story 15 reads these values as facts. |
| Preconditions | No rows for occurrence key K1. |
| Test data | `{"big": 9007199254740993, "money": "10.50", "ключ🎓": "значение🎓"}` — one integer above 2^53, one decimal with a trailing zero, one key and one value outside the basic plane. |
| Steps | 1. `POST` a `SITE_VISITED` for V1 with occurrence key K1 carrying the payload above.<br>2. In a **fresh session**, read the stored `payload`. |
| Expected result | `204`; the fresh read returns `big` as exactly `9007199254740993` (not `9007199254740992`), `money` as exactly `10.50` with its trailing zero intact, and the key and value `ключ🎓` / `значение🎓` byte-identical; no number is returned in exponent or float form. |
| Status | Not run |

---

## 4. Ingest — Server-Owned Fields

### TC-14-API-4.1 — A client cannot choose the account an event belongs to

| Field | Value |
|---|---|
| Description | `user_id` is derived from the token and is deliberately absent from the request schema. A bindable `user_id` on a tokenless route lets anyone write events onto anyone's account. |
| Preconditions | Accounts A and B both registered and verified. |
| Test data | Account A's Bearer token; body `{"event_name":"SITE_VISITED","visitor_id":"7b1f…","occurrence_key":"c0d51e73-…","user_id":"9f3c1a58-7e04-4b62-8d19-5a2f07c3b6e1"}` (account B's id). |
| Steps | 1. `POST` the body above with account A's access token.<br>2. In a fresh session, read the stored row for occurrence key K1.<br>3. In the same read, count rows whose `user_id` equals account B's id. |
| Expected result | `204`; the stored row's `user_id` equals **account A's** id; the count of rows attributed to account B is `0`. |
| Status | Not run |

### TC-14-API-4.2 — A client cannot choose when an event happened

| Field | Value |
|---|---|
| Description | `event_time` comes from the server's injected `Clock`. A client-set time lets anyone backdate rows into a closed reporting period. |
| Preconditions | Server clock readable; no rows for occurrence key K1. |
| Test data | `{"event_name":"SITE_VISITED","visitor_id":"7b1f…","occurrence_key":"c0d51e73-…","event_time":"2001-01-01T00:00:00Z"}`. |
| Steps | 1. Record the server's current time.<br>2. `POST` the body above with no token.<br>3. In a fresh session, read `event_time` on the stored row. |
| Expected result | `204`; the stored `event_time` is within seconds of the time recorded in step 1 and is **not** `2001-01-01T00:00:00Z`; the value is timezone-aware. |
| Status | Not run |

### TC-14-API-4.3 — A client cannot choose an event's identity or its position in the order

| Field | Value |
|---|---|
| Description | `sequence` is the total-order key Story 15 pages on, and `id` is the row's identity. A client that can set either can insert itself anywhere in another visitor's timeline or collide with an existing row. |
| Preconditions | No rows for occurrence key K1. |
| Test data | Body adding `"id":"00000000-0000-4000-8000-000000000001"` and `"sequence": 1`. |
| Steps | 1. `POST` the body above with no token.<br>2. In a fresh session, read the stored row's `id` and `sequence`. |
| Expected result | `204`; the stored `id` is not `00000000-0000-4000-8000-000000000001`; the stored `sequence` is the server-assigned next value and not `1` unless `1` is genuinely the next value for an empty table; both are server-minted. |
| Status | Not run |

### TC-14-API-4.4 — A field this version does not know is ignored, not refused

| Field | Value |
|---|---|
| Description | Frontend and backend ship as independently deployable repositories, so a newer client reaching an older backend is routine rather than an edge. |
| Preconditions | No rows for either occurrence key used. |
| Test data | Request X: the minimal valid body. Request Y: the same body plus `"session_kind": "pwa"`, a field this version does not define. Distinct occurrence keys, same visitor V1. |
| Steps | 1. `POST` request X.<br>2. `POST` request Y.<br>3. Read both statuses.<br>4. In a fresh session, read both stored rows and compare every column except `id`, `sequence`, `event_time` and the occurrence key. |
| Expected result | Both answer `204` (neither answers `400` or `422`); both rows exist; the compared columns are identical between X and Y — in particular `payload` is `{}` on both and `session_kind` is stored nowhere. |
| Status | Not run |

The frontend and backend are published as independently deployable repositories, so a newer
client reaching an older backend is routine rather than an edge. Every other case in this
section feeds *server-owned* fields and asserts they have no effect — a request model that
refuses unknown keys satisfies all of them and breaks every deploy where the client ships
first.

---

## 5. Ingest — Re-run Safety (inbound duplicate)

### TC-14-API-5.1 — One occurrence reported twice is recorded once

| Field | Value |
|---|---|
| Description | React StrictMode double-invokes effects and the second request is genuinely sent. The client cannot unsend it, so the collapse is server-side — and it must answer success, not an error. |
| Preconditions | No rows for visitor V1. |
| Test data | The identical body twice: `SITE_VISITED`, visitor V1, occurrence key K1. |
| Steps | 1. `POST` the body.<br>2. `POST` the byte-identical body a second time.<br>3. Read both statuses.<br>4. In a fresh session, count rows for visitor V1 with occurrence key K1. |
| Expected result | Both requests answer `204` (the second is not a `409` and not a `400`); exactly one row exists for V1 with K1. |
| Status | Not run |

### TC-14-API-5.2 — Two distinct occurrences from one visitor are both recorded

| Field | Value |
|---|---|
| Description | The mirror of TC-14-API-5.1: a dedupe keyed on the visitor alone, or on the event name alone, would collapse two real page loads into one and halve every visit count. |
| Preconditions | No rows for visitor V1. |
| Test data | Two `SITE_VISITED` bodies for visitor V1 with occurrence keys K1 and K2. |
| Steps | 1. `POST` the event with occurrence key K1.<br>2. `POST` the event with occurrence key K2.<br>3. In a fresh session, count rows for visitor V1. |
| Expected result | Both answer `204`; exactly two rows exist for V1; their occurrence keys are K1 and K2 and their `sequence` values differ. |
| Status | Not run |

### TC-14-API-5.3 — A missing or malformed occurrence key is refused

| Field | Value |
|---|---|
| Description | Without a usable key there is nothing to collapse on, so an absent key would make every StrictMode double-fire a second row. |
| Preconditions | No rows for visitor V1. |
| Test data | (a) a body with `occurrence_key` omitted entirely; (b) a body with `occurrence_key` set to `abc-123`. Both `SITE_VISITED`, visitor V1. |
| Steps | 1. `POST` body (a).<br>2. `POST` body (b).<br>3. Read both statuses and bodies.<br>4. In a fresh session, count rows for visitor V1. |
| Expected result | Both answer `400` with `error_code` `INVALID_OCCURRENCE_KEY`; neither body echoes `abc-123`; the row count for V1 is `0`. |
| Status | Not run |

### TC-14-API-5.4 — One occurrence reported to two instances is recorded once

| Field | Value |
|---|---|
| Description | A per-process set of seen keys passes TC-14-API-5.1 forever. This is the case that forces the «done» marker into shared storage, which the multi-instance rule requires. |
| Preconditions | Two application instances running against one database. No rows for visitor V1. |
| Test data | The identical body — `SITE_VISITED`, visitor V1, occurrence key K1 — sent to instance 1 then instance 2. |
| Steps | 1. `POST` the body to instance 1.<br>2. `POST` the byte-identical body to instance 2.<br>3. Read both statuses.<br>4. In a fresh session, count rows for V1 with key K1.<br>5. Restart instance 1, `POST` the same body to it again, and re-count. |
| Expected result | Every request answers `204`; the fresh read returns exactly one row for V1 with K1 after step 4, and still exactly one after step 5 — the marker survives a process restart because it lives in the database. |
| Status | Not run |

A per-process set of seen keys passes TC-14-API-5.1 forever. This is the case that forces the
«done» marker into shared storage, which the multi-instance rule requires.

### TC-14-API-5.5 — One occurrence reported twice at the same instant is recorded once

| Field | Value |
|---|---|
| Description | The production shape is a StrictMode double-invoke where both requests are in flight together. A read-then-insert dedupe passes 5.1 and 5.4 and writes two rows here. |
| Preconditions | A latch installable between the existence check and the insert, as `test_document_storage_concurrency.py` does. No rows for visitor V1. |
| Test data | Two identical bodies — `SITE_VISITED`, visitor V1, occurrence key K1 — released together at the latch. |
| Steps | 1. Install a latch at the point where the recorder decides whether the occurrence already exists.<br>2. Issue both requests and hold both at the latch.<br>3. Release both.<br>4. Read both statuses.<br>5. In a fresh session, count rows for V1 with K1.<br>6. Inspect the schema for a unique constraint on `(visitor_id, occurrence_key)`. |
| Expected result | Both answer `204`; exactly one row exists; the second insert was rejected by a **unique constraint in the store** (visible in the schema and in the caught integrity error), not avoided by a prior read. |
| Status | Not run |

The production shape is a StrictMode double-invoke where the second request is genuinely
sent — both are in flight together. A read-then-insert dedupe passes 5.1 and 5.4 and writes
two rows here.

### TC-14-API-5.6 — One occurrence key in two letter cases is one occurrence

| Field | Value |
|---|---|
| Description | Stored as text, case variants stop collapsing — and collapsing is the entire reason the key exists. |
| Preconditions | No rows for visitor V1. |
| Test data | Occurrence key upper `C0D51E73-84B2-4F16-9A07-3E5B18D6C294` then lower `c0d51e73-84b2-4f16-9a07-3e5b18d6c294`, same visitor V1, same `event_name` `SITE_VISITED`. |
| Steps | 1. `POST` the event with the upper-case key.<br>2. `POST` the event with the lower-case key.<br>3. Read both statuses.<br>4. In a fresh session, count rows for V1.<br>5. Query `information_schema.columns` for the occurrence-key column's declared type. |
| Expected result | Both answer `204`; exactly one row exists for V1; `information_schema.columns.data_type` for the occurrence-key column is `uuid`, not `character varying` or `text`. |
| Status | Not run |

The two spec documents disagree on what this key is — the story's validation table says
«bounded» with no unit or type, `endpoints.md` says a client-minted UUID that «sidesteps a
length bound and a normalization question entirely». Stored as text, case variants stop
collapsing, and collapsing is the entire reason the key exists.

---

## 6. Ingest — Abuse Bounds

### TC-14-API-6.1 — A caller at the rate limit is served and one request over is refused

| Field | Value |
|---|---|
| Description | This is the product's busiest write path and its only tokenless one; without a bound one script fills the table Story 15 reads. |
| Preconditions | `ANALYTICS_EVENT_RATE_LIMIT=120`, `ANALYTICS_EVENT_RATE_WINDOW_SECONDS=60`. Injected `Clock` stub so the window is advanced, never waited on. Bucket empty. |
| Test data | 120 valid `SITE_VISITED` events from one source, each with a fresh occurrence key; then a 121st. |
| Steps | 1. `POST` 120 valid events from one source within one window.<br>2. `POST` a 121st event in the same window.<br>3. Read its status and body.<br>4. In a fresh session, count rows for that visitor.<br>5. Advance the `Clock` past the window and `POST` one more event. |
| Expected result | The first 120 answer `204`; the 121st answers `429` with `error_code` `RATE_LIMITED`; the stored row count is exactly `120` — the refused request wrote nothing; after the window advances the next event answers `204` and the count becomes `121`. |
| Status | Not run |

### TC-14-API-6.2 — Analytics traffic cannot exhaust an account's sign-in budget

| Field | Value |
|---|---|
| Description | Buckets key on `client_source()` in a key space separate from OAuth's. Sharing one bucket would let a page-view flood lock a real user out of signing in. |
| Preconditions | Account A registered and verified. The analytics bucket for one source driven to its limit. |
| Test data | 120 events from address `203.0.113.7`; then a sign-in for account A from the same address. |
| Steps | 1. `POST` 120 events from `203.0.113.7` until the analytics bucket is exhausted.<br>2. Confirm a 121st event answers `429`.<br>3. `POST /api/v1/auth/login` as account A from the same address. |
| Expected result | Step 2 answers `429 RATE_LIMITED`; step 3 answers `200` with a token pair — not `429`; the `oauth_rate_limits` rows for OAuth's own key space are unchanged in count by steps 1–2. |
| Status | Not run |

### TC-14-API-6.3 — A rate limiter that cannot answer refuses the event

| Field | Value |
|---|---|
| Description | Fails **closed** by design. The story-wide rule «an analytics failure never changes the user's operation» applies to the product's operations, not to the only volume bound on its busiest write path. |
| Preconditions | The rate-limit adapter fault-injected to raise on every call. No rows for visitor V1. |
| Test data | One valid `SITE_VISITED`, visitor V1, occurrence key K1. |
| Steps | 1. Fault-inject the rate-limit adapter to raise.<br>2. `POST` the valid event.<br>3. Read the status and body.<br>4. In a fresh session, count rows for V1. |
| Expected result | `503` in the canonical envelope; the request is **not** admitted; the row count for V1 is `0`. |
| Status | Not run |

### TC-14-API-6.4 — The rate limit is one budget across every instance

| Field | Value |
|---|---|
| Description | A per-instance in-memory bucket passes 6.1, 6.2 and 6.3 and yields the limit multiplied by the instance count on the product's hottest write path. |
| Preconditions | Two instances against one database. Bucket empty. `Clock` stub injected in both. |
| Test data | 120 events through instance 1; the 121st through instance 2. Then elapsed-window rows pruned while a live window is being counted. |
| Steps | 1. `POST` 120 events from one source through instance 1.<br>2. `POST` the 121st from the same source through instance 2.<br>3. Read its status and body.<br>4. In a fresh session, count stored rows for that source.<br>5. With a live window part-counted, run the elapsed-window pruning job.<br>6. `POST` one more event in the live window and read the status. |
| Expected result | Step 2 answers `429 RATE_LIMITED`; step 4 returns exactly `120` rows; after step 5 the live window's counter is unchanged (the pruning removed only elapsed-window rows) and step 6 still answers `429` — the live count was not reset to zero. |
| Status | Not run |

A per-instance in-memory bucket passes 6.1, 6.2 and 6.3 and yields the limit multiplied by
the instance count on the product's hottest write path.

### TC-14-API-6.5 — The window admits exactly at the rollover instant

| Field | Value |
|---|---|
| Description | 6.1's «when the next window begins» is satisfiable by a real-time wait, which is the flaky shape, and cannot distinguish a window that rolls at the boundary from one that rolls a whole window late. |
| Preconditions | Injected `Clock` stub — never a real-time wait. A caller at the limit within one window. |
| Test data | Clock fixed at `window_start + 59.999 s`, then at exactly `window_start + 60.000 s`. |
| Steps | 1. Drive the bucket to 120 events with the clock inside one window.<br>2. Fix the clock one tick before the window ends and `POST` an event.<br>3. Advance the clock to exactly the rollover instant and `POST` an event.<br>4. Read both statuses.<br>5. Read the counter value for the new window. |
| Expected result | Step 2 answers `429 RATE_LIMITED`; step 3 answers `204`; the new window's counter reads `1`, not `121` — the bucket started over rather than resuming the exhausted one. |
| Status | Not run |

### TC-14-API-6.6 — A rate limiter that does not answer does not hold the request open

| Field | Value |
|---|---|
| Description | 6.3 covers a limiter that raises. A limiter that simply never answers holds a database connection and, at page-view volume, drains the pool the product's own calls need. |
| Preconditions | The rate-limit adapter stubbed to hang. Connection-pool checkout observable. |
| Test data | One valid `SITE_VISITED`, visitor V1; the endpoint's normal response budget as the assertion bound. |
| Steps | 1. Stub the rate-limit store to never answer.<br>2. `POST` the valid event and time the response.<br>3. Read the status.<br>4. In a fresh session, count rows for V1.<br>5. Read the connection pool's checked-out count after the response. |
| Expected result | The request is refused within the endpoint's normal response budget (no open-ended wait); the row count for V1 is `0`; the pool's checked-out count returns to its pre-request value — the connection was released, not leaked. |
| Status | Not run |

### TC-14-API-6.7 — Events refused by the limiter are counted, not merely dropped

| Field | Value |
|---|---|
| Description | By design the client drops the refusal silently, so without this an arbitrary share of the product's most-emitted event vanishes with nothing server-side distinguishing the limiter from a quiet day. |
| Preconditions | Structured log records capturable. Bucket at the limit for one source. |
| Test data | 5 further events past the limit; then 3 events from a fresh source within the limit. |
| Steps | 1. Drive one source past 120 events in a window.<br>2. `POST` 5 further events and capture the emitted log records.<br>3. From a fresh source, `POST` 3 events within the limit and capture the log records.<br>4. Inspect the fields of the captured records. |
| Expected result | Step 2 produces exactly 5 rate-limited records, each distinct from the swallowed-emission-failure record and each carrying the bucket key and the `event_name` as **fields**, not interpolated into the message; step 3 produces zero such records. |
| Status | Not run |

By design the client drops the refusal silently, so without this an arbitrary share of the
product's most-emitted event vanishes with nothing server-side distinguishing the limiter
from a quiet day.

---

## 7. Registration Context

### TC-14-API-7.1 — Registration stores the caller's technical context and first-touch attribution

| Field | Value |
|---|---|
| Description | The whole point of the register extension: without these ten columns a CAC-by-UTM report has no source data at all. |
| Preconditions | `qa.newvisitor@textery.test` not registered. Geolocation resolver configured and answering. |
| Test data | Address `203.0.113.7`; `User-Agent` of a mobile Safari on iOS; `Accept-Language: ru-RU,ru;q=0.9,en;q=0.8`; body carrying `utm_source=vk`, `utm_medium=cpc`, `utm_campaign=spring2026`, `utm_content=banner_a`, `utm_term=диплом`. |
| Steps | 1. `POST /api/v1/auth/register` with the credentials, headers and `utm_*` above.<br>2. Read the response status.<br>3. In a **fresh session**, read the created `accounts` row. |
| Expected result | Registration answers its normal success status; the fresh read shows IP `203.0.113.7`, a resolved country code, device type `mobile`, OS `iOS`, device language `ru-RU`, and all five `utm_*` exactly as sent — `vk`, `cpc`, `spring2026`, `banner_a`, `диплом`. |
| Status | Not run |

### TC-14-API-7.2 — The context survives the next write to the same account

| Field | Value |
|---|---|
| Description | `save()`'s update branch and `to_domain` each enumerate columns by hand. A column present in one list and missing from the other writes NULL over the whole context at the first later write. |
| Preconditions | An account registered with the full context of TC-14-API-7.1, still unverified. |
| Test data | The verification code; a new display name; one deliberately wrong password for the failed sign-in. |
| Steps | 1. Confirm the account's verification code.<br>2. In a fresh session, read all ten context columns.<br>3. Rename the account through `PATCH /api/v1/auth/me`.<br>4. In a fresh session, read all ten columns again.<br>5. Attempt a sign-in with a wrong password (which increments the failed-attempt counter).<br>6. In a fresh session, read all ten columns a third time. |
| Expected result | After each of steps 2, 4 and 6 all ten values are byte-identical to those stored at registration — IP, country, device type, OS, language and the five `utm_*` — with none turned NULL and none truncated. |
| Status | Not run |

### TC-14-API-7.3 — An account created before this feature still reads

| Field | Value |
|---|---|
| Description | No backfill is planned, so every pre-existing account row carries eleven NULLs. A mapper that assumes the columns are populated breaks `GET /me` for the entire existing user base. |
| Preconditions | An `accounts` row inserted directly with IP, country, device type, OS, language and all five `utm_*` NULL. That account holds a live access token. |
| Test data | The legacy account's id and access token. |
| Steps | 1. Read the legacy row through `SqlAlchemyAccountRepository.find_by_id`.<br>2. `GET /api/v1/auth/me` with that account's token.<br>3. Inspect the domain object and the response body for the context values. |
| Expected result | Step 1 returns the account without raising; step 2 answers `200`; every absent context value reads as `None`/absent — never as `""`, `"unknown"`, `"XX"` or any other placeholder. |
| Status | Not run |

### TC-14-API-7.4 — The country of an address that cannot be located is unset

| Field | Value |
|---|---|
| Description | Loopback and private addresses are what every local run and every misconfigured proxy hop produces; they must yield a NULL country, not a failed registration and not a fabricated code. |
| Preconditions | Geolocation resolver configured. Two unregistered emails. |
| Test data | Registration from `127.0.0.1`; registration from `10.0.0.5`. |
| Steps | 1. `POST /api/v1/auth/register` with the caller address `127.0.0.1`.<br>2. `POST /api/v1/auth/register` with the caller address `10.0.0.5`.<br>3. Read both statuses.<br>4. In a fresh session, read the country column on both accounts. |
| Expected result | Both registrations answer their normal success status with the normal body; both accounts' country columns are `NULL`; neither carries a placeholder code; no resolution failure is reported for either, because no lookup was attempted. |
| Status | Not run |

### TC-14-API-7.5 — Attribution values are normalized before the bound, and dropped over it

| Field | Value |
|---|---|
| Description | The bound decides what is **stored**, never what is **answered**. The order matters: normalizing after the bound rejects a value that would have fit. |
| Preconditions | Two unregistered emails. Structured log records capturable. |
| Test data | (a) a `utm_campaign` of 205 decomposed code points that is exactly 200 after NFC; (b) a `utm_campaign` of 201 code points after NFC, sent alongside four valid values. A control registration with no `utm_*` at all. |
| Steps | 1. Register a visitor carrying value (a).<br>2. In a fresh session, read `utm_campaign` on that account.<br>3. Register a second visitor carrying value (b) plus four valid `utm_*`.<br>4. Compare its status, body and `error_code` set against the control registration that carried no `utm_*`.<br>5. In a fresh session, read all five `utm_*` on the second account.<br>6. Read the captured log records. |
| Expected result | Step 2 shows the NFC-normalized 200-code-point value stored in full; step 4 shows an identical status, an identical body shape and an identical (empty) `error_code` set to the no-attribution control; step 5 shows all five `utm_*` `NULL` — including the four valid ones — and nothing truncated to 200; step 6 shows exactly one discard record naming the field and the reason and carrying no value. |
| Status | Not run |

The bound decides what is **stored**, never what is **answered** — the Governing Decision in
`14_AnalyticsEventTracking.md`. The four valid values go with the bad one because attribution
is stored as a set (`B2`): a stored set is always a faithful copy of one real link.

### TC-14-API-7.5a — Attribution never changes the registration's answer

| Field | Value |
|---|---|
| Description | The case that goes red on the defect this story is most likely to ship. Every other attribution case asserts what was *stored*; this one asserts that the caller cannot tell from the response that attribution was involved at all. A `400 INVALID_UTM` would satisfy «nothing is stored truncated» perfectly. |
| Preconditions | Two unregistered emails with otherwise identical credentials. |
| Test data | Visitor 1: no `utm_*`. Visitor 2: `utm_campaign` of 201 code points after NFC, `utm_source` percent-encoded as a cp1251 byte sequence that is not valid UTF-8, `utm_term` carrying `<script>alert(1)</script>`. |
| Steps | 1. `POST /api/v1/auth/register` for visitor 1 with no `utm_*`; record status, body keys and any `error_code`.<br>2. `POST /api/v1/auth/register` for visitor 2 with the three hostile values; record the same.<br>3. Compare the two responses field by field.<br>4. Sign in as each account and confirm both are usable. |
| Expected result | Both answer the same status code and the same body shape with the same key set; neither body names `utm_source`, `utm_campaign`, `utm_term` or any attribution field; no `error_code` is present on either; both accounts exist and both sign in successfully. |
| Status | Not run |

The case that goes red on the defect this story is most likely to ship. Every other
attribution case asserts what was *stored*; this one asserts that the caller cannot tell
from the response that attribution was involved at all. A `400 INVALID_UTM` would satisfy
«nothing is stored truncated» perfectly.

### TC-14-API-7.6 — The same attribution written two ways is stored one way

| Field | Value |
|---|---|
| Description | Two Unicode spellings of one campaign name are two rows in every group-by, splitting a single campaign's numbers across two lines of the report. |
| Preconditions | Two unregistered emails. |
| Test data | `utm_campaign` in NFC composed form `весна`; the same name in NFD decomposed form (`е` + combining mark). |
| Steps | 1. Register visitor 1 carrying the composed spelling.<br>2. Register visitor 2 carrying the decomposed spelling.<br>3. In a fresh session, read `utm_campaign` on both accounts and compare them byte for byte. |
| Expected result | Both registrations succeed; the two stored values are byte-identical and both equal the NFC form; neither retains a separate combining mark. |
| Status | Not run |

### TC-14-API-7.7 — A client cannot supply its own address, country, device or verification state

| Field | Value |
|---|---|
| Description | Register's writable allow-list is exactly the five `utm_*`. A bindable `is_verified` is a complete bypass of email confirmation; a bindable `failed_attempt_count` resets the lockout. |
| Preconditions | One unregistered email. Caller address `203.0.113.7`, `User-Agent` of desktop Chrome on Windows, `Accept-Language: ru-RU,ru;q=0.9`. |
| Test data | Body additionally carrying `ip=1.2.3.4`, `country=US`, `device_type=tv`, `os=Plan9`, `language=fr-FR`, `is_verified=true`, `failed_attempt_count=99`, `created_at=2001-01-01T00:00:00Z`. |
| Steps | 1. `POST /api/v1/auth/register` with the body above and the headers named.<br>2. Read the status.<br>3. In a fresh session, read every named column on the created account. |
| Expected result | Registration succeeds; IP is `203.0.113.7` not `1.2.3.4`; country is the one resolved from `203.0.113.7` not `US`; device type is `desktop` not `tv`; OS is `Windows` not `Plan9`; language is `ru-RU`, **derived from `Accept-Language`**, not `fr-FR`; `is_verified` is `false`; `failed_attempt_count` is `0`; `created_at` is the server's time, not `2001-01-01`. |
| Status | Not run |

### TC-14-API-7.8 — Text the store cannot hold is dropped at registration, never stored mangled

| Field | Value |
|---|---|
| Description | The events endpoint has this guard at 3.3 and refuses there, because a refusal on the new endpoint costs one analytics row. Here the same input reaches an existing auth route, where a refusal would cost a user their account — so the value is dropped instead. It must go red both on a `500` and on a `400`. |
| Preconditions | Two unregistered emails. Structured log records capturable. Provider handshake reachable. |
| Test data | (a) `utm_campaign` containing `U+0000`; (b) `utm_campaign` containing an unpaired surrogate `U+D800`. Both sent to `POST /auth/register` and to `GET /api/v1/auth/oauth/yandex/start`. |
| Steps | 1. Register visitor 1 carrying value (a); register visitor 2 carrying value (b).<br>2. `GET /api/v1/auth/oauth/yandex/start` carrying value (a), then carrying value (b).<br>3. Read all four statuses and bodies.<br>4. In a fresh session, read all five `utm_*` on both accounts and scan them for a replacement character or a truncated value.<br>5. Read the captured log records. |
| Expected result | Both registrations answer their normal success status; both handshakes answer `302` to the provider; none answers `500` and none answers `400`; both accounts exist with all five `utm_*` `NULL` and no value containing `U+FFFD`, `U+0000` or a truncated remainder; exactly one discard record was emitted per input, naming the field and the reason and carrying no value. |
| Status | Not run |

The events endpoint has this guard at 3.3 and refuses there, because a refusal on the new
endpoint costs one analytics row. Here the same input reaches an existing auth route, where a
refusal would cost a user their account — so the value is dropped instead. The hostile-text
scenario at `05_Security_Tests.md` §3.1 sends only well-formed text, which trips neither
failure; this one is the unstorable-text half, and it must go red both on a `500` and on a
`400`.

### TC-14-API-7.9 — An explicitly empty attribution value and an omitted one are the same stored state

| Field | Value |
|---|---|
| Description | A link ending in `&utm_term=` and a link with no `utm_term` are the same marketing fact; storing `""` for one gives Story 15 two spellings of «no term» to handle at every read. |
| Preconditions | Two unregistered emails. |
| Test data | Visitor 1: `utm_source=vk`, `utm_medium=cpc`, `utm_campaign=spring2026`, `utm_content=banner_a`, `utm_term=` (explicit empty). Visitor 2: the same four values with `utm_term` omitted entirely. |
| Steps | 1. Register visitor 1 with the explicit empty `utm_term`.<br>2. In a fresh session, read all five `utm_*` on that account.<br>3. Register visitor 2 with `utm_term` omitted.<br>4. In a fresh session, read all five `utm_*` on that account and compare with step 2. |
| Expected result | Both registrations succeed; on both accounts `utm_term` is `NULL` (not `""`); on both, `utm_source`, `utm_medium`, `utm_campaign` and `utm_content` hold `vk`, `cpc`, `spring2026`, `banner_a` unchanged; the two accounts' five-column tuples are identical. |
| Status | Not run |

### TC-14-API-7.10 — The highest-priority language tag wins, at every edge of the priority list

| Field | Value |
|---|---|
| Description | An absent `q` means the highest priority, so an implementation defaulting it to the lowest picks the wrong tag; a tag marked `q=0` must never be selected, yet a naive maximum over a single-tag header picks it. |
| Preconditions | Three unregistered emails. |
| Test data | (a) `Accept-Language: en,ru;q=0.9`; (b) `Accept-Language: en;q=0`; (c) `Accept-Language: en;q=abc`. |
| Steps | 1. Register a visitor sending header (a); read the stored language in a fresh session.<br>2. Register a visitor sending header (b); read the stored language.<br>3. Register a visitor sending header (c); read the status and the stored language. |
| Expected result | Step 1 stores `en` — the tag with no stated `q` — not `ru`; step 2 stores `NULL`, never `en`; step 3 answers the normal success status with no `500` and stores `NULL`. |
| Status | Not run |

An absent priority means the highest, so an implementation defaulting it to the lowest picks
the wrong tag; a tag marked unacceptable must never be selected, yet a naive maximum over a
single-tag header picks it.

### TC-14-API-7.11 — An unusable language header stores nothing, never a default

| Field | Value |
|---|---|
| Description | The browser identification has exactly this guard; the language tag had none, so a parser falling through to a default is green against every other case. |
| Preconditions | Three unregistered emails. |
| Test data | (a) `Accept-Language: ???`; (b) `Accept-Language: <script>x</script>\r\nX-Injected: 1`; (c) no `Accept-Language` header at all. |
| Steps | 1. Register a visitor sending header (a).<br>2. Register a visitor sending header (b).<br>3. Register a visitor sending no `Accept-Language`.<br>4. In a fresh session, read the language column on all three accounts. |
| Expected result | All three registrations succeed; all three language columns are `NULL`; none holds the raw header text, the markup or the line break; none holds `ru`, `ru-RU`, `en` or any other most-common fallback. |
| Status | Not run |

The browser identification has exactly this guard; the language tag had none, so a parser
falling through to a default is green against every other case.

### TC-14-API-7.12 — The attribution bound is measured in characters, not bytes

| Field | Value |
|---|---|
| Description | The payload is bounded in **bytes** and the attribution values in **characters**. With an ASCII fixture the two are the same number, so an implementation counting the wrong unit passes both bounds. §3.5 is this case's mirror on the other unit. |
| Preconditions | Two unregistered emails. |
| Test data | `utm_campaign` of exactly 200 astral-plane code points (800 bytes), NFC-stable; and the same value at 201 code points (804 bytes). |
| Steps | 1. Register a visitor carrying the 200-code-point value.<br>2. In a fresh session, read `utm_campaign` on that account.<br>3. Register a visitor carrying the 201-code-point value.<br>4. Read the status.<br>5. In a fresh session, read all five `utm_*` on that account. |
| Expected result | Step 2 shows the full 200-code-point value stored byte-identically and unchanged after NFC — the 800 bytes did not trip the bound; step 4 answers the normal success status; step 5 shows all five `utm_*` `NULL` with nothing truncated to 200 code points. |
| Status | Not run |

The payload is bounded in **bytes** and the attribution values in **characters**. With an
ASCII fixture the two are the same number, so an implementation counting the wrong unit passes
both bounds. §3.5 is this case's mirror on the other unit.

### TC-14-API-7.13 — The language tag is canonicalized under an invariant locale

| Field | Value |
|---|---|
| Description | Under a Turkish locale a naive `lower()` turns `I` into `ı`, producing a language tag that matches nothing — the same trap `test_password_normalization_order.py` already parameterizes. |
| Preconditions | The process runnable under a Turkish locale (`tr_TR`) and under the default locale. One unregistered email per run. |
| Test data | `Accept-Language: TR-tr` containing a dotted capital `I`, e.g. `Accept-Language: TI-TR`. |
| Steps | 1. Run the application under the Turkish locale and register a visitor sending the header above.<br>2. In a fresh session, read the stored language.<br>3. Restart under the default locale and register an identical visitor with the same header.<br>4. In a fresh session, read the stored language and compare with step 2. |
| Expected result | The value stored under the Turkish locale is the invariant-locale canonical tag (containing `i`, never `ı`); it is byte-identical to the value stored under the default locale. |
| Status | Not run |

---

## 8. Emission Bound to the Transition — Auth

### TC-14-API-8.1 — Confirming a code records the registration once

| Field | Value |
|---|---|
| Description | `REGISTRATION_COMPLETED` hangs off the verify CAS winner, not off the register call — an account that never confirms never completed a registration. |
| Preconditions | An account registered but not yet verified; its verification code known. |
| Test data | The account's email and verification code. |
| Steps | 1. `POST /api/v1/auth/verify` with the account's code.<br>2. Read the status.<br>3. In a **fresh session**, count `analytics_events` rows for that account with `event_name` `REGISTRATION_COMPLETED`. |
| Expected result | Verification succeeds; exactly one `REGISTRATION_COMPLETED` row exists for that account. |
| Status | Not run |

### TC-14-API-8.2 — Confirming the same code twice records one registration

| Field | Value |
|---|---|
| Description | A repeat confirmation is idempotent for the user; if the emitter sits outside the CAS it fires again and inflates the completed-registration count by every double-click. |
| Preconditions | An account that has already confirmed its code, with exactly one `REGISTRATION_COMPLETED` recorded. |
| Test data | The same verification code, replayed. |
| Steps | 1. `POST /api/v1/auth/verify` with the same code a second time.<br>2. Read the status.<br>3. In a fresh session, count `REGISTRATION_COMPLETED` rows for that account. |
| Expected result | The request still succeeds (the same status it answers today for a repeat confirmation); the count is still exactly `1`. |
| Status | Not run |

### TC-14-API-8.3 — Two simultaneous confirmations record one registration

| Field | Value |
|---|---|
| Description | The CAS is the only thing that decides which confirmation really performed the transition. An emitter placed after the read rather than after the update fires on both. |
| Preconditions | An account registered but not confirmed. A latch installable between the read and the conditional update. |
| Test data | Two identical confirmations of the same code, released together at the latch. |
| Steps | 1. Install a latch between the read and the conditional update in the verify path.<br>2. Issue two confirmations of the same code and hold both.<br>3. Release both and wait for both to answer.<br>4. In a fresh session, count `REGISTRATION_COMPLETED` rows for the account.<br>5. Inspect the losing update's affected row count and the events it emitted. |
| Expected result | Exactly one `REGISTRATION_COMPLETED` row exists; the losing confirmation's `UPDATE` reports `rowcount == 0` and emitted **nothing**. |
| Status | Not run |

### TC-14-API-8.4 — A first sign-in through a provider records both a registration and a sign-in

| Field | Value |
|---|---|
| Description | An OAuth sign-up is both events at once; recording only the sign-in makes every provider-created account absent from the registration funnel. |
| Preconditions | No account for the provider identity under test. Provider stubbed to return that identity. |
| Test data | Provider `yandex`; a fresh provider identity; the callback's authorization code. |
| Steps | 1. `GET /api/v1/auth/oauth/yandex/start` and follow to the stubbed provider.<br>2. Complete `GET /api/v1/auth/oauth/yandex/callback` for the fresh identity.<br>3. In a fresh session, read all `analytics_events` rows for the created account. |
| Expected result | Exactly one `REGISTRATION_COMPLETED` and exactly one `LOGIN_SUCCESS` row exist for that account; their `event_time` values are byte-identical (the same moment); their `sequence` values differ. |
| Status | Not run |

### TC-14-API-8.5 — A later sign-in through the same provider records only a sign-in

| Field | Value |
|---|---|
| Description | The mirror of 8.4: an emitter that fires on every callback rather than only on account creation counts every returning user as a new registration. |
| Preconditions | An account that already exists through the provider, with one `REGISTRATION_COMPLETED` recorded. |
| Test data | The same provider identity, signing in again. |
| Steps | 1. Complete the provider handshake again for the existing identity.<br>2. In a fresh session, count `LOGIN_SUCCESS` and `REGISTRATION_COMPLETED` rows for that account. |
| Expected result | `LOGIN_SUCCESS` count increased by exactly `1`; `REGISTRATION_COMPLETED` count is still exactly `1`. |
| Status | Not run |

### TC-14-API-8.6 — Attribution frozen in the browser reaches a provider-created account

| Field | Value |
|---|---|
| Description | The account is created inside `/callback`, two redirects away from anything the client can put in a body. Without carrying the set through `/start` and the `oauth_states` row, every provider account registers with NULL attribution — a working sign-up channel absent from every CAC-by-UTM figure. |
| Preconditions | No account for the provider identity under test. Provider stubbed. |
| Test data | `GET /api/v1/auth/oauth/yandex/start?utm_source=vk&utm_medium=cpc&utm_campaign=spring2026&utm_content=banner_a&utm_term=диплом`. |
| Steps | 1. `GET` the handshake URL above and record the `302` to the provider.<br>2. Inspect the provider redirect URL for any `utm_` parameter.<br>3. Complete the callback so the account is created.<br>4. In a **fresh session**, read all five `utm_*` on the created account. |
| Expected result | Step 1 answers `302`; step 2 shows **no** `utm_` parameter forwarded to the provider; step 4 shows `vk`, `cpc`, `spring2026`, `banner_a`, `диплом` — all five values present and unchanged. |
| Status | Not run |

### TC-14-API-8.7 — A pair whose second emission fails keeps the first and re-attempts nothing

| Field | Value |
|---|---|
| Description | The pair is not atomic. Without this, a half-recorded account is indistinguishable in the data from a returning sign-in, and the outbound half — that the missing event is not re-attempted on the next sign-in — has no other case. |
| Preconditions | No account for the provider identity. The recorder fault-injected to fail only on `LOGIN_SUCCESS`. Log records capturable. |
| Test data | Provider `yandex`; a fresh identity; the fault injected on `LOGIN_SUCCESS` only. |
| Steps | 1. Complete the first provider callback for the fresh identity.<br>2. Read the callback's status and confirm the account exists.<br>3. In a fresh session, count `REGISTRATION_COMPLETED` and `LOGIN_SUCCESS` rows for the account.<br>4. Read the captured failure records.<br>5. Remove the fault, sign in again through the provider.<br>6. In a fresh session, re-count both event kinds. |
| Expected result | Step 2: the callback succeeds and the account exists; step 3: exactly one `REGISTRATION_COMPLETED`, zero `LOGIN_SUCCESS`; step 4: exactly one failure record, naming `LOGIN_SUCCESS` and the visitor as fields; step 6: exactly one `LOGIN_SUCCESS` and still exactly one `REGISTRATION_COMPLETED` — the failed emission was not replayed and the registration was not re-emitted. |
| Status | Not run |

The pair is not atomic. Without this, a half-recorded account is indistinguishable in the
data from a returning sign-in, and the outbound half — that the stored event is not
re-attempted on the next sign-in — has no other case.

---

## 9. Emission Bound to the Transition — Generation & Documents

### TC-14-API-9.1 — Requesting a generation records a start and remembers the visitor

| Field | Value |
|---|---|
| Description | `generations.visitor_id` is written here and read by the completion emitter — a sweep-recovered generation on another replica has no other way to know whose it was. |
| Preconditions | Account A signed in with a live access token. |
| Test data | `POST /api/v1/generations` with account A's token, carrying visitor V1. |
| Steps | 1. `POST /api/v1/generations` as account A, carrying visitor V1.<br>2. Read the created generation id.<br>3. In a fresh session, count `GENERATION_STARTED` rows for that account.<br>4. In the same read, read `generations.visitor_id` for the created row. |
| Expected result | Exactly one `GENERATION_STARTED` row exists for the account; `generations.visitor_id` equals `7b1f2c40-6d83-4a19-9e52-0c4a7d18b3f6`. |
| Status | Not run |

### TC-14-API-9.2 — A completed generation is recorded with the requesting visitor, from any instance

| Field | Value |
|---|---|
| Description | The completion runs wherever the worker happens to be. Reading the visitor from request-scoped state instead of the generation row emits an empty visitor on every cross-instance completion. |
| Preconditions | A generation requested by account A carrying visitor V1, still in progress. Two instances against one database. |
| Test data | The generation id; completion executed from instance 2 (a separate session/process). |
| Steps | 1. Execute `GenerateDocument` for that generation from instance 2.<br>2. In a fresh session, read the `GENERATION_COMPLETED` rows for that generation. |
| Expected result | Exactly one `GENERATION_COMPLETED` row exists; its `visitor_id` equals `7b1f2c40-6d83-4a19-9e52-0c4a7d18b3f6`, not NULL and not the completing instance's own value. |
| Status | Not run |

### TC-14-API-9.3 — A generation completed twice records one completion

| Field | Value |
|---|---|
| Description | Only the CAS winner really performed the transition. An emitter outside the CAS window records a completion for a result that was thrown away. |
| Preconditions | A generation in progress. A latch installable at the CAS window. Two workers with distinguishable results R1 and R2. |
| Test data | Worker 1 storing result R1, worker 2 storing result R2, interleaved at the CAS window. |
| Steps | 1. Install a latch at the CAS window.<br>2. Have both workers attempt to store their result and hold both.<br>3. Release both and wait.<br>4. In a fresh session, count `GENERATION_COMPLETED` rows for that generation.<br>5. Read the stored generation result and compare with the recorded event. |
| Expected result | Exactly one `GENERATION_COMPLETED` row exists; the stored result is one of R1/R2; the recorded completion belongs to the worker whose result was actually stored, not to the loser. |
| Status | Not run |

### TC-14-API-9.4 — Recovering a stalled generation records no new start

| Field | Value |
|---|---|
| Description | A sweep requeue recovers an occurrence rather than starting one. Emitting there inflates the started-generation count by one per stalled row per instance per tick. |
| Preconditions | 5 generations stalled past `GENERATION_STALE_AFTER_MINUTES`, each with exactly one `GENERATION_STARTED` already recorded. Three instances running `run_stale_generation_sweep` on the same tick. |
| Test data | The 5 stalled generation ids; instance counts 1 and 3, run separately. |
| Steps | 1. Run the sweep on all three instances on the same tick.<br>2. Wait for the sweep to complete.<br>3. In a fresh session, count `GENERATION_STARTED` rows across the 5 generations.<br>4. Repeat the whole case with a single instance and compare the counts. |
| Expected result | The count is exactly `5` — one per generation — after the three-instance run, and exactly `5` after the single-instance run; the number is independent of the instance count. |
| Status | Not run |

### TC-14-API-9.5 — A retried generation records a new start only when a generation was created

| Field | Value |
|---|---|
| Description | `RetryGeneration` emits only when it answers `created`. An emitter on every call counts an idempotent replay as a new generation. |
| Preconditions | A failed generation owned by account A. |
| Test data | `POST /api/v1/generations/{id}/retry` twice under `Idempotency-Key: 5c1e8b90-2a47-4f63-91d0-7e38b4c25a06`; then once under a fresh idempotency key. |
| Steps | 1. `POST` the retry with the first idempotency key.<br>2. `POST` the retry again with the **same** idempotency key.<br>3. In a fresh session, count `GENERATION_STARTED` rows added since the start of the case.<br>4. `POST` the retry under a fresh idempotency key.<br>5. Re-count. |
| Expected result | After step 3 exactly one further `GENERATION_STARTED` was recorded (the replay added none); after step 5 exactly two further starts in total — one per generation actually created. |
| Status | Not run |

### TC-14-API-9.6 — Saving a document records a save

| Field | Value |
|---|---|
| Description | `DOCUMENT_SAVED` is the engagement event the retention funnel rests on; it must fire on the path that really wrote a row. |
| Preconditions | Account A signed in, holding a document with known content. |
| Test data | `POST /api/v1/documents/{id}/save` with changed content and a fresh idempotency key. |
| Steps | 1. `POST` the save with changed content.<br>2. Read the status.<br>3. In a fresh session, count `DOCUMENT_SAVED` rows for that account and document. |
| Expected result | The save succeeds; exactly one `DOCUMENT_SAVED` row exists for that document. |
| Status | Not run |

### TC-14-API-9.7 — A save that persisted nothing records nothing

| Field | Value |
|---|---|
| Description | The `_explain_miss` 200 branch answers success without writing a row. Emitting there counts a network retry as a user edit. |
| Preconditions | A save that has already landed for account A's document, with one `DOCUMENT_SAVED` recorded. |
| Test data | The same save replayed under the same idempotency key, answered through the already-applied branch. |
| Steps | 1. Replay the identical save so it is answered as already applied.<br>2. Read the status.<br>3. In a fresh session, count `DOCUMENT_SAVED` rows for that document. |
| Expected result | The replay answers `200` through the already-applied branch; the `DOCUMENT_SAVED` count is still exactly `1`. |
| Status | Not run |

### TC-14-API-9.8 — A generation that already failed records no completion

| Field | Value |
|---|---|
| Description | A late worker arriving after a failure has performed no transition. An emitter with no state check records a completion for a generation the user was told had failed. |
| Preconditions | A generation already in the `failed` state, with no `GENERATION_COMPLETED` recorded. |
| Test data | A late `GenerateDocument` completion attempt against that generation id. |
| Steps | 1. Attempt to complete the failed generation from a late worker.<br>2. In a fresh session, count `GENERATION_COMPLETED` rows for that generation.<br>3. Read the generation's stored status. |
| Expected result | Zero `GENERATION_COMPLETED` rows exist; the generation's status is still `failed`. |
| Status | Not run |

### TC-14-API-9.9 — A generation that already completed records nothing further

| Field | Value |
|---|---|
| Description | Both other terminal-state cases enter from *failed*. The domain's state setters are bare assignments with no legality check, so a refused retry that still emits inflates the funnel while 9.5 and 9.8 stay green. |
| Preconditions | A generation owned by account A already in the `completed` state, with exactly one `GENERATION_STARTED` and one `GENERATION_COMPLETED` recorded, and a known stored result. |
| Test data | `POST /api/v1/generations/{id}/retry` under a fresh idempotency key; then a late completion attempt. |
| Steps | 1. `POST` the retry for the completed generation under a fresh idempotency key.<br>2. Read the status and `error_code`.<br>3. In a fresh session, count `GENERATION_STARTED` rows for that generation.<br>4. Attempt a late completion of the same generation.<br>5. In a fresh session, count `GENERATION_COMPLETED` rows and read the stored result. |
| Expected result | The retry is refused with the status and `error_code` the route answers today for a non-retryable generation; the `GENERATION_STARTED` count is still exactly `1`; the `GENERATION_COMPLETED` count is still exactly `1`; the stored result is byte-identical to the one recorded in the preconditions. |
| Status | Not run |

Both other terminal-state cases enter from *failed*. The domain's state setters are bare
assignments with no legality check, so a refused retry that still emits inflates the funnel
while 9.5 and 9.8 stay green.

### TC-14-API-9.10 — The requesting visitor survives a requeue

| Field | Value |
|---|---|
| Description | The requeue is a read-modify-write on the same row; a blind full-row write drops the column, and the completion then emits with nothing. 9.2 covers another instance with no requeue in between, and 9.4 counts starts only — neither composes the two. |
| Preconditions | A generation requested by account A carrying visitor V1; the row aged past the stale threshold and requeued by `RequeueStaleGenerations`. |
| Test data | The generation id; visitor V1 `7b1f2c40-6d83-4a19-9e52-0c4a7d18b3f6`. |
| Steps | 1. Request a generation as account A carrying visitor V1.<br>2. Age the row past the stale threshold and run the periodic sweep so it is requeued.<br>3. In a fresh session, read `generations.visitor_id`.<br>4. Complete the requeued generation.<br>5. In a fresh session, read the `GENERATION_COMPLETED` row for it. |
| Expected result | After step 3 `generations.visitor_id` is still `7b1f2c40-6d83-4a19-9e52-0c4a7d18b3f6`, not NULL; the `GENERATION_COMPLETED` row carries that same `visitor_id`, not NULL and not an empty value. |
| Status | Not run |

The requeue is a read-modify-write on the same row; a blind full-row write drops the column,
and the completion then emits with nothing. 9.2 covers another instance with no requeue in
between, and 9.4 counts starts only — neither composes the two.

### TC-14-API-9.11 — One generation failing mid-sweep neither discards the earlier recoveries nor blocks the later ones

| Field | Value |
|---|---|
| Description | A sweep that wraps every row in one transaction loses the recoveries that already succeeded when row three raises; one that aborts on the first error never reaches rows four and five. |
| Preconditions | 5 stalled generations G1–G5 in a known sweep order; the recovery of G3 fault-injected to raise. |
| Test data | G1–G5; fault on G3; two consecutive sweep ticks. |
| Steps | 1. Run the sweep with the fault on G3.<br>2. In a fresh session, read the state of G1–G5 and count `GENERATION_STARTED` rows for each.<br>3. Run the next sweep tick with the fault removed.<br>4. Re-read the states and re-count the starts. |
| Expected result | After step 2: G1 and G2 are recovered, G4 and G5 are recovered, G3 alone is still stalled; no generation gained a `GENERATION_STARTED` row. After step 4: only G3 was picked up; G1, G2, G4 and G5 were not recovered again and recorded no further start. |
| Status | Not run |

---

## 10. Ordering

### TC-14-API-10.1 — Events for one visitor are ordered by their position, not their time

| Field | Value |
|---|---|
| Description | Instance clocks skew. Ordering a funnel by `event_time` across two instances can return the effect before its cause. |
| Preconditions | Two instances with deliberately skewed `Clock` stubs — instance 2's clock reads earlier than instance 1's. No rows for visitor V1. |
| Test data | Cause event `SITE_VISITED` written from instance 1; effect event `REGISTRATION_STARTED` written afterwards from instance 2 whose clock reads earlier. |
| Steps | 1. Write the cause event from instance 1.<br>2. Write the effect event from instance 2 with the skewed clock.<br>3. In a fresh session, read V1's events ordered by the `sequence` column. |
| Expected result | The read returns `SITE_VISITED` first and `REGISTRATION_STARTED` second, despite the second row's `event_time` being the earlier value; ordering by `event_time` would invert them. |
| Status | Not run |

### TC-14-API-10.2 — Two events sharing a moment have a stable, repeatable order

| Field | Value |
|---|---|
| Description | The OAuth pair shares one `event_time` by design. Without a tie-break the two rows come back in whatever order the planner chose, and the funnel flickers between runs. |
| Preconditions | A provider-created account holding exactly the `REGISTRATION_COMPLETED` + `LOGIN_SUCCESS` pair from TC-14-API-8.4, both with the identical `event_time`. |
| Test data | That account's two events; 10 consecutive ordered reads. |
| Steps | 1. Read the visitor's events ordered by `sequence`.<br>2. Repeat the identical read 10 times, in separate sessions.<br>3. Compare the 10 returned orderings. |
| Expected result | All 10 reads return the two events in the identical order; their `event_time` values are equal while their `sequence` values differ, and the `sequence` is what fixes the order. |
| Status | Not run |

### TC-14-API-10.3 — A recorded moment keeps its precision and its zone

| Field | Value |
|---|---|
| Description | A column declared without microsecond precision, or without a zone, silently rounds every event to the second and loses the offset. |
| Preconditions | Injected `Clock` fixed at `2026-08-19T10:15:30.123456+00:00`. No rows for occurrence key K1. |
| Test data | The fixed instant above; one `SITE_VISITED` for visitor V1 with key K1. |
| Steps | 1. Fix the clock at `2026-08-19T10:15:30.123456+00:00`.<br>2. `POST` the event.<br>3. In a **fresh session**, read `event_time` on the stored row.<br>4. Inspect the returned value's `tzinfo`. |
| Expected result | The fresh read returns exactly `2026-08-19T10:15:30.123456+00:00` with the `123456` microseconds intact; the returned value is timezone-aware (`tzinfo` is not `None`). |
| Status | Not run |

### TC-14-API-10.4 — A moment recorded under a non-UTC server timezone is the same instant

| Field | Value |
|---|---|
| Description | 10.3 goes red on a *missing* zone. It cannot go red on the trap the story actually names — a naive value carrying UTC digits round-trips correctly wherever the process runs in UTC, which is every CI run, and is off by the offset everywhere else. |
| Preconditions | The application process `TZ` and the database session `TimeZone` both set to `Europe/Moscow`; a second run with both at `UTC`. Injected `Clock` fixed at a known instant. |
| Test data | Instant `2026-08-19T10:15:30.123456+00:00`; runs under `Europe/Moscow` and under `UTC`. |
| Steps | 1. Run under `Europe/Moscow` with the clock fixed at the instant above and `POST` an event.<br>2. In a fresh session, read the stored `event_time` as an absolute instant.<br>3. Repeat the whole run under `UTC`.<br>4. Compare the two stored absolute instants. |
| Expected result | Step 2 returns the absolute instant `2026-08-19T10:15:30.123456+00:00`, not `2026-08-19T13:15:30` reinterpreted as UTC; the two runs' stored instants are identical when compared as absolute moments. |
| Status | Not run |

10.3 goes red on a *missing* zone. It cannot go red on the trap the story actually names — a
naive value carrying UTC digits round-trips correctly wherever the process runs in UTC, which
is every CI run, and is off by the offset everywhere else.

---

## 11. Account Deletion

### TC-14-API-11.1 — Deleting an account detaches its events and keeps them

| Field | Value |
|---|---|
| Description | The events are aggregate history; the account's personal data is not. Deletion must remove the person and keep the counts, which is exactly what `ON DELETE SET NULL` plus the eraser's scoped UPDATE buys. |
| Preconditions | Account A holding 3 recorded events and a full technical + attribution context. |
| Test data | Account A's id; the 3 event ids. |
| Steps | 1. `DELETE /api/v1/auth/me` as account A and complete the deletion flow.<br>2. In a fresh session, select the 3 event rows by id.<br>3. Read their `user_id` values.<br>4. Query the `accounts` table for account A's id. |
| Expected result | All 3 event rows still exist; every one has `user_id IS NULL`; account A's row is gone, and with it its IP, country, device type, OS, language and all five `utm_*`. |
| Status | Not run |

### TC-14-API-11.2 — Deleting one account leaves every other account's events untouched

| Field | Value |
|---|---|
| Description | The eraser's UPDATE must be scoped to one account. An unscoped predicate detaches every event in the table inside the product's only irreversible operation. |
| Preconditions | Account A holds 3 events, account B holds 2 events, and 4 events belong to no account. Total 9 rows. |
| Test data | The 9 event ids and their `user_id` values recorded before deletion. |
| Steps | 1. Record `user_id` for all 9 rows.<br>2. Delete account A.<br>3. In a fresh session, read all 9 rows again.<br>4. Count all rows in `analytics_events`. |
| Expected result | Account B's 2 rows still carry account B's id unchanged; the 4 unattached rows are still `user_id IS NULL` and otherwise unchanged; the total row count is still `9`; only account A's 3 rows changed, and only in `user_id`. |
| Status | Not run |

### TC-14-API-11.3 — Deleting an account with no events changes nothing

| Field | Value |
|---|---|
| Description | The empty-result path must be a no-op, not an unscoped UPDATE that happens to look correct when the table is small. |
| Preconditions | Account A holds zero recorded events; other accounts hold events. |
| Test data | The full `analytics_events` table snapshot taken before the deletion. |
| Steps | 1. Snapshot every row of `analytics_events` including `user_id`.<br>2. Delete account A.<br>3. In a fresh session, snapshot the table again.<br>4. Compare the two snapshots row by row. |
| Expected result | The two snapshots are identical — no row was modified, none was deleted, and no `user_id` changed. |
| Status | Not run |

### TC-14-API-11.4 — Removing an account row outside the eraser does not fail on its events

| Field | Value |
|---|---|
| Description | The rolling-deploy N-1 path: an old replica removes an account row without knowing about the events table. A `NO ACTION` foreign key turns that into a constraint violation on the deletion path. |
| Preconditions | Account A holding 3 recorded events. |
| Test data | `DELETE FROM accounts WHERE id = <account A's id>` executed as raw SQL. |
| Steps | 1. Execute the raw `DELETE` against the `accounts` row.<br>2. Read the statement's outcome.<br>3. In a fresh session, select the 3 event rows and read their `user_id`. |
| Expected result | The `DELETE` succeeds with no foreign-key violation; all 3 event rows still exist; every one has `user_id IS NULL` — the FK's `ON DELETE SET NULL` did the work. |
| Status | Not run |

### TC-14-API-11.5 — A deletion that fails part-way leaves the events attached

| Field | Value |
|---|---|
| Description | The detach and the account removal are one transaction. A detach committed separately would strip the events' attribution while leaving the account alive. |
| Preconditions | Account A holding 3 recorded events; the removal of the `accounts` row fault-injected to raise. |
| Test data | Account A's id; the 3 event ids. |
| Steps | 1. Fault-inject the account-row removal to raise.<br>2. Attempt `DELETE /api/v1/auth/me` as account A.<br>3. Read the response status.<br>4. In a **fresh session**, read the 3 event rows' `user_id` and the `accounts` row. |
| Expected result | The deletion is refused with an error; account A's row still exists; all 3 events still carry account A's id — the detach was rolled back with the removal, not committed on its own. |
| Status | Not run |

### TC-14-API-11.6 — An event arriving during a deletion cannot break it

| Field | Value |
|---|---|
| Description | The only interesting instant in the deletion is between the detach and the removal. An insert placed anywhere else passes trivially. |
| Preconditions | Account A holding events. A latch installable between the eraser's detaching UPDATE and the account-row `DELETE`. A second session able to insert and commit. |
| Test data | One `analytics_events` row for account A committed from the second session while the deletion is held at the latch. |
| Steps | 1. Install the latch between the detach and the account removal.<br>2. Begin `DELETE /api/v1/auth/me` as account A and hold at the latch.<br>3. From a second session, insert and **commit** an event carrying account A's `user_id`.<br>4. Release the latch and wait for the deletion to answer.<br>5. In a fresh session, read every `analytics_events` row's `user_id` and check each against the `accounts` table. |
| Expected result | The deletion completes successfully (no foreign-key violation, no hang); no `analytics_events` row references an `accounts` id that no longer exists — the late row's `user_id` is `NULL`. |
| Status | Not run |

The only interesting instant in the deletion is between the detach and the removal. An insert
placed anywhere else passes trivially.

### TC-14-API-11.7 — Detaching an account's events costs the same at any volume

| Field | Value |
|---|---|
| Description | Asserted on the statement count across two seeded volumes — a wall-clock bound alone lets a per-row loop pass on a fast machine, inside the product's only irreversible operation. |
| Preconditions | Two accounts seeded, one with 100 events and one with 50 000 events. SQL statement counting enabled. |
| Test data | Volume 100 and volume 50 000; the deletion's stated wall-clock bound. |
| Steps | 1. Delete the 100-event account and record the number of statements issued against `analytics_events` and the elapsed time.<br>2. Delete the 50 000-event account and record the same.<br>3. Compare the two statement counts.<br>4. In a fresh session, count the 50 000 account's events still carrying a `user_id`. |
| Expected result | Both deletions issue the **same** number of statements against `analytics_events` — one set-based `UPDATE`, not 100 versus 50 000; both complete within the stated wall-clock bound; zero of the 50 000 events still carries a `user_id`. |
| Status | Not run |

Asserted on the statement count across two seeded volumes — a wall-clock bound alone lets a
per-row loop pass on a fast machine, inside the product's only irreversible operation.

### TC-14-API-11.8 — An erasure with no account to scope to changes nothing

| Field | Value |
|---|---|
| Description | 11.3 covers a valid account with an empty *result*. This covers an absent *filter* — the one place a missing predicate detaches every event in the table. |
| Preconditions | Several accounts holding events, plus events belonging to no account. Table snapshot taken. |
| Test data | `SqlAlchemyAccountEraser` invoked with account id `None`. |
| Steps | 1. Snapshot every `analytics_events` row including `user_id`.<br>2. Invoke the eraser with a `None` account id.<br>3. Read the eraser's return value / raised exception.<br>4. In a fresh session, snapshot the table again and compare. |
| Expected result | The snapshots are identical — no `user_id` changed; the call does **not** report a successful erasure: it raises or returns a not-found/zero-affected outcome rather than answering as if something had been erased. |
| Status | Not run |

11.3 covers a valid account with an empty *result*. This covers an absent *filter* — the one
place a missing predicate detaches every event in the table.

### TC-14-API-11.9 — Removing an account through the object model detaches its events, never deletes them

| Field | Value |
|---|---|
| Description | 11.4 goes through raw SQL and 11.1 through the eraser, which detaches first and so leaves the relationship empty. A cascade configured to delete children therefore passes both while destroying events on any object-model delete path — the scar this codebase already carries in its account eraser. |
| Preconditions | Account A holding 3 recorded events. Total table row count recorded. |
| Test data | `session.delete(account)` followed by `commit()`, with **no** manual detaching step. |
| Steps | 1. Record the total `analytics_events` row count and the 3 event ids.<br>2. Load account A and call `session.delete(account)`, then commit.<br>3. In a fresh session, select the 3 event rows by id and read their `user_id`.<br>4. Re-count the total rows in `analytics_events`. |
| Expected result | All 3 event rows still exist; every one has `user_id IS NULL`; the total row count is unchanged from step 1 — the ORM relationship did not cascade a `DELETE` onto the children. |
| Status | Not run |

11.4 goes through raw SQL and 11.1 through the eraser, which detaches first and so leaves the
relationship empty. A cascade configured to delete children therefore passes both while
destroying events on any object-model delete path — the scar this codebase already carries in
its account eraser.

### TC-14-API-11.10 — An event reported with a deleted account's token is refused, not silently attributed

| Field | Value |
|---|---|
| Description | Tokens outlive the row. Without this the write is either a swallowed constraint violation — the event lost with no signal — or an anonymous row, and nothing distinguishes them. |
| Preconditions | Account A registered, issued an access token, then deleted itself. The token string retained. |
| Test data | The pre-deletion access token; body `SITE_VISITED`, visitor V1, occurrence key K1. |
| Steps | 1. Register account A, obtain an access token and record it.<br>2. Delete account A.<br>3. `POST` the event carrying the retained token.<br>4. Read the status and body.<br>5. In a fresh session, count rows for visitor V1 and check every row's `user_id` against the `accounts` table. |
| Expected result | `401` with `{"error_code": "UNAUTHORIZED", "message": "A valid access token is required."}`; zero rows for visitor V1 — neither an attributed one nor an anonymous one; no `analytics_events` row references an `accounts` id that no longer exists. |
| Status | Not run |

Tokens outlive the row. Without this the write is either a swallowed constraint violation —
the event lost with no signal — or an anonymous row, and nothing distinguishes them.

---

## 12. The Analytics Path Is Isolated From the Product

### TC-14-API-12.1 — A failing recorder changes no product outcome

| Field | Value |
|---|---|
| Description | The story's headline criterion: a failure anywhere in the analytics path never changes the outcome of a product operation. |
| Preconditions | The emission port fault-injected to raise on every write. Baseline responses for all five operations recorded against a healthy recorder. |
| Test data | Register, verify, sign in, request a generation, save a document — the five emitting operations. |
| Steps | 1. Fault-inject the emission port to reject every write.<br>2. `POST /api/v1/auth/register` and record status and body.<br>3. Confirm the verification code and record status and body.<br>4. Sign in and record status and body.<br>5. Request a generation and record status and body.<br>6. Save a document and record status and body.<br>7. Compare all five against the healthy-recorder baseline. |
| Expected result | All five operations answer the same status code and the same body shape as the baseline; the account exists and is verified, the generation was created, the document content was written — every persisted effect is present. |
| Status | Not run |

### TC-14-API-12.2 — A failing recorder is not silent

| Field | Value |
|---|---|
| Description | Swallowing the failure is required for the user; swallowing it for the operator turns a dead ingest path into a quiet day in the dashboards. |
| Preconditions | Log records capturable. An unverified account per run. |
| Test data | Run 1 with the emission port rejecting; run 2 with it accepting. |
| Steps | 1. Fault-inject the emission port to reject; confirm an account's verification code.<br>2. Capture the emitted log records and inspect their fields.<br>3. Remove the fault; confirm another account's code.<br>4. Capture the log records again. |
| Expected result | Run 1 emits exactly one failure record carrying `event_name` = `REGISTRATION_COMPLETED` and the visitor id as **fields**, never interpolated into the message; run 2 emits **zero** such records. |
| Status | Not run |

### TC-14-API-12.3 — A hanging recorder does not hold the caller

| Field | Value |
|---|---|
| Description | Rejecting fast is the easy failure. A recorder that simply never answers turns the emission into an unbounded wait on the user's own request. |
| Preconditions | The emission port stubbed to never answer. Baseline timings for register and save recorded against a healthy recorder. |
| Test data | The named emission timeout as the abandonment allowance; one registration and one document save. |
| Steps | 1. Stub the emission port to hang indefinitely.<br>2. `POST /api/v1/auth/register` and time the response.<br>3. Save a document and time the response.<br>4. Compare both against the healthy baseline. |
| Expected result | Both operations answer successfully within their healthy baseline plus the named emission timeout, and no longer; neither waits indefinitely; both persisted their own effect. |
| Status | Not run |

### TC-14-API-12.4 — A product operation that rolls back records no event

| Field | Value |
|---|---|
| Description | Emission runs after the caller's transaction commits. An emitter inside the transaction — or before the commit — records work that was undone. |
| Preconditions | Account A holding a document with known content. The save's own commit fault-injected to fail after the point where the event would be emitted. |
| Test data | A save with changed content; the pre-save document content recorded. |
| Steps | 1. Fault-inject the save's commit to fail after the emission point.<br>2. Attempt the save.<br>3. Read the response status.<br>4. In a fresh session, count `DOCUMENT_SAVED` rows for that document.<br>5. In the same read, read the document's stored content. |
| Expected result | The save fails; zero `DOCUMENT_SAVED` rows exist for that document; the stored content is byte-identical to the pre-save content — no partially written document remains. |
| Status | Not run |

### TC-14-API-12.5 — A recorded event is readable by another connection once its call has answered

| Field | Value |
|---|---|
| Description | The emission runs on its own session in a context manager. If that session is never committed — or is committed after the response — Story 15 reads a table that lags the product by an unstated window. |
| Preconditions | An account registered but not confirmed. A second connection ready. |
| Test data | The verification code; a read issued from a second connection immediately after the confirmation answers. |
| Steps | 1. `POST /api/v1/auth/verify` with the account's code.<br>2. The instant the response is received, from a **separate connection**, select `REGISTRATION_COMPLETED` rows for that account.<br>3. Read the result without retrying or waiting. |
| Expected result | The separate connection already returns exactly one `REGISTRATION_COMPLETED` row on the first read — no polling, no sleep, no retry needed. |
| Status | Not run |

### TC-14-API-12.6 — A confirmation that rolls back records no registration

| Field | Value |
|---|---|
| Description | 12.4 catches the same-session commit trap on the save path. Confirmation is the other emitter on a business write, and the one the story names as immediately re-saving the account. |
| Preconditions | An account registered but not confirmed, holding a full technical and attribution context. Its confirmation commit fault-injected to fail after the emission point. |
| Test data | The verification code; the account's ten context values recorded before the attempt. |
| Steps | 1. Fault-inject the confirmation's commit to fail after the emission point.<br>2. `POST /api/v1/auth/verify` with the code.<br>3. Read the response status.<br>4. In a **fresh session**, read the account's verified flag and its ten context values.<br>5. In the same read, count `REGISTRATION_COMPLETED` rows for the account. |
| Expected result | The request fails; the account still reads as unverified; all ten context values are byte-identical to those recorded in the preconditions; zero `REGISTRATION_COMPLETED` rows exist. |
| Status | Not run |

12.4 catches the same-session commit trap on the save path. Confirmation is the other emitter
on a business write, and the one the story names as immediately re-saving the account.

### TC-14-API-12.7 — A recorder that answers just inside its allowance still records

| Field | Value |
|---|---|
| Description | Only the past-deadline side is otherwise tested. An allowance sized too tight, or an abandon firing before the write commits, silently drops events that were about to land. |
| Preconditions | The emission port stubbed to answer at the named emission timeout minus a small margin. Log records capturable. Baseline confirm timing recorded. |
| Test data | An unverified account and its code; the emission stub delayed to just inside the allowance. |
| Steps | 1. Stub the emission to answer at the allowance minus a margin.<br>2. `POST /api/v1/auth/verify` with the code and time the response.<br>3. In a fresh session, count `REGISTRATION_COMPLETED` rows for the account.<br>4. Read the captured log records.<br>5. Compare the response time with the healthy baseline. |
| Expected result | Exactly one `REGISTRATION_COMPLETED` row was recorded; zero swallowed-failure records were emitted; the confirmation answered within its normal budget. |
| Status | Not run |

Only the past-deadline side is otherwise tested. An allowance sized too tight, or an abandon
firing before the write commits, silently drops events that were about to land.

### TC-14-API-12.8 — Every slow hop on one request still fits inside the caller's deadline

| Field | Value |
|---|---|
| Description | Every other case hangs exactly one hop. One registration traverses all three: geolocation, emission and the connection pool. |
| Preconditions | Geolocation dependency stubbed to never answer; emission port stubbed to never answer; connection pool contended to its stated ceiling. |
| Test data | `GEOLOCATION_TIMEOUT_SECONDS=1.5` plus the named emission timeout plus the pool checkout bound; the client's stated deadline of 25 s (`REQUEST_TIMEOUT_MS`). |
| Steps | 1. Install all three conditions at once.<br>2. `POST /api/v1/auth/register` and time the response.<br>3. Compare the elapsed time with the register endpoint's normal budget plus the three named allowances, and with 25 s.<br>4. Repeat with the caller's deadline set below the combined worst case and abandon the request at that deadline.<br>5. After abandoning, in a fresh session look for the account row and any `analytics_events` row for that visitor.<br>6. Inspect for a geolocation lookup or an emission still running. |
| Expected result | Step 2 answers within the normal budget plus the three named allowances, and inside 25 s; after step 4 no `accounts` row and no `analytics_events` row was committed after the caller stopped waiting; no lookup task and no emission task is still running past that point. |
| Status | Not run |

Every other case hangs exactly one hop. One registration traverses all three.

### TC-14-API-12.9 — A reported event is readable by another connection once its call has answered

| Field | Value |
|---|---|
| Description | `endpoints.md` chose `204` over `202` precisely on this claim, and recorded that `202` «would make the read-after-write guard unassertable». Without it nothing goes red if the ingest write becomes a background task. |
| Preconditions | No rows for visitor V1. A second connection ready. |
| Test data | One `SITE_VISITED` for visitor V1 with occurrence key K1, sent with no token. |
| Steps | 1. `POST` the event.<br>2. The instant the `204` is received, from a **separate connection**, select rows for visitor V1 with key K1.<br>3. Read the result without retrying or waiting. |
| Expected result | The response is `204`; the separate connection already returns exactly one row on the first read — no polling, no sleep, no retry needed. |
| Status | Not run |

`endpoints.md` chose 204 over 202 precisely on this claim, and recorded that 202 «would make
the read-after-write guard unassertable». That guard is this case; without it nothing
goes red if the ingest write becomes a background task.

### TC-14-API-12.10 — The two extended auth routes answer exactly as they did before this story

| Field | Value |
|---|---|
| Description | The one case that owns the Governing Decision as a whole rather than one clause of it. The attribution cases each assert their own outcome; nothing else asserts that the *set* of outcomes did not grow. |
| Preconditions | `07-authorization/tests/01_API_Tests.md` §1–2 and story 16's handshake scenarios available **unmodified** as the reference set of what «today» means. |
| Test data | Each reference request replayed twice: once with no `utm_*`, once carrying `utm_campaign` of 201 code points after NFC (a value that cannot be stored). |
| Steps | 1. Replay every accepted request from the reference set against the story's implementation with no `utm_*`; record status and body shape.<br>2. Replay every refused request from the reference set with no `utm_*`; record status and `error_code`.<br>3. Repeat steps 1–2 with the unstorable `utm_campaign` attached.<br>4. Collect the full set of status codes each route answered across all four passes. |
| Expected result | Every accepted request is still accepted with the same status and the same body shape in all passes; every refused request is still refused with the same status and the same `error_code`; `POST /auth/register` answered no status code outside its pre-story set and `GET /auth/oauth/{provider}/start` answered only `302`, `404` and `500` — in particular no `400` anywhere; the reference scenarios pass unmodified. |
| Status | Not run |

The one case that owns the Governing Decision as a whole rather than one clause of it. The
attribution cases each assert their own outcome; nothing else asserts that the *set* of
outcomes did not grow. `07-authorization/tests/01_API_Tests.md` §1–2 and story 16's handshake
scenarios are the reference for what «today» means, and they must pass unmodified.

### TC-14-API-12.11 — A missing geolocation configuration is not a failed boot

| Field | Value |
|---|---|
| Description | An analytics dependency that can refuse to boot the product is the deployment-level form of the defect 7.5a guards at the request level. The disabled signal is what keeps «unset» loud — it must be distinguishable from both a resolution failure (Infra 2.2) and a legitimate NULL. |
| Preconditions | `GEOLOCATION_API_URL` unset (its documented default). Startup log records capturable. |
| Test data | Environment with `GEOLOCATION_API_URL` and `GEOLOCATION_API_TOKEN` absent; one unregistered email. |
| Steps | 1. Start the application with `GEOLOCATION_API_URL` unset.<br>2. Confirm the process is up and the health endpoint answers.<br>3. Read the captured startup log records.<br>4. `POST /api/v1/auth/register`.<br>5. In a fresh session, read the account's country column.<br>6. Read the captured records for any resolution-failure signal. |
| Expected result | The application boots and answers health checks; exactly one startup record names country resolution as **disabled**; registration succeeds with its normal status; the account's country is `NULL`; **no** resolution-failure record was emitted — none was attempted, and the disabled record is distinguishable from a failure record. |
| Status | Not run |

An analytics dependency that can refuse to boot the product is the deployment-level form of
the defect 7.5a guards at the request level. The disabled signal is what keeps «unset» loud —
it must be distinguishable from both a resolution failure (Infra 2.2) and a legitimate NULL.

---

## 13. Disclosure

### TC-14-API-13.1 — Personal data lives on the account and nowhere else

| Field | Value |
|---|---|
| Description | An account's personal data must be in exactly one place, so that deleting the account removes it. A copy in an event payload, a log line or a rate-limit row survives the deletion forever. |
| Preconditions | Account A registered from a distinctive address with a distinctive attribution value, then driven through all eight emissions. Log records capturable. |
| Test data | Distinctive IP `198.51.100.77`; distinctive `utm_content` sentinel `SENTINEL-7Q4Z-CONTENT`; the account's email. |
| Steps | 1. Register account A from `198.51.100.77` carrying the sentinel `utm_content`, then run all eight emissions.<br>2. Text-scan every `analytics_events` row for that account — `payload` included — for the IP, the sentinel and the email.<br>3. Text-scan every response body the visitor received for the same three values.<br>4. Text-scan every captured log record for the same three values.<br>5. Text-scan the `oauth_rate_limits` rows for the same three values. |
| Expected result | The IP, the sentinel `SENTINEL-7Q4Z-CONTENT` and the email appear **only** on the `accounts` row; zero occurrences in any `analytics_events` row, in any response body, in any log record and in any `oauth_rate_limits` row. |
| Status | Not run |

### TC-14-API-13.2 — A refusal never echoes what was rejected

| Field | Value |
|---|---|
| Description | The events endpoint is anonymous and its errors reach anyone. An echoing message turns a validation error into a reflection primitive and leaks internal detail to an unauthenticated caller. |
| Preconditions | Events route reachable. |
| Test data | (a) `event_name` = `<script>alert(1)</script>`; (b) `visitor_id` = `7b1f2c40-6d83-4a19-9e52-0c4a7d18b3f6?admin=1`. |
| Steps | 1. `POST` the event with the markup `event_name`.<br>2. `POST` the event with the query-fragment `visitor_id`.<br>3. Read both statuses and full response bodies.<br>4. Search each body for the submitted string and for any internal detail (table name, column name, SQL text, file path, stack frame, `correlation_id`). |
| Expected result | (a) answers `400 UNKNOWN_EVENT_NAME`, (b) answers `400 INVALID_VISITOR_ID`; both bodies carry exactly the keys `error_code` and `message`; neither contains `<script>`, `alert(1)` or `?admin=1`; neither names `analytics_events`, a column, a SQL fragment, a file path or a stack frame. |
| Status | Not run |

### TC-14-API-13.3 — A stored event name this version does not define is preserved, and the read survives

| Field | Value |
|---|---|
| Description | Story 15 is handed this as a written guarantee. Every read in this suite goes through a mapper that has never met an out-of-set value. |
| Preconditions | Direct database access. Visitor V1 holding two ordinary events. |
| Test data | An `analytics_events` row inserted directly with `event_name` = `FUTURE_EVENT_X` (outside the domain enumeration), sequenced between the two ordinary events for V1. |
| Steps | 1. Record one ordinary event for V1.<br>2. Insert the `FUTURE_EVENT_X` row directly, after it in `sequence`.<br>3. Record a second ordinary event for V1.<br>4. In a fresh session, read V1's events ordered by `sequence` through the repository. |
| Expected result | The read returns all three rows in sequence order without raising; the middle row's `event_name` comes back as exactly `FUTURE_EVENT_X`; it is **not** mapped to `SITE_VISITED` or to any other member of the known set, and is not dropped. |
| Status | Not run |

Story 15 is handed this as a written guarantee. Every read in this suite goes through a
mapper that has never met an out-of-set value.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `reports a site visit` / `opening the editor` | `POST /api/v1/analytics/events` with `event_name`, `visitor_id`, `occurrence_key` |
| `the same occurrence again` | Identical `occurrence_key` on a second request |
| `another instance` | A second session/process sharing only the database — the start's process state gone |
| `at once, interleaved at the point where…` | Latch between the read and the write, as `test_document_storage_concurrency.py` does — never two threads and hope |
| `a fresh read` | Re-read through a **new** session — never the same `AsyncSession` |
| `the stored event has no account attached` | `analytics_events.user_id IS NULL` |
| `resolve to one stored visitor` | One distinct value in the `uuid`-typed `visitor_id` column |
| `the declared type is the native identifier type` | `information_schema.data_type` = `uuid`, the assertion shape the repo already uses |
| `its braced form` / `its urn form` | `{…}` and `urn:uuid:…` spellings of one UUID |
| `characters outside the basic plane` | Astral-plane code points — N code points, 4N bytes, the fixture that separates the two units |
| `the canonical error shape` | `{error_code, message}` per `api-specs/README.md` |
| `the configured event rate limit` | `ANALYTICS_EVENT_RATE_LIMIT=120` / `ANALYTICS_EVENT_RATE_WINDOW_SECONDS=60`, fixed-window bucket keyed on `client_source()` |
| `the rate limiter's own store is unavailable` | Fault-inject the rate-limit adapter |
| `the clock fixed one tick before the window ends` | Injected `Clock` stub at the rollover boundary — never a real-time wait |
| `a distinguishable rate-limited signal` | A structured log record distinct from the swallowed-emission-failure record |
| `a frozen first-touch attribution set` | The five `utm_*` in the register body / `oauth/start` query |
| `succeeds exactly as it does for a visitor carrying no attribution at all` | Same status, same response body shape and same `error_code` set as the identical request with the `utm_*` omitted — asserted against that request, not against a literal |
| `an undecodable attribution value` | A percent-encoded cp1251 byte sequence that is not valid UTF-8 |
| `the discard is reported once` | One structured log record naming the field and the reason, carrying no value — distinct from the swallowed-emission-failure record |
| `the set of requests … accepts and refuses today` | The scenarios of `07-authorization/tests/01_API_Tests.md` §1–2 and story 16's handshake scenarios, run unmodified |
| `the geolocation configuration absent` | `GEOLOCATION_API_URL` unset — the default, which disables resolution |
| `composed form` / `decomposed form` | NFC and NFD spellings of one string |
| `a tag with no stated priority` | `Accept-Language: en,ru;q=0.9` — absent `q` means 1.0 |
| `explicitly marked unacceptable` | `q=0`, which must never be selected |
| `a Turkish locale` | The locale the repo already parameterizes in `test_password_normalization_order.py` |
| `the generation remembers the requesting visitor` | `generations.visitor_id` column written by `RequestGeneration` |
| `an instance other than the one that received the request` | Execute `GenerateDocument` from a separate session/process |
| `two workers at once` | Interleave at the CAS window |
| `the periodic sweep` | `RequeueStaleGenerations` + `run_stale_generation_sweep` |
| `one retry key` | Repeated `Idempotency-Key` on `POST /generations/{id}/retry` |
| `answered as already applied` | The `_explain_miss` 200 branch of `SaveDocument` |
| `clocks disagree` | Two `Clock` stubs with deliberately skewed readings |
| `read in order` | Ordered by the `sequence` column |
| `a non-UTC zone` | Process `TZ` and session `TimeZone` both set away from UTC |
| `removed directly, without the eraser` | Raw `DELETE FROM accounts` — the rolling-deploy N-1 path |
| `removed through the object model` | `session.delete(account)` — the ORM relationship path, no manual detach |
| `one set-based update` | Statement count captured across two seeded volumes, asserted equal |
| `invoked with no account identified` | Eraser called with a `None` account id |
| `the event recorder rejects every write` | Fault-inject the emission port |
| `the recorder's abandonment allowance` | The named emission timeout from the spec |
| `the client's stated deadline` | The frontend's 25 s `REQUEST_TIMEOUT_MS` |
| `everything the system reported` | Captured log records, asserted on a fixed redaction token |
| `the abuse counter rows` | `oauth_rate_limits`, which this story keys on every anonymous page view |
| `a name outside the reader's known set` | Direct insert of an `event_name` the domain enumeration does not contain |
