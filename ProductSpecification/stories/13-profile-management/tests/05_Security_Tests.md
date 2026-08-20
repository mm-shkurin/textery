# Profile management — Security Tests

Scoped to this story's actual attack surface. Not included: generic unauthenticated 401s,
security headers, CORS and HTTPS (cross-cutting, tested globally); SQL injection (the ORM
parameterizes, and the scan dismissed it with that reason); account enumeration (no route
takes an account identifier, so there is nothing to enumerate — 1.3 is the guard that it
stays that way); session fixation (bearer tokens, no server session).

The dominant risk here is **stored XSS with the widest blast radius in the application**:
the name is free-form user text echoed into a header that renders on every page, with length
as the only input restriction by design. The whole escaping burden therefore sits at output,
across two sinks.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A | `qa.profile@textery.test` / `Qa!Profile2026`, id `3d9f1a26-7c48-4b1e-9a03-51e6b8d47f20`, `name = "Мария Соколова"` |
| Account B | `qa.stranger13@textery.test` / `Qa!Stranger2026`, id `8b21c07e-4f5a-4d92-8c31-a7d0e2f96415`, `name = "Иван Петров"` |
| Canary account | `qa.canary.7f3a@textery.test`, `name = "КанарейкаА9Z"`, token `eyJhbGciOiJIUzI1NiJ9.<canary>` |
| 401 body | `{"error_code": "UNAUTHORIZED", "message": "A valid access token is required."}` |
| Script payload | `<script>alert(1)</script>` |
| Attribute-breaking payload | `" onmouseover="alert(1)` |
| RTL override payload | `Мария‮авиж` (U+202E) |
| Invisible payloads | U+200B, U+FEFF, U+00A0, U+3164, U+2800 |
| Bounds | raw cap 256 code points → `400 NAME_INPUT_TOO_LARGE`; name bound 60 after trim+NFC → `400 INVALID_NAME`; body cap 2 MiB → `413 REQUEST_BODY_TOO_LARGE` |
| Redaction marker | `[REDACTED]` in the log where a value would have stood |

---

## 1. Authorization Surface

### TC-13-SEC-1.1 — A caller can never read another account's profile

| Field | Value |
|---|---|
| Description | The account is resolved only through `get_current_owner_id`; a token/identity mix-up would serve one account's email to another. |
| Preconditions | Accounts A and B both registered, verified and named, each holding its own valid access token. |
| Test data | A's token; B's token. |
| Steps | 1. `GET /api/v1/auth/me` with A's token; record the body.<br>2. `GET /api/v1/auth/me` with B's token; record the body.<br>3. Search each body for the other account's email and name. |
| Expected result | A's body is `{"email": "qa.profile@textery.test", "name": "Мария Соколова", "created_at": …}`; B's is `{"email": "qa.stranger13@textery.test", "name": "Иван Петров", "created_at": …}`; neither body contains `qa.stranger13@textery.test`/`Иван Петров` respectively, nor the other's `created_at`. |
| Status | Not run |

### TC-13-SEC-1.2 — A caller can never write another account's profile

| Field | Value |
|---|---|
| Description | An `id` accepted from the body or the query would turn a display-name route into an arbitrary-account write. |
| Preconditions | Accounts A and B both named; A holding a valid access token. |
| Test data | Body `{"name": "Взломано", "id": "8b21c07e-4f5a-4d92-8c31-a7d0e2f96415"}`; and `PATCH /api/v1/auth/me?id=8b21c07e-4f5a-4d92-8c31-a7d0e2f96415` with `{"name": "Взломано2"}`. |
| Steps | 1. `PATCH /api/v1/auth/me` as A with the body carrying B's id.<br>2. `PATCH /api/v1/auth/me?id=<B id>` as A with `{"name": "Взломано2"}`.<br>3. Re-read both rows in a new session. |
| Expected result | Both PATCHes answer `200 OK`; account A's `name` ends as `Взломано2`; account B's `name` is still `Иван Петров` and its `email` is unchanged. |
| Status | Not run |

### TC-13-SEC-1.3 — Neither route accepts an account identifier as a parameter

