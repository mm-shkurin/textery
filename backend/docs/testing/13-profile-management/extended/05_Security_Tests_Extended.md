<!-- COPIED FILE. Source of truth: ProductSpecification/stories/13-profile-management/tests/extended/05_Security_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Profile management — Security Tests (Extended)

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A | `qa.profile@textery.test` / `Qa!Profile2026`, `name = "Мария Соколова"` |
| 401 body | `{"error_code": "UNAUTHORIZED", "message": "A valid access token is required."}` |
| Script payload | `<script>alert(1)</script>` |
| Log-forging payload | `Мария\nWARNING:root:ADMIN GRANTED to qa.profile@textery.test` |
| Homoglyph payload | `Мaрия Coкoлoва` (Latin `a`, `C`, `o` inside Cyrillic text) |
| Identity surfaces | `/projects` header, `/profile` screen, the avatar menu panel, the avatar `aria-label`/`title` |
| Snapshot store | the single `/me`-backed identity store the header and screen both read |
| Browser storage | `sessionStorage` and `localStorage` |

---

## 1. Output Sinks Beyond the Header

### TC-13-SEC-1.1e — A name carrying markup renders as text wherever else identity is shown

| Field | Value |
|---|---|
| Description | The main file pins three sinks. Any *other* place the identity appears — the menu panel row, a page title, a tooltip, a future breadcrumb — is a fourth sink with its own escaping. |
| Preconditions | Account A's stored `name` set to the script payload; signed in through the browser. |
| Test data | `name = "<script>alert(1)</script>"`; every route that mounts the header, plus `/profile`; a global `alert` spy installed before load. |
| Steps | 1. Enumerate every place the identity is rendered: header identity, menu panel row, screen identity, name input, avatar `aria-label`/`title`, `document.title`.<br>2. Visit each authenticated route and read each of those values.<br>3. Query for `script` elements added since load and for any injected event-handler attribute.<br>4. Read the `alert` spy. |
| Expected result | Every one of those places holds the payload literally as text (`textContent` / attribute value equal to `<script>alert(1)</script>`); `document.querySelectorAll('script')` gains no element on any route; no injected handler attribute exists; the `alert` spy is never called on any page. |
| Status | Not run |

### TC-13-SEC-1.2e — A name carrying a line break does not forge a second log record

| Field | Value |
|---|---|
| Description | An unescaped newline in a logged value splits one record into two, and the forged half can claim anything an operator or a log-parsing alert would believe. |
| Preconditions | Account A signed in; the application log captured; an operation that logs something about the account (a refused rename or an audited write). |
| Test data | Submitted name `"Мария\nWARNING:root:ADMIN GRANTED to qa.profile@textery.test"` (a real newline in the JSON string). |
| Steps | 1. `PATCH /api/v1/auth/me` with that value.<br>2. Trigger the operation that logs about the account.<br>3. Count log records produced for that request.<br>4. Search the log for a record whose own level/prefix is `WARNING:root:ADMIN GRANTED`. |
| Expected result | Exactly one log record exists for the operation; no record begins with the forged `WARNING:root:ADMIN GRANTED` prefix — the newline is escaped (`\n`) or the value is redacted, so the fabricated text can only appear inside a field of the single genuine record, never as a record of its own. |
| Status | Not run |

---

## 2. Impersonation Through Look-Alikes

### TC-13-SEC-2.1e — A look-alike name is stored as written, not silently folded

| Field | Value |
|---|---|
| Description | Recorded rather than guarded: display names are not identifiers on this product, so homoglyph folding would cost more than it buys. The guard is that nothing silently rewrites the value — a rewrite would break the round-trip assertions the main files rely on. |
| Preconditions | Account A signed in. |
| Test data | `{"name": "Мaрия Coкoлoва"}` — Cyrillic `М`, `р`, `и`, `я` mixed with Latin `a` (U+0061), `C` (U+0043), `o` (U+006F). |
| Steps | 1. `PATCH /api/v1/auth/me` with that value.<br>2. Read the response `name` code point by code point.<br>3. Re-read account A's row in a new session and compare code point by code point. |
| Expected result | `200 OK`; both the response and the stored value are code-point-identical to what was sent — the Latin `a`/`C`/`o` are still U+0061/U+0043/U+006F, not folded to their Cyrillic look-alikes and not refused. |
| Status | Not run |

---

## 3. Token Handling Edges

