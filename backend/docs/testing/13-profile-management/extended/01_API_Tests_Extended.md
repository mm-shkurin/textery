<!-- COPIED FILE. Source of truth: ProductSpecification/stories/13-profile-management/tests/extended/01_API_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Profile management — API Tests (Extended)

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.profile@textery.test` / `Qa!Profile2026`, id `3d9f1a26-7c48-4b1e-9a03-51e6b8d47f20`, `name = "Мария Соколова"` |
| Account C (never named) | `qa.noname@textery.test` / `Qa!NoName2026`, `name = null` |
| Access token | `Authorization: Bearer <access token of account A>` |
| Error body shape | `{"error_code": "<CODE>", "message": "<generic text>"}` |
| The profile path | `/api/v1/auth/me` |
| Name bound | 60 code points after trim + NFC → `400 INVALID_NAME` |
| Body cap | 2 MiB → `413 REQUEST_BODY_TOO_LARGE` |
| Fresh read | re-read through a **new** SQLAlchemy session against real Postgres |

---

## 1. Method and Content Surface

### TC-13-API-1.1e — Methods this contract does not define are refused as such

| Field | Value |
|---|---|
| Description | The path carries exactly two operations. A framework fallback that answers `404`, or a handler that silently accepts `PUT` as `PATCH`, both hide the surface's real shape. |
| Preconditions | Account A signed in. |
| Test data | `POST`, `PUT`, `DELETE` on `/api/v1/auth/me`, each with account A's token and body `{"name": "Мария Волкова"}`. |
| Steps | 1. `POST /api/v1/auth/me`.<br>2. `PUT /api/v1/auth/me`.<br>3. `DELETE /api/v1/auth/me`.<br>4. Re-read account A's row in a new session. |
| Expected result | Each answers `405 Method Not Allowed` with an `Allow` header listing `GET` and `PATCH` (and `OPTIONS`/`HEAD` if the framework adds them) — never `404`, never `200`; step 4 shows `name` still `Мария Соколова`. |
| Status | Not run |

### TC-13-API-1.2e — Unknown keys alongside a valid name are ignored, not refused

| Field | Value |
|---|---|
| Description | The input allow-list is the request DTO itself, matching `documents_save`'s server-owned-fields decision: ignored rather than rejected. A `422` here would break any client that sends a field this version does not know. |
| Preconditions | Account A signed in with `name = "Мария Соколова"`; the full row recorded. |
| Test data | Body `{"name": "Мария Волкова", "nickname": "мася", "theme": "dark", "locale": "ru"}` |
| Steps | 1. Record account A's full row.<br>2. `PATCH /api/v1/auth/me` with the body above.<br>3. Re-read the full row in a new session. |
| Expected result | `200 OK` with `"name": "Мария Волкова"` — not `400`, not `422`; step 3 shows only `name` changed, every other column byte-equal to step 1; no `nickname`/`theme`/`locale` column or JSON blob is written anywhere. |
| Status | Not run |

### TC-13-API-1.3e — A body that is legal in size but pathological in shape is bounded in cost

| Field | Value |
|---|---|
| Description | TC-13-API-1.2e makes unknown keys legal and ignored, which is the right contract and also the opening: a body well under the size cap can still be arbitrarily expensive to parse, on the product's highest-rate endpoint. The size cap bounds bytes, not shape. |
| Preconditions | Account A signed in; a second caller issuing ordinary `GET /api/v1/auth/me` requests once per second throughout. |
| Test data | (a) `{"name": "Мария Волкова", "x": [[[[…]]]]}` nested 100 000 deep, total size ~1 MiB (under the 2 MiB cap). (b) `{"name": "Мария Волкова", "k1": 1, …, "k50000": 1}`, ~800 KiB. Wall-clock bound: 5 s per request. |
| Steps | 1. Start the concurrent 1 req/s `GET /me` driver and record its baseline latency.<br>2. Send body (a); record the status and wall-clock duration.<br>3. Send body (b); record the status and duration.<br>4. Read the concurrent driver's latencies and statuses during steps 2–3. |
| Expected result | Each of (a) and (b) either is refused (`400`/`413`/`422` in a defined shape) or completes within 5 s — never hangs and never crashes the worker; during both, the concurrent `GET /me` calls all answer `200` with latency no more than 2× the step-1 baseline, and none times out. |
| Status | Not run |

---

## 2. Name Content Edges

### TC-13-API-2.1e — A grapheme cluster spanning several code points is bounded as written

| Field | Value |
|---|---|
| Description | The bound is code points, not graphemes; a ZWJ family emoji is one rendered character and seven code points, and neither a grapheme-counting bound nor a ZWJ-stripping normalizer is correct here. |
| Preconditions | Account A signed in. |
| Test data | `{"name": "👨‍👩‍👧‍👦👨‍👩‍👧‍👦…"}` — ZWJ family sequences totalling exactly 60 code points (8 full clusters of 7 code points plus a 4-code-point remainder). |
| Steps | 1. `PATCH /api/v1/auth/me` with the 60-code-point ZWJ value.<br>2. Re-read account A's row in a new session and compare code point by code point. |
| Expected result | `200 OK`; the stored value equals the sent value exactly, 60 code points, with every U+200D zero-width joiner preserved — no cluster split, no ZWJ stripped as an invisible character. |
| Status | Not run |

### TC-13-API-2.2e — Interior whitespace is preserved while surrounding whitespace is trimmed

| Field | Value |
|---|---|
| Description | A blanket whitespace-collapse would rewrite a legitimate name; a missing trim leaves a value the client's dirty flag can never match. |
| Preconditions | Account A signed in. |
| Test data | `{"name": "  Мария   Соколова  "}` — two leading spaces, three interior, two trailing. |
| Steps | 1. `PATCH /api/v1/auth/me` with that value.<br>2. Read the response `name`.<br>3. Re-read account A's row in a new session. |
| Expected result | `200 OK`; both the response and the stored value are exactly `Мария   Соколова` — the three interior spaces preserved, no leading or trailing whitespace, and not collapsed to a single space. |
| Status | Not run |

### TC-13-API-2.3e — A name of a single character is accepted

| Field | Value |
|---|---|
| Description | There is no lower bound above zero: a "1..60" reading that refuses short values would also contradict the tri-state clearing rule. |
| Preconditions | Account A signed in. |
| Test data | `{"name": "М"}` |
| Steps | 1. `PATCH /api/v1/auth/me` with `{"name": "М"}`.<br>2. Re-read account A's row in a new session. |
| Expected result | `200 OK` with `"name": "М"`; the stored value is exactly `М` — not refused, not padded, not cleared. |
| Status | Not run |

### TC-13-API-2.4e — Renaming to the value already stored is accepted and changes nothing

| Field | Value |
|---|---|
| Description | A rename to the value already held is a success, not a no-op to be refused with `400` or `409`. |
| Preconditions | Account A signed in with stored `name = "Мария Соколова"`. |
| Test data | `{"name": "Мария Соколова"}` |
| Steps | 1. `PATCH /api/v1/auth/me` with the identical name.<br>2. Read the response.<br>3. Re-read account A's row in a new session. |
| Expected result | `200 OK` with `"name": "Мария Соколова"` — never `304`, `400` or `409`; the stored value is still `Мария Соколова`. |
| Status | Not run |

### TC-13-API-2.5e — Clearing a name that was never set is accepted

| Field | Value |
|---|---|
| Description | A clear on an account that had no name is a success, not a no-op to be refused — and it must not write `''` in place of `NULL`. |
| Preconditions | Account C signed in, `name = NULL`, never renamed. |
| Test data | `{"name": ""}` and `{"name": null}`. |
| Steps | 1. `PATCH /api/v1/auth/me` as account C with `{"name": ""}`.<br>2. Re-read account C's row in a new session.<br>3. Repeat with `{"name": null}` and re-read. |
| Expected result | Both answer `200 OK` with `"name": null`; both fresh reads show `name IS NULL` — never `''`, never an error. |
| Status | Not run |

---

## 3. Last-Write-Wins, Observed

### TC-13-API-3.1e — The later rename wins and the earlier one is silently lost

| Field | Value |
|---|---|
| Description | Recorded so last-write-wins reads as the decision it is (`endpoints.md`), not as a missed hazard. Note this is not a concurrency guard — issuing two renames together serializes. |
| Preconditions | Account A signed in; two independent clients each holding a valid access token for account A. |
| Test data | Client 1 sends `{"name": "Мария Волкова"}`; client 2 then sends `{"name": "Мария Орлова"}`. |
| Steps | 1. Client 1 `PATCH /api/v1/auth/me` with `Мария Волкова`; record the status.<br>2. Client 2 `PATCH /api/v1/auth/me` with `Мария Орлова`; record the status.<br>3. Re-read account A's row in a new session. |
| Expected result | Both answer `200 OK` — neither is refused with `409`, and neither response carries a conflict or version field; the stored value is `Мария Орлова`; `Мария Волкова` is gone with no record of it. |
| Status | Not run |

### TC-13-API-3.2e — A stale client can clear a name another client just set

| Field | Value |
|---|---|
| Description | Because clearing is first-class, a stale tab can *undo* a rename rather than merely overwrite it. Accepted for a display name, and written down so it is not read as a missed hazard. |
| Preconditions | Account A signed in from two clients; client 2 loaded its snapshot while `name` was `NULL` and has not refreshed. |
| Test data | Client 1 sends `{"name": "Мария Волкова"}`; client 2 then sends `{"name": null}`. |
| Steps | 1. Client 1 `PATCH /api/v1/auth/me` with `{"name": "Мария Волкова"}`.<br>2. Client 2, still believing the name is unset, `PATCH`es `{"name": null}`.<br>3. Re-read account A's row in a new session. |
| Expected result | Both answer `200 OK`; client 2's response carries `"name": null`; the stored `name IS NULL` — client 1's rename is undone, with no conflict reported to either. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the profile path` | `/api/v1/auth/me` |
| `joined emoji` | ZWJ sequence — several code points, one rendered grapheme |
| `the bound` | 60 code points after trim + NFC |
| `a fresh read of the stored profile` | Re-read through a new session against real Postgres |