| Field | Value |
|---|---|
| Description | "A caller can never read another account's profile" is a property of the route *shape* here, not of a check somebody has to remember to write. This case is the guard that the shape stays that way. |
| Preconditions | `api-specs/auth_me_get.yaml` and `api-specs/auth_me_update.yaml` present; the running app's `/openapi.json` reachable. |
| Test data | Path `/api/v1/auth/me`; the `parameters` list of both operations. |
| Steps | 1. Read the `parameters` array of the `get` and `patch` operations at `/api/v1/auth/me` in both YAML files and in the served `/openapi.json`.<br>2. Confirm no path template segment carries an id.<br>3. Confirm `getOwnOwnerId`-style resolution is the only account source in `backend/adapters/rest/src/router/auth/`. |
| Expected result | The path is literally `/api/v1/auth/me` with no `{…}` segment; the `parameters` array is empty or absent on both operations — no `id`, `account_id`, `user_id` or `email` parameter in path or query; the handler signature takes the owner id only from `get_current_owner_id`. |
| Status | Not run |

### TC-13-SEC-1.4 — A token that is not a live access token is refused identically in every case

| Field | Value |
|---|---|
| Description | Any divergence between the five refusals tells an attacker which half of the credential they got right — the deleted-account case in particular must not be distinguishable from a forged token. |
| Preconditions | Account A registered; a second account registered and then its row deleted while its token is retained. |
| Test data | (a) a refresh token; (b) a token with no `type` claim; (c) `type: "session"`; (d) a valid token whose account row is gone; (e) a token signed with a wrong key. |
| Steps | 1. `GET /api/v1/auth/me` with each of the five tokens.<br>2. `PATCH /api/v1/auth/me` with `{"name": "X"}` with each of the five.<br>3. Compare all ten status lines, headers (`Date` aside) and bodies. |
| Expected result | All ten answer `401 Unauthorized` with body `{"error_code": "UNAUTHORIZED", "message": "A valid access token is required."}` and `Cache-Control: no-store`; all ten are byte-identical to one another — no `403`, no `404`, no differing message, no differing header set. |
| Status | Not run |

### TC-13-SEC-1.5 — The account check denies when its own database access fails

| Field | Value |
|---|---|
| Description | This check runs on its own session, separate from the profile read (`endpoints.md`), so it is a guard with an independently failing backing store. Exhausting the pool and asserting "the request fails" does not cover it: on the read path that failure is equally explained by the profile read dying downstream, so the scenario stays green on an existence check that swallows its error and answers "the account exists". |
| Preconditions | Account A signed in with a stored `name = "Мария Соколова"`; the **existence check's** session made to fail independently of the profile read's session. |
| Test data | (a) the existence check's `session.get` patched to raise `OperationalError`; (b) its checkout patched to raise `TimeoutError` (pool checkout timeout). |
| Steps | 1. Under (a): `GET /api/v1/auth/me`, then `PATCH /api/v1/auth/me` with `{"name": "Мария Волкова"}`.<br>2. Under (b): repeat both.<br>3. Compare all four responses against the forged-token `401` of TC-13-SEC-1.4(e).<br>4. Re-read account A's row in a new session. |
| Expected result | All four answer `401 Unauthorized` — never `200`, never `500` — with the `UNAUTHORIZED` body byte-identical to the forged-token refusal; step 4 shows `name` still `Мария Соколова`. |
| Status | Not run |

---

## 2. Mass Assignment

### TC-13-SEC-2.1 — Only the name is writable through the rename route

| Field | Value |
|---|---|
| Description | The response is described as "the profile", which invites reusing the response model for the request; that model plus a repository update branch that rewrites the aggregate is a direct path to `is_verified` or `email` being set from a request body (`13_ProfileManagement_Notes.md` § Security Considerations). |
| Preconditions | Account A verified (`is_verified = true`), `failed_attempt_count = 2`, `created_at = 2026-03-14T09:26:53Z`, `password_hash` recorded. |
| Test data | Body `{"name": "Мария Волкова", "is_verified": false, "email": "attacker@evil.test", "password": "Hacked!2026", "password_hash": "x", "created_at": "2000-01-01T00:00:00Z", "failed_attempt_count": 0, "id": "8b21c07e-4f5a-4d92-8c31-a7d0e2f96415"}` |
| Steps | 1. Record account A's full row.<br>2. `PATCH /api/v1/auth/me` with the body above.<br>3. Re-read the full row in a new session.<br>4. Attempt to sign in with `Hacked!2026`. |
| Expected result | `200 OK`; step 3 shows `name = "Мария Волкова"` and `is_verified = true`, `email = "qa.profile@textery.test"`, `created_at = 2026-03-14T09:26:53Z`, `failed_attempt_count = 2`, `password_hash` and `id` unchanged; step 4 is refused — the password was not set from the body. |
| Status | Not run |