### TC-13-SEC-3.1e — A malformed authorization header is refused like a missing one

| Field | Value |
|---|---|
| Description | A header parser that falls through on an unexpected shape can end up treating a malformed header as absent-but-authorized, or as a token to be trusted. |
| Preconditions | Account A registered with a stored name; a valid access token available for constructing the malformed variants. |
| Test data | (a) `Authorization: <raw token>` (no scheme); (b) `Authorization: Basic <raw token>`; (c) `Authorization: Token <raw token>`; (d) `Authorization: Bearer ` (empty token); (e) `Authorization: Bearer  <token>` (double space). |
| Steps | 1. `GET /api/v1/auth/me` with each of the five headers.<br>2. `PATCH /api/v1/auth/me` with `{"name": "Взломано"}` with each of the five.<br>3. Re-read account A's row in a new session. |
| Expected result | All ten answer `401 Unauthorized` with body `{"error_code": "UNAUTHORIZED", "message": "A valid access token is required."}` and `Cache-Control: no-store` — never `200`, never `500`; step 3 shows `name` still `Мария Соколова`. |
| Status | Not run |

### TC-13-SEC-3.2e — A token signed with the wrong key or algorithm is refused

| Field | Value |
|---|---|
| Description | The `alg: none` and HS/RS confusion attacks both produce a structurally perfect token; only signature verification pinned to the configured algorithm refuses them. |
| Preconditions | Account A registered; the app's configured signing key and algorithm known to the test. |
| Test data | (a) a token with correct claims signed with a different HMAC key; (b) the same claims with the header rewritten to `{"alg": "none"}` and the signature stripped; (c) the same claims signed with a different algorithm than the app configures. |
| Steps | 1. `GET /api/v1/auth/me` with token (a).<br>2. Repeat with (b).<br>3. Repeat with (c).<br>4. Compare all three responses with one another. |
| Expected result | All three answer `401 Unauthorized` with the `UNAUTHORIZED` body, byte-identical to one another and to the missing-token refusal; none returns any profile field. |
| Status | Not run |

---

## 4. Storage Hygiene

### TC-13-SEC-4.1e — The identity snapshot never outlives the session it belongs to

| Field | Value |
|---|---|
| Description | A snapshot left behind is readable by whoever uses the machine next, and by any script running on the origin afterwards — regardless of *how* the session ended. |
| Preconditions | Account A signed in through the browser, `/profile` visited so the snapshot is populated. |
| Test data | Session-end causes: (a) «Выйти»; (b) the refresh flow failing and ending the session; (c) the session key removed by another tab. |
| Steps | 1. Sign in and populate the snapshot.<br>2. End the session by cause (a); enumerate every `sessionStorage` and `localStorage` key/value.<br>3. Repeat for (b) and for (c). |
| Expected result | After each of the three, no value in either store contains `qa.profile@textery.test` or `Мария Соколова` as a substring — including inside JSON blobs and cache keys; the identity store key is removed, not merely emptied of one field. |
| Status | Not run |

### TC-13-SEC-4.2e — A refused rename leaves the shared identity snapshot untouched

| Field | Value |
|---|---|
| Description | Writing the typed value into the shared snapshot optimistically means a refused rename shows an unsaved name in every mounted header until the next page load. |
| Preconditions | Account A signed in on `/profile` with the header showing `Мария Соколова`; `PATCH /api/v1/auth/me` answering `400 {"error_code": "INVALID_NAME", …}`. |
| Test data | Typed name `"я" × 61`; refused with `400 INVALID_NAME`. |
| Steps | 1. Type the 61-character name and click «Сохранить».<br>2. Read the header identity and the avatar initials.<br>3. Read the identity snapshot in browser storage. |
| Expected result | The header still shows `Мария Соколова` with initials `МС`; the stored snapshot still holds `Мария Соколова` — the refused value was never written into it; the typed value remains only in the form field. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `reads` / `renames` | `GET` / `PATCH /api/v1/auth/me` |
| `a fabricated log prefix` | Newline plus a forged level/timestamp prefix in the name value |
| `characters that look like another alphabet's` | Cyrillic/Latin homoglyphs (е/e, а/a) |
| `a scheme this product does not use` | e.g. `Basic`, `Token` |
| `browser storage key` | `sessionStorage` and `localStorage` |
| `the shared identity snapshot` | The single `/me`-backed identity store the header and screen read |
