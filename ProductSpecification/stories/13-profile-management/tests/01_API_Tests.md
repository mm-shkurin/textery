> **Implementation Order**: sequential TDD — token guards → read the profile → rename
> validation → rename happy path & persistence → write-path integrity (server-owned fields,
> presence, re-run safety) → transport boundary & disclosure.

# Profile management — API Tests

Endpoints: `GET /api/v1/auth/me` (read), `PATCH /api/v1/auth/me` (write). Contract:
`endpoints.md`, `api-specs/auth_me_get.yaml`, `api-specs/auth_me_update.yaml`.

> **Persistence assertions re-read in a separate session.** `create_session_factory` sets
> `expire_on_commit=False` and `find_by_id` is `session.get`, so a same-session re-read is
> served from the identity map and passes on a row Postgres never received. Wherever a
> scenario says «a fresh read of the stored profile», that is the requirement, not a phrasing
> choice — see `13_ProfileManagement_Notes.md` § Technical Warnings.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.profile@textery.test` / `Qa!Profile2026`, id `3d9f1a26-7c48-4b1e-9a03-51e6b8d47f20`, `name = "Мария Соколова"`, `created_at = 2026-03-14T09:26:53Z` |
| Account B (a second account) | `qa.stranger13@textery.test` / `Qa!Stranger2026`, id `8b21c07e-4f5a-4d92-8c31-a7d0e2f96415`, `name = "Иван Петров"` |
| Account C (never named) | `qa.noname@textery.test` / `Qa!NoName2026`, id `c04b7e91-2a63-4f18-9d75-6be3c1a80f52`, `name = null` |
| Access token | `Authorization: Bearer <access token of account A>` (15-minute TTL, `type` claim `access`) |
| Error body shape | `{"error_code": "<CODE>", "message": "<generic text>"}` — the canonical envelope from `exception_handlers.py` |
| 401 body | `{"error_code": "UNAUTHORIZED", "message": "A valid access token is required."}` |
| 500 body | `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}` |
| Raw input cap | 256 code points, checked before trim/NFC → `400 NAME_INPUT_TOO_LARGE` |
| Name bound | 60 code points after trim + NFC → `400 INVALID_NAME` |
| Request body cap | 2 MiB in the app → `413 REQUEST_BODY_TOO_LARGE`; nginx `client_max_body_size` 4 MiB above it |
| Astral fixture | `"😀"` (U+1F600) — 1 code point, 2 UTF-16 units, 4 UTF-8 bytes |
| NFD fixture | `"е́"` repeated 60× — 120 raw code points, 60 after NFC |

---

## 1. Token Guards

Not the generic unauthenticated case — these are the three refusals this story's own token
handling can get wrong, plus the boundary that proves the expiry check is not inverted.

### TC-13-API-1.1 — A refresh token is refused on both routes

| Field | Value |
|---|---|
| Description | A refresh token is a valid, unexpired, correctly signed JWT. If the route checks only the signature, it silently accepts a long-lived credential the access path was designed to keep out. |
| Preconditions | Account A signed in via `POST /api/v1/auth/login`; the response's `refresh_token` captured; account A's stored `name` is `null`. |
| Test data | `Authorization: Bearer <refresh_token of account A>`; PATCH body `{"name": "Мария Соколова"}` |
| Steps | 1. `GET /api/v1/auth/me` with the refresh token.<br>2. `PATCH /api/v1/auth/me` with the refresh token and body `{"name": "Мария Соколова"}`.<br>3. Re-read account A's row in a new session. |
| Expected result | Both answer `401 Unauthorized` with body `{"error_code": "UNAUTHORIZED", "message": "A valid access token is required."}`; step 3 shows `name` still `NULL` — nothing was stored. |
| Status | Not run |

### TC-13-API-1.2 — A token whose type claim is absent or unknown is refused

| Field | Value |
|---|---|
| Description | An absent or unrecognized `type` claim must fail closed. A check written as `type != "refresh"` accepts both of these. |
| Preconditions | Account A exists; two tokens are minted with the app's own signing key and a valid `exp`. |
| Test data | Token X: claims `{sub: <A id>, exp: <now+15m>}` with **no** `type` key. Token Y: same claims plus `type: "session"`. |
| Steps | 1. `GET /api/v1/auth/me` with token X.<br>2. `GET /api/v1/auth/me` with token Y. |
| Expected result | Both answer `401 Unauthorized` with the `UNAUTHORIZED` body; no profile field (`email`, `name`, `created_at`) appears in either response. |
| Status | Not run |

### TC-13-API-1.3 — A token one second past expiry is refused, and one second before it is served

| Field | Value |
|---|---|
| Description | Pins the direction of the expiry comparison. An inverted `<`/`>` passes any test that only checks a long-expired token. |
| Preconditions | Account A exists and is verified. |
| Test data | Token E1: `exp = now − 1s`. Token E2: `exp = now + 1s`, `type: "access"`. |
| Steps | 1. `GET /api/v1/auth/me` with token E1.<br>2. `GET /api/v1/auth/me` with token E2 immediately. |
| Expected result | Step 1: `401 Unauthorized`, `UNAUTHORIZED` body. Step 2: `200 OK` with body `{"email": "qa.profile@textery.test", "name": "Мария Соколова", "created_at": "2026-03-14T09:26:53Z"}`. |
| Status | Not run |

### TC-13-API-1.4 — A valid token whose account no longer exists is refused as unauthorized

| Field | Value |
|---|---|
| Description | A deleted account's still-valid token must not be distinguishable from a forged one — a `404` or a different message would confirm the account once existed. |
| Preconditions | Account A signed in and its access token captured; then account A's row is deleted directly from `accounts`. |
| Test data | Account A's captured access token; a forged token signed with a wrong key. |
| Steps | 1. `GET /api/v1/auth/me` with account A's captured token.<br>2. `GET /api/v1/auth/me` with the forged token.<br>3. Compare the two responses byte for byte, `Date` aside. |
| Expected result | Both answer `401 Unauthorized` with `{"error_code": "UNAUTHORIZED", "message": "A valid access token is required."}`; status line, headers and body are identical between the two. Never `404`, never `403`. |
| Status | Not run |

---

## 2. Read the Profile

### TC-13-API-2.1 — The profile reports the caller's own email, name and registration date

| Field | Value |
|---|---|
| Description | The primary read contract, and the replacement for client-side JWT decoding in the header. |
| Preconditions | Account A registered, verified, `name` set to `Мария Соколова`, `created_at` stored as `2026-03-14 09:26:53+00`. |
| Test data | Account A's access token. |
| Steps | 1. `GET /api/v1/auth/me` with account A's Bearer token. |
| Expected result | `200 OK`; `Content-Type: application/json`; body exactly `{"email": "qa.profile@textery.test", "name": "Мария Соколова", "created_at": "2026-03-14T09:26:53Z"}`. |
| Status | Not run |

### TC-13-API-2.2 — An account that never set a name reports the name as present and null

| Field | Value |
|---|---|
| Description | The client's email fallback is keyed on reading an explicit `null`. An omitted key breaks it silently. |
| Preconditions | Account C registered and verified, never renamed. |
| Test data | Account C's access token. |
| Steps | 1. `GET /api/v1/auth/me` with account C's token.<br>2. Inspect the raw JSON text for the `name` key. |
| Expected result | `200 OK`; the raw body contains `"name": null`; `"name"` is present as a key (`"name" in json` is true); the value is `null`, not `""` and not absent. |
| Status | Not run |

### TC-13-API-2.3 — The profile carries no verification status

| Field | Value |
|---|---|
| Description | `is_verified` would be `true` on every response this route can produce, and an `id` would give a caller an account identifier it has no use for. Exactly three keys. |
| Preconditions | Account A signed in. |
| Test data | Account A's access token. |
| Steps | 1. `GET /api/v1/auth/me`.<br>2. List the top-level keys of the response body. |
| Expected result | `200 OK`; the key set is exactly `{"email", "name", "created_at"}` — no `is_verified`, no `id`, no `password_hash`, no `failed_attempt_count`. |
| Status | Not run |

### TC-13-API-2.4 — The registration date is a UTC instant regardless of the stored offset

| Field | Value |
|---|---|
| Description | A row written with a non-UTC offset must be converted, not echoed — every other timestamp on this wire is `Z`-suffixed UTC. |
| Preconditions | Account D exists with `created_at` stored as `2026-03-14 12:26:53+03:00`. |
| Test data | Account D `qa.offset@textery.test`, stored `2026-03-14T12:26:53+03:00`. |
| Steps | 1. `GET /api/v1/auth/me` with account D's token. |
| Expected result | `200 OK`; `created_at` is exactly `"2026-03-14T09:26:53Z"` — the same instant, `Z`-suffixed, matching `ProjectItemDto._as_utc`. Never `"…+03:00"`. |
| Status | Not run |

### TC-13-API-2.5 — A registration instant with no timezone is a server fault, named

| Field | Value |
|---|---|
| Description | `astimezone(UTC)` does not raise on a naive datetime — it reads it as host-local, which is silently correct in a UTC container and silently shifted on a developer machine. |
| Preconditions | Account E exists with `created_at` stored naive (no tzinfo), value `2026-03-14 09:26:53`. |
| Test data | Account E `qa.naive@textery.test`. |
| Steps | 1. `GET /api/v1/auth/me` with account E's token.<br>2. Read the captured application log for that request. |
| Expected result | `500 Internal Server Error` with body `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}`; the log record names `created_at` as the failing field. No `200` carrying a shifted instant. |
| Status | Not run |

### TC-13-API-2.6 — The registration instant crosses the wire at full precision

| Field | Value |
|---|---|
| Description | TC-13-API-2.4 is satisfied by a serializer that truncates to whole seconds — "the equivalent UTC instant" says nothing about precision. |
| Preconditions | Account F exists with `created_at = 2026-03-14 09:26:53.472918+00`. |
| Test data | Account F `qa.fraction@textery.test`, stored fraction `.472918`. |
| Steps | 1. `GET /api/v1/auth/me` with account F's token. |
| Expected result | `200 OK`; `created_at` is `"2026-03-14T09:26:53.472918Z"` — the fraction is present and equal to the stored one, not truncated to `…:53Z`. |
| Status | Not run |
| Note | Written as counter-pressure to TC-13-API-2.4, which a truncating serializer passes. |

### TC-13-API-2.7 — The registration instant does not follow the server's own timezone

| Field | Value |
|---|---|
| Description | The container and CI are UTC by accident, not by contract; a code path reading local system time is invisible until the first non-UTC host. |
| Preconditions | The application process started with `TZ=Asia/Yekaterinburg` (UTC+5); account A exists with `created_at = 2026-03-14 09:26:53+00`. |
| Test data | `TZ=Asia/Yekaterinburg` vs `TZ=UTC`; account A's token. |
| Steps | 1. Start the app with `TZ=UTC`, `GET /api/v1/auth/me`, record `created_at`.<br>2. Restart with `TZ=Asia/Yekaterinburg`, `GET /api/v1/auth/me` again. |
| Expected result | Both return `"2026-03-14T09:26:53Z"` — identical strings. Never `"2026-03-14T14:26:53Z"` under the shifted process. |
| Status | Not run |

### TC-13-API-2.8 — Both routes forbid caching

| Field | Value |
|---|---|
| Description | The body carries the account's email; a shared cache must never store it. The header is applied at the route, before the outcome is known, so it is present on refusals too. |
| Preconditions | Account A signed in. |
| Test data | Account A's token; PATCH body `{"name": "Мария Соколова"}`; also a request with no `Authorization` header. |
| Steps | 1. `GET /api/v1/auth/me` and read `Cache-Control`.<br>2. `PATCH /api/v1/auth/me` with `{"name": "Мария Соколова"}` and read `Cache-Control`.<br>3. `GET /api/v1/auth/me` with no token and read `Cache-Control`. |
| Expected result | All three responses carry `Cache-Control: no-store` — on the two `200`s and on the `401`. |
| Status | Not run |

---

## 3. Rename — Validation

### TC-13-API-3.1 — A raw value over the input cap is refused before normalization, with its own code

| Field | Value |
|---|---|
| Description | The cheap gate must run first, so a long or adversarial input never reaches trim + NFC. A single shared code would make it impossible to prove the gate ran at all. |
| Preconditions | Account A signed in with stored `name = "Мария Соколова"`. |
| Test data | `{"name": "а" × 300}` (300 code points, over the 256 raw cap). |
| Steps | 1. `PATCH /api/v1/auth/me` with `{"name": "ааа…"}` (300 `а`).<br>2. Re-read account A's row in a new session. |
| Expected result | `400 Bad Request`, body `{"error_code": "NAME_INPUT_TOO_LARGE", "message": …}` — `NAME_INPUT_TOO_LARGE`, never `INVALID_NAME`; step 2 shows `name` still `Мария Соколова`. |
| Status | Not run |

### TC-13-API-3.2 — The raw cap accepts its last legal value and refuses the first illegal one

| Field | Value |
|---|---|
| Description | Pins the exact edge, 256 accept / 257 refuse, so an off-by-one in either direction goes red. |
| Preconditions | Account A signed in. Note the 256-code-point value is under the raw cap but over the 60 bound, so it is refused as `INVALID_NAME` after normalization. |
| Test data | `"а" × 256` and `"а" × 257`. |
| Steps | 1. `PATCH /api/v1/auth/me` with `{"name": "а" × 256}`.<br>2. `PATCH /api/v1/auth/me` with `{"name": "а" × 257}`. |
| Expected result | Step 1 passes the raw gate: `400 INVALID_NAME` (the normalized bound), never `NAME_INPUT_TOO_LARGE`. Step 2: `400 NAME_INPUT_TOO_LARGE`. |
| Status | Not run |

### TC-13-API-3.2a — The raw cap counts code points, not units or bytes

| Field | Value |
|---|---|
| Description | A raw gate written over byte length or UTF-16 units refuses this value at the cheap gate, and TC-13-API-3.1 and 3.2 both stay green — they never vary the unit. |
| Preconditions | Account A signed in. |
| Test data | `{"name": "😀" × 256}` — 256 code points, 512 UTF-16 units, 1024 UTF-8 bytes. |
| Steps | 1. `PATCH /api/v1/auth/me` with `{"name": "😀" × 256}`. |
| Expected result | `400 Bad Request` with `error_code` `INVALID_NAME` (the normalized 60 bound), **not** `NAME_INPUT_TOO_LARGE` — the raw gate must let 256 code points through regardless of their byte or unit width. |
| Status | Not run |

### TC-13-API-3.3 — The name bound is applied after normalization, and counts code points

| Field | Value |
|---|---|
| Description | Pins the exact edge, 60 accept / 61 refuse, on the post-normalization bound. |
| Preconditions | Account A signed in. |
| Test data | `"я" × 60` and `"я" × 61`. |
| Steps | 1. `PATCH /api/v1/auth/me` with `{"name": "я" × 60}`.<br>2. `PATCH /api/v1/auth/me` with `{"name": "я" × 61}`. |
| Expected result | Step 1: `200 OK`, response `name` is the 60-character value. Step 2: `400 Bad Request`, `{"error_code": "INVALID_NAME", …}`. |
| Status | Not run |

### TC-13-API-3.4 — A composed name is measured after normalization, not before

| Field | Value |
|---|---|
| Description | An NFD fixture of 60 NFC characters is 120 raw code points; a bound applied before normalization refuses a name the contract accepts. |
| Preconditions | Account A signed in. |
| Test data | `{"name": "е́" × 60}` — 120 raw code points, 60 after NFC (`ё`-like `é` sequence). |
| Steps | 1. `PATCH /api/v1/auth/me` with the 120-code-point NFD value.<br>2. Re-read account A's row in a new session. |
| Expected result | Step 1: `200 OK`. Step 2: the stored value is canonically equivalent to what was sent (`unicodedata.normalize("NFC", sent) == stored`), 60 code points long. |
| Status | Not run |

### TC-13-API-3.5 — A name of exactly the bound in astral characters round-trips unchanged

| Field | Value |
|---|---|
| Description | 60 astral characters are 120 UTF-16 units; a bound counted in units refuses them, and a storage or serialization path counted in units mangles them. |
| Preconditions | Account A signed in. |
| Test data | `{"name": "😀" × 60}` — 60 code points, 120 UTF-16 units, 240 UTF-8 bytes. |
| Steps | 1. `PATCH /api/v1/auth/me` with `{"name": "😀" × 60}`.<br>2. Re-read account A's row in a new session. |
| Expected result | Step 1: `200 OK`, response `name` equals the sent value. Step 2: the stored value equals `"😀" × 60` character for character — no U+FFFD, no lone surrogate, no truncation. |
| Status | Not run |

### TC-13-API-3.4a — Normalization actually runs, and the response is the normalized value

| Field | Value |
|---|---|
| Description | TC-13-API-3.4 asserts canonical equivalence, which an implementation that stores the raw bytes and never normalizes satisfies exactly — and then two users who typed the same name are stored differently, and the client's dirty flag never clears after such a save. |
| Preconditions | Account A and account B both signed in. |
| Test data | Account A sends `"Мари́я"` (NFD, 6 code points). Account B sends `"Ма́рия"` in NFC form (5 code points). |
| Steps | 1. Account A: `PATCH /api/v1/auth/me` with the NFD value; record the response `name`.<br>2. Account B: `PATCH /api/v1/auth/me` with the NFC value.<br>3. Re-read both rows in a new session and compare the stored strings byte for byte. |
| Expected result | Both `200 OK`; the two stored values are byte-identical; account A's response body carries the **composed** form (5 code points), not the 6-code-point bytes it sent. |
| Status | Not run |

### TC-13-API-3.6 — Control and surrogate code points are refused, not stripped

| Field | Value |
|---|---|
| Description | U+0000 passes a whitespace+`Cf` filter, is under both bounds, reaches Postgres and is rejected by the `text` type — turning a documented `400` into a `500`. |
| Preconditions | Account A signed in with a stored name. |
| Test data | `{"name": " "}` and `{"name": "Мария\ud800"}` (unpaired high surrogate, sent as `\ud800` in the JSON escape). |
| Steps | 1. `PATCH /api/v1/auth/me` with `{"name": " "}`.<br>2. `PATCH /api/v1/auth/me` with `{"name": "Мария\ud800"}`.<br>3. Re-read account A's row. |
| Expected result | Both answer `400 Bad Request` with `{"error_code": "INVALID_NAME", …}` — never `500`, never `200` with the character stripped; step 3 shows the name unchanged. |
| Status | Not run |

### TC-13-API-3.6a — A name carrying storage metacharacters is stored as written

| Field | Value |
|---|---|
| Description | The hazard scan dismissed injection because the ORM parameterizes — that is the mitigation, not a guard. This is the round-trip proof for the storage sink, which the astral and decomposed fixtures do not give. |
| Preconditions | Accounts A and B both exist with names set. |
| Test data | `{"name": "О'Ко\\ннор 100%_а'; DROP TABLE accounts;--"}` |
| Steps | 1. `PATCH /api/v1/auth/me` as account A with that value.<br>2. Re-read account A's row in a new session.<br>3. Re-read account B's row and count rows in `accounts`. |
| Expected result | Step 1: `200 OK`. Step 2: the stored `name` equals `О'Ко\ннор 100%_а'; DROP TABLE accounts;--` character for character — quote, backslash, `%` and `_` unescaped and unstripped. Step 3: account B's `name` and `email` unchanged and the `accounts` row count unchanged. |
| Status | Not run |

### TC-13-API-3.7 — A non-string name is refused by this contract's own failure shape

| Field | Value |
|---|---|
| Description | FastAPI's `RequestValidationError` answers `422` in a `{"detail": …}` shape that **echoes the rejected input back**. The value must reach the domain instead. |
| Preconditions | Account A signed in. |
| Test data | `{"name": 123}`, `{"name": []}`, `{"name": {}}` |
| Steps | 1. `PATCH /api/v1/auth/me` with `{"name": 123}`.<br>2. Repeat with `{"name": []}`.<br>3. Repeat with `{"name": {}}`. |
| Expected result | Each answers `400 Bad Request` with exactly `{"error_code": "INVALID_NAME", "message": …}` — two keys, never `422`, never a `detail` key; no body contains `123`, `[]` or `{}` echoed back. |
| Status | Not run |

### TC-13-API-3.8 — A body that is not JSON is the one shape this contract does not own

| Field | Value |
|---|---|
| Description | Pinned deliberately: closing this means an application-wide validation handler that changes the failure contract of all nineteen existing endpoints (`endpoints.md`). |
| Preconditions | Account A signed in. |
| Test data | Raw body `{` with `Content-Type: application/json`; and body `hello` with `Content-Type: text/plain`. |
| Steps | 1. `PATCH /api/v1/auth/me` with the raw body `{`.<br>2. Repeat with `Content-Type: text/plain` and body `hello`. |
| Expected result | Each is refused with FastAPI's own `422 Unprocessable Entity` carrying a `detail` array — **not** `{"error_code", "message"}`. The divergence is asserted, not fixed. |
| Status | Not run |

---

## 4. Rename — Clearing and the Tri-State

### TC-13-API-4.1 — A blank name clears the stored name

| Field | Value |
|---|---|
| Description | A blank string clears exactly as `null` does; persisting `""` would defeat the NULL-keyed email fallback. |
| Preconditions | Account A signed in with stored `name = "Мария Соколова"`. |
| Test data | `{"name": ""}` and `{"name": "   "}` (three spaces). |
| Steps | 1. `PATCH /api/v1/auth/me` with `{"name": ""}`.<br>2. Re-read account A's row in a new session.<br>3. Re-set the name, then `PATCH` with `{"name": "   "}` and re-read. |
| Expected result | Both PATCHes answer `200 OK` with `"name": null` in the body; both fresh reads show the column is `NULL`, never `''`. |
| Status | Not run |

### TC-13-API-4.2 — An omitted name leaves the stored name untouched

| Field | Value |
|---|---|
| Description | The presence half of the tri-state. `name: str | None = None` makes omitted and explicit-null indistinguishable, and the moment this route grows a second field, an omitted key becomes destructive. |
| Preconditions | Account A signed in with stored `name = "Мария Соколова"`. |
| Test data | Body `{}` |
| Steps | 1. `PATCH /api/v1/auth/me` with body `{}`.<br>2. Re-read account A's row in a new session. |
| Expected result | `200 OK` with `"name": "Мария Соколова"` in the response; the fresh read still shows `Мария Соколова`. Not `null`. |
| Status | Not run |

### TC-13-API-4.3 — An explicit null name clears the stored name

| Field | Value |
|---|---|
| Description | The clearing half of the tri-state, distinguished from omission by TC-13-API-4.2. |
| Preconditions | Account A signed in with stored `name = "Мария Соколова"`. |
| Test data | Body `{"name": null}` |
| Steps | 1. `PATCH /api/v1/auth/me` with `{"name": null}`.<br>2. Re-read account A's row in a new session. |
| Expected result | `200 OK` with `"name": null` in the response; the fresh read shows the column is `NULL`. |
| Status | Not run |

### TC-13-API-4.4 — A name of only invisible characters clears rather than persisting

| Field | Value |
|---|---|
| Description | A set-but-unrenderable name blanks the identity row and truncates the `aria-label` to «Меню профиля: » — worse than no name, because the contract claims it cannot happen. |
| Preconditions | Account A signed in with stored `name = "Мария Соколова"`, re-set before each sub-step. |
| Test data | `{"name": "​﻿ "}`; `{"name": "ㅤ"}` (Hangul filler, `Lo`); `{"name": "⠀"}` (Braille blank, `So`). |
| Steps | 1. `PATCH /api/v1/auth/me` with the zero-width/NBSP value; re-read the row in a new session.<br>2. Re-set the name, `PATCH` with `"ㅤ"`; re-read.<br>3. Re-set the name, `PATCH` with `"⠀"`; re-read. |
| Expected result | Each PATCH answers `200 OK` with `"name": null`; after each, the fresh read shows the column is `NULL` — none of the three values is persisted. |
| Status | Not run |

### TC-13-API-4.5 — A cleared account and a never-named account are indistinguishable at rest

| Field | Value |
|---|---|
| Description | "No name" must have exactly one stored representation, or the email fallback fires for one account and not the other. |
| Preconditions | Account A had `name = "Мария Соколова"` and cleared it; account C registered and never named. |
| Test data | Accounts A and C. |
| Steps | 1. `PATCH /api/v1/auth/me` as account A with `{"name": null}`.<br>2. Select `name` for both accounts directly from `accounts` in a new session.<br>3. `GET /api/v1/auth/me` as each. |
| Expected result | Both stored values are `NULL` (`name IS NULL` true for both); neither is `''`; both `GET`s return `"name": null`. |
| Status | Not run |

---

## 5. Rename — Persistence Integrity

### TC-13-API-5.1 — A rename leaves the rest of the account row untouched

| Field | Value |
|---|---|
| Description | The rename runs through `save()`, whose update branch copies `email`, `password_hash` and `is_verified` from the loaded snapshot — a full-row rewrite would clobber out-of-band writes. |
| Preconditions | Account A verified, `failed_attempt_count = 2`, `created_at = 2026-03-14T09:26:53Z`, `password_hash` recorded before the call. |
| Test data | `{"name": "Мария Соколова"}` |
| Steps | 1. Select `email, name, is_verified, created_at, failed_attempt_count, password_hash` for account A and record them.<br>2. `PATCH /api/v1/auth/me` with `{"name": "Мария Соколова"}`.<br>3. Repeat the select in a new session. |
| Expected result | `200 OK`; step 3 shows `name = "Мария Соколова"` and `email`, `is_verified = true`, `created_at`, `failed_attempt_count = 2` and `password_hash` all byte-equal to step 1. |
| Status | Not run |

### TC-13-API-5.2 — A rename writes only the name

| Field | Value |
|---|---|
| Description | The guard is the shape of the emitted statement, not the resulting row — SQLAlchemy's dirty check is an unasserted implementation detail. |
| Preconditions | Account A signed in; a `before_cursor_execute` listener attached, per the idiom of `test_generation_storage_cas_shape.py`. |
| Test data | `{"name": "Мария Соколова"}` |
| Steps | 1. Attach the statement capture.<br>2. `PATCH /api/v1/auth/me` with `{"name": "Мария Соколова"}`.<br>3. Filter the captured statements for `UPDATE accounts`. |
| Expected result | Exactly one `UPDATE accounts` statement is captured; its SET clause names `name` and nothing else — no `email`, no `password_hash`, no `is_verified`, no `failed_attempt_count`. |
| Status | Not run |
| Note | Two concurrent renames issued together are **not** this guard — they serialize, and a test that goes green on the defect it names certifies the bug (`13_ProfileManagement_Notes.md`). |

### TC-13-API-5.3 — Renaming one account leaves every other account untouched

| Field | Value |
|---|---|
| Description | Catches a missing `WHERE id = …` on the rename UPDATE. |
| Preconditions | Account A (`Мария Соколова`) and account B (`Иван Петров`) both exist. |
| Test data | Account A renames to `Мария Волкова`. |
| Steps | 1. `PATCH /api/v1/auth/me` as account A with `{"name": "Мария Волкова"}`.<br>2. Select `name, email` for account B in a new session. |
| Expected result | `200 OK`; account B still has `name = "Иван Петров"` and `email = "qa.stranger13@textery.test"`. |
| Status | Not run |

### TC-13-API-5.4 — Repeating the same rename is safe

| Field | Value |
|---|---|
| Description | A rename to the value already held is a success, not a no-op to be refused; and it must not insert a second row via an upsert-shaped write. |
| Preconditions | Account A signed in with stored `name = "Мария Соколова"`. |
| Test data | `{"name": "Мария Соколова"}` sent twice. |
| Steps | 1. `PATCH /api/v1/auth/me` with `{"name": "Мария Соколова"}`.<br>2. Send the identical request again.<br>3. `SELECT count(*) FROM accounts WHERE email = 'qa.profile@textery.test'` and select `name`, in a new session. |
| Expected result | Both requests answer `200 OK` with `"name": "Мария Соколова"`; no `IntegrityError`; the count is exactly `1`; the stored `name` is `Мария Соколова`. |
| Status | Not run |

### TC-13-API-5.5 — A rename commits once, and a refused rename commits not at all

| Field | Value |
|---|---|
| Description | Pins the transaction boundary on both outcomes, against a real `SqlAlchemyUnitOfWork` bound to the repository session (wiring shape of `test_login_wiring.py`). |
| Preconditions | Account A signed in; the unit of work's `commit` instrumented with a counter. |
| Test data | Success: `{"name": "Мария Соколова"}`. Refusal: `{"name": "я" × 61}`. |
| Steps | 1. `PATCH /api/v1/auth/me` with the valid name; read the commit count.<br>2. Reset the counter; `PATCH` with the 61-code-point name; read the count. |
| Expected result | Step 1: `200 OK` and the commit count is exactly `1`. Step 2: `400 INVALID_NAME` and the commit count is `0`. |
| Status | Not run |

### TC-13-API-5.5a — A failure between the write and the commit leaves the old name stored

| Field | Value |
|---|---|
| Description | TC-13-API-5.5's negative half provokes a validation refusal, which short-circuits before any write and therefore proves nothing about rollback. This is the only scenario that exercises write-then-fail. |
| Preconditions | Account A signed in with stored `name = "Мария Соколова"`; the unit of work's `commit` patched to raise `OperationalError` after the UPDATE has been flushed. |
| Test data | `{"name": "Мария Волкова"}` |
| Steps | 1. `PATCH /api/v1/auth/me` with `{"name": "Мария Волкова"}` while the commit is forced to fail.<br>2. Re-read account A's row on a **new** connection.<br>3. Read the same row from a second independent connection opened during step 1's transaction. |
| Expected result | Step 1: `500 INTERNAL_ERROR`. Step 2: `name` is `Мария Соколова` — the previous value. Step 3: never observes `Мария Волкова`. |
| Status | Not run |

### TC-13-API-5.5b — A rename against a removed account mutates nothing

| Field | Value |
|---|---|
| Description | TC-13-API-1.4 asserts only the refusal. An upsert-shaped write branch resurrects the row and the refusal still reads as a clean `401`. |
| Preconditions | Account A signed in and its access token captured; the row then deleted; the total `accounts` row count recorded. |
| Test data | Account A's captured token; `{"name": "Мария Волкова"}`. |
| Steps | 1. Record `SELECT count(*) FROM accounts`.<br>2. `PATCH /api/v1/auth/me` with the captured token and `{"name": "Мария Волкова"}`.<br>3. `SELECT count(*) FROM accounts` and `SELECT * FROM accounts WHERE id = '3d9f1a26-7c48-4b1e-9a03-51e6b8d47f20'`. |
| Expected result | `401 Unauthorized` with the `UNAUTHORIZED` body; the account A row select returns zero rows; the total count in step 3 equals step 1. |
| Status | Not run |

### TC-13-API-5.6 — A freshly registered account starts with no name

| Field | Value |
|---|---|
| Description | A column defaulted to `''` rather than `NULL` breaks the email fallback for every new account without any rename ever happening. |
| Preconditions | None — the account is registered inside the test. |
| Test data | Register `qa.fresh13@textery.test` / `Qa!Fresh2026` and verify it. |
| Steps | 1. `POST /api/v1/auth/register` and complete verification.<br>2. `SELECT name FROM accounts WHERE email = 'qa.fresh13@textery.test'` in a new session.<br>3. `GET /api/v1/auth/me` with the new account's token. |
| Expected result | Step 2: `name IS NULL` is true; the value is not `''`. Step 3: `200 OK` with `"name": null`. |
| Status | Not run |

---

## 6. Rename — Response and Mass Assignment

### TC-13-API-6.1 — A rename answers with the whole profile, normalized

| Field | Value |
|---|---|
| Description | The client updates its identity snapshot from this response and recomputes its dirty flag against it — a trailing space echoed back keeps the form dirty forever after a successful save. |
| Preconditions | Account A signed in, `created_at = 2026-03-14T09:26:53Z`. |
| Test data | `{"name": "  Мария Соколова  "}` (two leading and two trailing spaces). |
| Steps | 1. `PATCH /api/v1/auth/me` with `{"name": "  Мария Соколова  "}`. |
| Expected result | `200 OK`; body exactly `{"email": "qa.profile@textery.test", "name": "Мария Соколова", "created_at": "2026-03-14T09:26:53Z"}` — trimmed, and carrying all three fields so no second `GET` is needed. |
| Status | Not run |

### TC-13-API-6.2 — Server-owned fields sent alongside a name are never persisted

| Field | Value |
|---|---|
| Description | The input allow-list is the request DTO itself. Binding the response DTO here is the direct path to `email` or `is_verified` arriving from a body and reaching `save()`. |
| Preconditions | Account A verified, `failed_attempt_count = 2`, `password_hash` and `created_at` recorded. |
| Test data | Body `{"name": "Мария Волкова", "email": "attacker@evil.test", "is_verified": false, "created_at": "2000-01-01T00:00:00Z", "password": "Hacked!2026", "password_hash": "x", "failed_attempt_count": 0, "id": "8b21c07e-4f5a-4d92-8c31-a7d0e2f96415"}` |
| Steps | 1. Record account A's full row.<br>2. `PATCH /api/v1/auth/me` with the body above.<br>3. Re-read account A's full row in a new session. |
| Expected result | `200 OK` (unknown keys ignored, not rejected); step 3 shows `name = "Мария Волкова"` and `email = "qa.profile@textery.test"`, `is_verified = true`, `created_at = 2026-03-14T09:26:53Z`, `failed_attempt_count = 2`, `password_hash` and `id` all equal to step 1. |
| Status | Not run |

### TC-13-API-6.3 — A rename cannot reach another account

| Field | Value |
|---|---|
| Description | The account is resolved only through `get_current_owner_id`; an `id` in the body must have no effect on which row is written. |
| Preconditions | Account A (`Мария Соколова`) and account B (`Иван Петров`) both exist. |
| Test data | Account A sends `{"name": "Взломано", "id": "8b21c07e-4f5a-4d92-8c31-a7d0e2f96415"}` (account B's id). |
| Steps | 1. `PATCH /api/v1/auth/me` as account A with that body.<br>2. Select `name` for account A and for account B in a new session. |
| Expected result | `200 OK`; account A's `name` is `Взломано`; account B's `name` is still `Иван Петров` and its `email` is unchanged. |
| Status | Not run |

---

## 7. Transport Boundary and Disclosure

### TC-13-API-7.1 — An oversized body is refused at the boundary

| Field | Value |
|---|---|
| Description | The 256-code-point raw gate runs after the JSON body is already in memory, so a 10 MB `name` would be fully buffered on the way to being rejected. |
| Preconditions | Account A signed in; a memory/buffer probe or a body-read counter on the request pipeline. |
| Test data | `PATCH` body `{"name": "<10 MiB of 'а'>"}`, well over the 2 MiB app cap. |
| Steps | 1. `PATCH /api/v1/auth/me` with the 10 MiB body against `BACKEND_PORT`.<br>2. Inspect how many bytes of the body were read before the response was written. |
| Expected result | `413 Payload Too Large` with `{"error_code": "REQUEST_BODY_TOO_LARGE", "message": …}`; the bytes read stop at or below the 2 MiB cap — the full 10 MiB is never buffered and the JSON is never parsed. |
| Status | Not run |

### TC-13-API-7.2 — The boundary refusal is reached through the path a browser takes

| Field | Value |
|---|---|
| Description | The proxy in front of the API carries no body cap today, so its 1 MiB default answers first with HTML: a test that only reaches the backend port is green on a path no user takes (`endpoints.md` § Corrected after the review passes). |
| Preconditions | The app served through nginx (`infra/docker/nginx/frontend.conf`, `location /api/` → `backend:8000`) with `client_max_body_size 4m;`; account A signed in. |
| Test data | The same 10 MiB body, sent to `<app_url>/api/v1/auth/me`, not to `BACKEND_PORT`. |
| Steps | 1. `PATCH <app_url>/api/v1/auth/me` with the 10 MiB body.<br>2. Read the response `Content-Type` and body. |
| Expected result | `413` with `Content-Type: application/json` and body `{"error_code": "REQUEST_BODY_TOO_LARGE", "message": …}` — not nginx's `text/html` `<html><head><title>413 Request Entity Too Large</title>` page. |
| Status | Not run |

### TC-13-API-7.3 — No failure leaks the account's identity or the system's internals

| Field | Value |
|---|---|
| Description | The route's two PII fields must appear in no failure body and in no log line, and no failure may carry a stack trace, a file path or driver syntax. |
| Preconditions | Account G seeded with a distinctive email and name; the application log captured for the duration. |
| Test data | Account G `qa.canary.7f3a@textery.test`, `name = "КанарейкаА9Z"`. Provoke: (a) `GET /api/v1/auth/me` with no token; (b) `PATCH` with `{"name": "я" × 61}`; (c) a forced `500` on the read path. |
| Steps | 1. Provoke refusal (a) and capture the response and log.<br>2. Provoke (b).<br>3. Provoke (c).<br>4. Search all three bodies and the captured log for the two canary strings and for `Traceback`, `/app/`, `.py:`, `SELECT`, `psycopg`. |
| Expected result | Bodies are `401 UNAUTHORIZED`, `400 INVALID_NAME`, `500 INTERNAL_ERROR`; none contains `qa.canary.7f3a@textery.test` or `КанарейкаА9Z`; none contains `Traceback`, a file path, or SQL text; neither canary appears anywhere in the captured log. |
| Status | Not run |

### TC-13-API-7.4 — Every failure family answers the canonical failure form

| Field | Value |
|---|---|
| Description | One envelope across the whole contract, so a client's error handling has one shape to parse. |
| Preconditions | Account A signed in. |
| Test data | `401` (no token), `400 NAME_INPUT_TOO_LARGE` (`"а" × 300`), `400 INVALID_NAME` (`{"name": 123}`), `413 REQUEST_BODY_TOO_LARGE` (10 MiB body), `500 INTERNAL_ERROR` (forced fault). |
| Steps | 1. Provoke each of the five refusals in turn.<br>2. List the top-level keys of each response body. |
| Expected result | Every body's key set is exactly `{"error_code", "message"}` — both present, both strings, and no third key (`detail`, `errors`, `trace`, `input`). |
| Status | Not run |

### TC-13-API-7.5 — Redaction is a stated substitution, not the absence of a string

| Field | Value |
|---|---|
| Description | TC-13-API-7.3 passes on any encoding change — a JSON-escaped email or a row repr in a debug field satisfies "does not contain". The token is a credential and is covered here because the ordinary way it leaks is a warning line echoing the rejected authorization header. |
| Preconditions | Account G seeded as in TC-13-API-7.3, with a known access token; the application log captured. |
| Test data | Email `qa.canary.7f3a@textery.test`, name `КанарейкаА9Z`, token `eyJhbGciOiJIUzI1NiJ9.<canary>`; redaction marker `[REDACTED]`. |
| Steps | 1. Provoke the `401`, `400` and `500` families in turn.<br>2. For each, read the log record and the response body.<br>3. Search both for the three values raw, JSON-escaped (`@`, `К`), percent-encoded (`%40`, `%D0%9A`) and base64 (`cWEuY2FuYXJ5`). |
| Expected result | Each log record shows `[REDACTED]` in the position the value would have occupied (e.g. `account=[REDACTED]`, `authorization=[REDACTED]`); none of the three values appears in any body or log record in any of the four encodings. |
| Status | Not run |
| Note | The literal marker text is a story decision not yet fixed in code — `[REDACTED]` is the value asserted here and must match whatever the logging adapter emits. |

### TC-13-API-7.6 — A server fault is attributable after redaction

| Field | Value |
|---|---|
| Description | Written as counter-pressure to TC-13-API-7.3 and 7.5, which are fully satisfied by a `500` that logs nothing an operator could trace. Redaction and attribution must be pinned together or one silently defeats the other. |
| Preconditions | Account A signed in; the read path forced to raise; the application log captured. |
| Test data | Forced fault on `GET /api/v1/auth/me`; correlation header `X-Request-Id`. |
| Steps | 1. `GET /api/v1/auth/me` with the fault armed.<br>2. Read the response headers and body.<br>3. Count log records carrying that request's correlation identifier. |
| Expected result | `500` with the `INTERNAL_ERROR` body; the response carries a correlation identifier (`X-Request-Id` header or a `request_id` field); exactly **one** log record carries that identifier — not zero, not a duplicated pair. |
| Status | Not run |

---

## 8. The Published Contract

### TC-13-API-8.1 — Neither schema declares a length in a unit the domain does not use

| Field | Value |
|---|---|
| Description | OpenAPI counts UTF-16 units and the domain counts code points; they split at exactly the astral boundary these tests assert, so a well-meant `maxLength: 60` makes a generated client refuse a name the server accepts (`endpoints.md`). Nothing else in this spec would go red on that edit. |
| Preconditions | `api-specs/auth_me_get.yaml` and `api-specs/auth_me_update.yaml` present. |
| Test data | Both YAML files; validation payload `{"name": "😀" × 60}` against `UpdateProfileRequest`. |
| Steps | 1. Parse both specs and read `ProfileResponse.properties.name` and `UpdateProfileRequest.properties.name`.<br>2. Validate `{"name": "😀" × 60}` against the published `UpdateProfileRequest` schema with a standard JSON-Schema validator. |
| Expected result | Neither `name` property declares `maxLength` (or `minLength`); step 2 validates successfully with zero errors. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `an authenticated account` | Registered + verified account, valid access token in `Authorization: Bearer` |
| `it reads its profile` | `GET /api/v1/auth/me` |
| `it renames itself` / `submits a name` | `PATCH /api/v1/auth/me` with `{"name": …}` |
| `a fresh read of the stored profile` | Re-read through a **new** SQLAlchemy session (not `expire_on_commit=False` identity map) against real Postgres |
| `a fresh read of the whole stored row` | Direct row select of `email`, `name`, `is_verified`, `created_at`, `failed_attempt_count` |
| `the raw input cap` | 256 code points, checked before trim/NFC → `NAME_INPUT_TOO_LARGE` |
| `the name bound` | 60 code points after trim + NFC → `INVALID_NAME` |
| `astral characters` | U+1F600 and friends — 1 code point, 2 UTF-16 units, 4 UTF-8 bytes |
| `base and combining pairs` | NFD input, 120 raw code points normalizing to 60 |
| `this product's canonical failure form` | `{"error_code": …, "message": …}` via `exception_handlers.py` |
| `exactly one update reaches the database` | `before_cursor_execute` capture, idiom of `test_generation_storage_cas_shape.py` |
| `the work is committed exactly once` | Real `SqlAlchemyUnitOfWork` bound to the repository session; wiring shape of `test_login_wiring.py` |
| `the request body cap` | 2 MiB application cap (`api-specs/README.md`); proxy cap 4 MiB above it |
| `the application's own origin` | `app_url` (through nginx), not `BACKEND_PORT` |
| `forbid storing the body` | `Cache-Control: no-store` on every response of both routes |