---

## 3. Stored Cross-Site Scripting

### TC-13-SEC-3.1 — A name carrying markup renders as text in every sink

| Field | Value |
|---|---|
| Description | Three sinks, not one: element text, the profile field, and the `aria-label`/`title` attribute on the avatar. An attribute sink escapes differently from a text sink, so one assertion does not cover the other. No raw-HTML rendering may be used on this value. |
| Preconditions | Two accounts, each signed in through the browser, with the stored names below (set through `PATCH /api/v1/auth/me`, which stores them verbatim). |
| Test data | Name 1: `<script>alert(1)</script>`. Name 2: `" onmouseover="alert(1)`. |
| Steps | 1. Sign in as account 1; load `/projects` and `/profile`.<br>2. Read the header identity's `textContent`, the «Отображаемое имя» input's value, and the avatar's `aria-label`/`title`.<br>3. Query the DOM for `script` elements and for any `onmouseover` attribute added since load; install a global `alert` spy.<br>4. Repeat for account 2. |
| Expected result | The header identity's `textContent` is exactly `<script>alert(1)</script>` / `" onmouseover="alert(1)`; the input's value is the same string; the `aria-label` reads «Меню профиля: <script>alert(1)</script>» with the payload intact as text; `document.querySelectorAll('script')` gains no element, no `onmouseover` attribute exists on any identity element, and the `alert` spy is never called; the value is rendered through text nodes / bound attributes, never `innerHTML` or `dangerouslySetInnerHTML`. |
| Status | Not run |

### TC-13-SEC-3.1a — The address is the second hostile value into the same three sinks

| Field | Value |
|---|---|
| Description | With no name set — the state of every new account — the address **is** the rendered identity and the initials source. Every markup scenario feeds the name; whether the address value object forbids these characters is the unstated assumption this pins. |
| Preconditions | Two accounts registered with the addresses below, verified, **with no name set**, each signed in through the browser. If the `Email` value object refuses these addresses at registration, that refusal is the passing outcome and is recorded as such. |
| Test data | Address 1: `"<script>alert(1)</script>"@textery.test`. Address 2: `"\" onmouseover=\"alert(1)"@textery.test`. |
| Steps | 1. Register and verify each address (or record the refusal).<br>2. Sign in as each; load `/projects` and `/profile`.<br>3. Read the header identity's `textContent`, the screen identity text and the avatar's `aria-label`.<br>4. Query for injected `script` elements / `onmouseover` attributes; watch the `alert` spy. |
| Expected result | Either registration refuses the address with `400` and the payload never reaches a sink, **or** all three sinks render the address literally as text (`textContent` equal to the raw address, `aria-label` «Меню профиля: <the raw address>»), with no `script` element created, no `onmouseover` bound and the `alert` spy never called. |
| Status | Not run |

### TC-13-SEC-3.2 — A bidirectional override in a name cannot reorder the surrounding header

| Field | Value |
|---|---|
| Description | Not the same guard as TC-13-SEC-3.1 and not satisfied by escaping — U+202E is legal text. It needs bidi isolation at the sink. |
| Preconditions | An account whose stored name is the RTL payload, signed in through the browser. |
| Test data | `name = "Мария‮авиж"`; the header text surrounding the name («Меню профиля», «Выйти», the address row). |
| Steps | 1. Load `/projects` and open the avatar menu.<br>2. Inspect the element wrapping the name for `<bdi>` or `unicode-bidi: isolate` / `isolate-override`.<br>3. Compare the rendered order of the surrounding header text against the same page rendered with a plain name. |
| Expected result | The name is wrapped in `<bdi>` or carries `unicode-bidi: isolate` (computed style); the surrounding header text renders in the same visual order as with a plain name — the override's effect stops at the name's own box and does not reverse the items after it. |
| Status | Not run |

### TC-13-SEC-3.3 — A name that renders as nothing cannot be stored

| Field | Value |
|---|---|
| Description | An invisible name is worse than no name: it blanks the identity row and truncates the accessible label to a bare prefix, destroying the one job that row has. |
| Preconditions | Account A signed in with `name = "Мария Соколова"`, re-set before each sub-step. |
| Test data | `{"name": "​"}` (U+200B), `{"name": "﻿"}` (U+FEFF), `{"name": " "}` (U+00A0), `{"name": "ㅤ"}` (U+3164), `{"name": "⠀"}` (U+2800). |
| Steps | 1. For each payload: `PATCH /api/v1/auth/me`, then re-read the row in a new session.<br>2. After each, load `/projects` and read the identity row and the avatar's `aria-label`. |
| Expected result | Each PATCH answers `200 OK` with `"name": null`; each fresh read shows `name IS NULL` — none of the five is stored; the identity row shows `qa.profile@textery.test` and the `aria-label` reads «Меню профиля: qa.profile@textery.test», never the bare «Меню профиля: ». |
| Status | Not run |

---

## 4. Input Bounds

### TC-13-SEC-4.1 — The name is bounded at every layer that can be reached

| Field | Value |
|---|---|
| Description | Three bounds, three layers: the transport cap, the cheap raw gate before normalization, and the domain bound after it. A missing one is only visible at its own layer. |
| Preconditions | Account A signed in with `name = "Мария Соколова"`; an NFC/normalization probe on the value-object path. |
| Test data | (a) `{"name": "а" × 300}`; (b) `{"name": "я" × 61}`; (c) a `PATCH` body of 10 MiB. |
| Steps | 1. Send (a); record the status, `error_code`, and whether the normalization step was entered.<br>2. Send (b); record the status and `error_code`.<br>3. Send (c) against `BACKEND_PORT`; record the status and `error_code`.<br>4. Re-read account A's row in a new session. |
| Expected result | (a) `400 NAME_INPUT_TOO_LARGE`, and the trim/NFC step was **not** entered — the cheap gate ran first. (b) `400 INVALID_NAME`. (c) `413 REQUEST_BODY_TOO_LARGE`. Step 4 shows `name` still `Мария Соколова` in all three cases. |
| Status | Not run |

### TC-13-SEC-4.2 — A refusal never echoes the rejected input back

| Field | Value |
|---|---|
| Description | The framework's own validation failure does echo the input, which is why these must reach the domain path rather than that one (`endpoints.md`). |
| Preconditions | Account A signed in. |
| Test data | (a) `{"name": "ХочуЛомать" + "я" × 61}` (over the bound, with a distinctive marker); (b) `{"name": 1234567}`; (c) `{"name": ["ХочуЛомать"]}`. |
| Steps | 1. Send each of the three.<br>2. List each response body's top-level keys.<br>3. Search each body for `ХочуЛомать`, `1234567` and `[`. |
| Expected result | Each answers `400` with a key set of exactly `{"error_code", "message"}` — no `detail`, no `input`, no `ctx`; none of the three bodies contains `ХочуЛомать`, `1234567` or the submitted array. |
| Status | Not run |

---

## 5. Disclosure of Personal Data

### TC-13-SEC-5.1 — Neither route's response may be cached

| Field | Value |
|---|---|
| Description | The body carries the account's email; the header is applied at the route before the outcome is known, so refusals carry it too. |
| Preconditions | Account A signed in. |
| Test data | `GET /me` `200`; `PATCH /me` `200`; `GET /me` with no token (`401`); `PATCH /me` with `{"name": "я" × 61}` (`400`). |
| Steps | 1. Issue all four requests.<br>2. Read `Cache-Control`, `Pragma` and `Expires` on each response. |
| Expected result | All four carry `Cache-Control: no-store`; none carries `public`, `max-age` > 0 or a future `Expires`. |
| Status | Not run |

### TC-13-SEC-5.2 — No failure path logs or returns the account's identity

| Field | Value |
|---|---|
| Description | The route's two PII fields must appear in no failure body and in no log line. |
| Preconditions | The canary account seeded; the application log captured for the duration. |
| Test data | Email `qa.canary.7f3a@textery.test`, name `КанарейкаА9Z`. Provoke: `401` (forged token), `400 INVALID_NAME` (`"я" × 61`), `500` (forced fault on the read path). |
| Steps | 1. Provoke each of the three failures in turn.<br>2. Search each response body for the two canary strings.<br>3. Search the captured log for the two canary strings. |
| Expected result | Bodies are `401 UNAUTHORIZED`, `400 INVALID_NAME`, `500 INTERNAL_ERROR`; `qa.canary.7f3a@textery.test` and `КанарейкаА9Z` appear in none of the three bodies and in no captured log record. |
| Status | Not run |

### TC-13-SEC-5.2a — Redaction replaces the value rather than merely omitting it

| Field | Value |
|---|---|
| Description | TC-13-SEC-5.2 asserts absence of the raw string, which any encoding change satisfies. The bearer token is included because the ordinary way it leaks is a warning line echoing the rejected authorization header. |
| Preconditions | The canary account seeded with its distinctive email, name and access token; the application log captured. |
| Test data | The three canary values; encodings to search: raw, JSON-escaped (`К`), percent-encoded (`%40`, `%D0%9A`), base64 (`cWEuY2FuYXJ5`). Redaction marker `[REDACTED]`. |
| Steps | 1. Provoke the `401`, `400` and `500` families in turn.<br>2. For each, read the log record and the response body.<br>3. Assert the marker appears where each value would have stood.<br>4. Search both for all four encodings of each of the three values. |
| Expected result | Each log record carries `[REDACTED]` in the position of the value (e.g. `account=[REDACTED]`, `authorization=[REDACTED]`) — the field is present and masked, not silently dropped; none of the three values appears in any body or log record in any of the four encodings. |
| Status | Not run |
| Note | The literal marker text is a story decision not yet fixed in code — `[REDACTED]` is the value asserted here and must match whatever the logging adapter emits. |

### TC-13-SEC-5.3 — Signing out leaves no identity behind on a shared machine

| Field | Value |
|---|---|
| Description | The account-switch case does not cover this one: there, the next sign-in overwrites the snapshot. Here nothing overwrites it. |
| Preconditions | Account A signed in through the browser, `/profile` and `/projects` both visited so the identity snapshot is populated. |
| Test data | `name = "Мария Соколова"`, `email = qa.profile@textery.test`. |
| Steps | 1. Sign in and load `/profile`.<br>2. Choose «Выйти».<br>3. Enumerate every key/value in `sessionStorage`, `localStorage` and any IndexedDB store used by the app.<br>4. Read the full rendered `document.body.innerText` of the resulting page. |
| Expected result | No storage value in any of the three contains `qa.profile@textery.test` or `Мария Соколова` (searched as substrings across all values, including JSON blobs); the rendered page contains neither string; the avatar shows no initials `МС`. |
| Status | Not run |

### TC-13-SEC-5.4 — An account switch in one tab never shows the previous account's identity

| Field | Value |
|---|---|
| Description | A cross-account identity leak, strictly worse than a stale name. |
| Preconditions | Account A signed in in a tab; `GET /api/v1/auth/me` held open by the test double so its response has not yet arrived. |
| Test data | Account A (`Мария Соколова` / `qa.profile@textery.test`), account B (`Иван Петров` / `qa.stranger13@textery.test`); the held response released after B is signed in. |
| Steps | 1. Sign in as A with the `/me` response held.<br>2. Sign out and sign in as B in the same tab.<br>3. Release A's held `/me` response.<br>4. Read the header identity; mount a second header after the switch and read it too.<br>5. Search the whole DOM for A's email and name. |
| Expected result | The header shows `Иван Петров` / `qa.stranger13@textery.test` before and after the release; the newly mounted header shows B's identity; `Мария Соколова` and `qa.profile@textery.test` appear nowhere in the DOM. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `a valid access token` | Access-typed JWT from the sign-in flow |
| `reads its profile` / `renames itself` | `GET` / `PATCH /api/v1/auth/me` |
| `a fresh read of the stored row` | Direct row select through a new session against real Postgres |
| `an attribute-breaking fragment` | `" onmouseover="alert(1)` |
| `a right-to-left override character` | U+202E — needs `<bdi>` or `unicode-bidi: isolate`, not escaping |
| `invisible characters` | U+200B, U+FEFF, U+00A0, U+3164, U+2800 |
| `the avatar's accessible label` | `aria-label` / `title` on `ProfileAvatar` («Меню профиля: …») |
| `the input cap` / `the name bound` | 256 raw code points / 60 normalized code points |
| `the request body cap` | 2 MiB application cap; proxy cap set above it |
| `forbid storing the body` | `Cache-Control: no-store` |
| `the captured application log` | Log appender captured for the duration of the request |
| `browser storage key` | `sessionStorage` and `localStorage` after `clearSession()` |
