<!-- COPIED FILE. Source of truth: ProductSpecification/stories/10-editor-pages/tests/01_API_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> **Implementation Order**: sequential TDD — ownership guards → read semantics →
> write validation → write semantics (tri-state, replace, CAS) → export applies settings.

# Editor pages — API Tests

Endpoints: `GET`/`PUT /api/v1/documents/{id}` (extended with `page_settings`),
`GET /api/v1/documents/{id}/export` (contract unchanged, behaviour extended).
Contracts: `ProductSpecification/api-specs/documents_get.yaml`, `documents_save.yaml`,
`documents_export.yaml`.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.pages@textery.test` / `Qa!Pages2026` |
| Account B (a stranger) | `qa.stranger@textery.test` / `Qa!Stranger2026` |
| Access token | `Authorization: Bearer <access token of account A>` |
| Document A1 (unconfigured) | id `9d4b1e7a-3c62-4f08-b5d1-8e2a70c4f159`, title `Курсовая работа`, content `<p>Первый абзац.</p>`, `version` `3`, `page_settings` `null` |
| Document A2 (configured) | id `c31f8a05-6d47-4b92-8e10-2f5c9d7b3a64`, `version` `7`, settings `S1` below |
| Document B1 (owned by B) | id `2c9a77e0-51b4-4b1e-8f0a-6d3c9b2a4e18` |
| Absent id | `00000000-0000-4000-8000-000000000000` |
| Settings `S1` (self-distinct) | `{"page_size":"A5","orientation":"landscape","margins_mm":{"top":35,"right":15,"bottom":25,"left":40},"font_size_pt":11,"line_height":1.15,"header_text":"Кафедра ИВТ","footer_text":"Текстери","show_page_numbers":true,"skip_number_on_first_page":false}` |
| Default preset (what `null` renders as) | A4, portrait, margins 20/15/20/30 mm, `font_size_pt` 14, `line_height` 1.5, `show_page_numbers` true, `skip_number_on_first_page` true |
| Error body shape | `{"error_code": "<CODE>", "message": "<generic text>"}` |
| 404 body | `{"error_code": "NOT_FOUND", "message": "The requested resource was not found."}` |
| 409 body | `{"error_code": "VERSION_CONFLICT", "message": "The document was modified by another save. Refetch and retry."}` |
| 500 body | `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}` |

## 1. Ownership Guards

### TC-10-API-1.1 — Page settings of a non-existent document are refused

| Field | Value |
|---|---|
| Description | Reading geometry must not become a second, weaker path to a document — an absent id has to fail exactly like every other document read. |
| Preconditions | Account A signed in; no document exists with the id below. |
| Test data | `document_id = 00000000-0000-4000-8000-000000000000` |
| Steps | 1. `GET /api/v1/documents/00000000-0000-4000-8000-000000000000` with account A's Bearer token. |
| Expected result | `404 Not Found`; `Content-Type: application/json`; body exactly `{"error_code": "NOT_FOUND", "message": "The requested resource was not found."}`; no `page_settings` key and no document fields in the body. |
| Status | Not run |

### TC-10-API-1.2 — Another account's page settings are refused indistinguishably

| Field | Value |
|---|---|
| Description | A `403`, or any body that differs from the absent-id body, confirms the id exists — on read, on write, and on export alike. |
| Preconditions | Document B1 exists and is owned by account B; account A signed in. |
| Test data | Document B1 id `2c9a77e0-51b4-4b1e-8f0a-6d3c9b2a4e18`; save body `{"content":"<p>x</p>","version":1,"page_settings":<S1>}`; `format=pdf` |
| Steps | 1. `GET /api/v1/documents/2c9a77e0-51b4-4b1e-8f0a-6d3c9b2a4e18` with account A's token.<br>2. `PUT /api/v1/documents/2c9a77e0-51b4-4b1e-8f0a-6d3c9b2a4e18` with the save body above.<br>3. `GET /api/v1/documents/2c9a77e0-51b4-4b1e-8f0a-6d3c9b2a4e18/export?format=pdf`.<br>4. Repeat steps 1–3 against the absent id and compare each pair of responses. |
| Expected result | All three answer `404 Not Found`, never `403` and never `409`; each body is exactly the 404 body; each response is byte-identical (headers bar `Date`, and body) to its absent-id counterpart. |
| Status | Not run |

---

## 2. Read Semantics

### TC-10-API-2.1 — A never-configured document reads as unconfigured, not as the defaults

| Field | Value |
|---|---|
| Description | If the server materializes the preset into the response, "never configured" and "configured to today's preset" become indistinguishable and a later preset change can never reach old documents. |
| Preconditions | Document A1 exists, owned by account A, `page_settings` column is SQL `NULL`. |
| Test data | Document A1 id `9d4b1e7a-3c62-4f08-b5d1-8e2a70c4f159` |
| Steps | 1. `GET /api/v1/documents/9d4b1e7a-3c62-4f08-b5d1-8e2a70c4f159` with account A's token. |
| Expected result | `200 OK`; the body contains the key `page_settings` with the JSON value `null` — the key is present, its value is not an object; no `page_size`, `margins_mm`, `font_size_pt` or any other geometry key appears anywhere in the body. |
| Status | Not run |

### TC-10-API-2.2 — Stored page settings round-trip unchanged

| Field | Value |
|---|---|
| Description | A dropped or re-defaulted key on the read path would silently hand the client a geometry it never chose. |
| Preconditions | Document A2 exists, owned by account A, saved with settings `S1`. |
| Test data | Settings `S1` (all nine keys, every value non-default and distinct) |
| Steps | 1. `GET /api/v1/documents/c31f8a05-6d47-4b92-8e10-2f5c9d7b3a64` with account A's token. |
| Expected result | `200 OK`; `page_settings` equals `S1` field for field: `page_size` `A5`, `orientation` `landscape`, `margins_mm` `{top:35,right:15,bottom:25,left:40}`, `font_size_pt` `11`, `line_height` `1.15`, `header_text` `Кафедра ИВТ`, `footer_text` `Текстери`, `show_page_numbers` `true`, `skip_number_on_first_page` `false`. |
| Status | Not run |

### TC-10-API-2.3 — A stored object missing a later-added key reads as that key's default

| Field | Value |
|---|---|
| Description | Rows written before a key existed must not crash the read or downgrade the keys that were stored. |
| Preconditions | Document A3 exists, owned by account A; its `page_settings` JSONB was written directly to the DB without `skip_number_on_first_page`. |
| Test data | Document A3 id `4e70c9b2-18da-4a5f-9c33-7b60e1d4a2f8`; stored JSONB `{"page_size":"A5","orientation":"landscape","margins_mm":{"top":35,"right":15,"bottom":25,"left":40},"font_size_pt":11,"line_height":1.15,"header_text":"Кафедра ИВТ","footer_text":"Текстери","show_page_numbers":true}` |
| Steps | 1. `GET /api/v1/documents/4e70c9b2-18da-4a5f-9c33-7b60e1d4a2f8` with account A's token. |
| Expected result | `200 OK`; `skip_number_on_first_page` reads `true` (its default); `page_size` still `A5`, `font_size_pt` still `11`, `line_height` still `1.15`, `header_text` still `Кафедра ИВТ` — no stored key is reset. |
| Status | Not run |

### TC-10-API-2.4 — A stored object carrying an undefined key or constant is read, not rejected

| Field | Value |
|---|---|
| Description | A row written by a newer release must not make the document unreadable on an older one, and must not take the whole object down with the one part that is unknown. |
| Preconditions | Documents A4 and A5 exist, owned by account A, with JSONB written directly to the DB. |
| Test data | A4 id `b0c62d18-4f39-4e7a-9d51-3a8f75c2e604`, stored JSONB = `S1` plus `"gutter_mm": 12`.<br>A5 id `6f13ae95-7c20-4b88-a4e6-51d0937bc27f`, stored JSONB = `S1` with `"page_size": "B5"`. |
| Steps | 1. `GET /api/v1/documents/b0c62d18-4f39-4e7a-9d51-3a8f75c2e604`.<br>2. `GET /api/v1/documents/6f13ae95-7c20-4b88-a4e6-51d0937bc27f`.<br>3. Re-read the `page_settings` column of both rows directly from the DB. |
| Expected result | Both reads answer `200 OK`, neither `422` nor `500`. A4's response omits `gutter_mm` and every other key equals `S1`. A5's response reports `page_size` `A4` (the default) while `orientation`, `margins_mm`, `font_size_pt`, `line_height`, `header_text`, `footer_text` and both flags still equal `S1`. Step 3 shows both stored rows unchanged — `gutter_mm` and `B5` are still in the column. |
| Status | Not run |

---

## 3. Write Validation

Every scenario here asserts rejection **at the boundary** — never a clamp, never a partial
application. Every rejection is `422 Unprocessable Entity` with the generic
`{"error_code", "message"}` body and nothing else.

### TC-10-API-3.1 — An unknown key inside page settings is rejected

| Field | Value |
|---|---|
| Description | Unknown keys inside `page_settings` are deliberately stricter than unknown top-level fields: the object is re-serialized from a validated value object, so a silently dropped key would read back as a default the client never asked for. |
| Preconditions | Document A2 exists, owned by account A, at `version` `7`, with settings `S1` stored. |
| Test data | `PUT` body `{"content":"<p>Первый абзац.</p>","version":7,"page_settings":{<S1 keys>, "gutter_mm":12}}` |
| Steps | 1. `PUT /api/v1/documents/c31f8a05-6d47-4b92-8e10-2f5c9d7b3a64` with that body.<br>2. `GET` the same document. |
| Expected result | Step 1: `422 Unprocessable Entity` with the `{"error_code","message"}` body and no document fields. Step 2: `page_settings` still equals `S1` and `version` is still `7`. |
| Status | Not run |

### TC-10-API-3.2 — An unknown sheet size or orientation is rejected

| Field | Value |
|---|---|
| Description | `page_size` and `orientation` are closed enums; an unknown constant must fail rather than fall back to a default the caller did not choose. |
| Preconditions | Document A2 exists, owned by account A, at `version` `7`. |
| Test data | (a) `page_size: "B5"`; (b) `page_size: "a4"` (wrong case); (c) `orientation: "diagonal"` — each sent with the remaining `S1` keys valid and `version: 7`. |
| Steps | 1. `PUT` document A2 with variant (a).<br>2. `PUT` document A2 with variant (b).<br>3. `PUT` document A2 with variant (c). |
| Expected result | Each of the three answers `422 Unprocessable Entity` with the generic error body; no response is `200`; document A2's stored `page_settings` and `version` are unchanged after all three. |
| Status | Not run |

### TC-10-API-3.3 — Numeric bounds are inclusive and rejected one step outside

| Field | Value |
|---|---|
| Description | An exclusive-by-mistake bound rejects a legitimate 8 pt or 3.0 line height; a missing bound accepts a 500 pt font. Both edges are pinned. |
| Preconditions | Document A2 exists, owned by account A; refetch `version` before each `PUT`. |
| Test data | Accepted: `font_size_pt` `8` and `72`; `line_height` `1.0` and `3.0`. Rejected: `font_size_pt` `7.9` and `72.1`; `line_height` `0.99` and `3.01`. Margins for the accepted 72 pt case: A4 portrait 20/15/20/30 mm. |
| Steps | 1. `PUT` document A2 with `font_size_pt: 8`, then with `font_size_pt: 72`.<br>2. `PUT` with `line_height: 1.0`, then with `line_height: 3.0`.<br>3. `PUT` with `font_size_pt: 7.9`, then `72.1`.<br>4. `PUT` with `line_height: 0.99`, then `3.01`. |
| Expected result | Steps 1–2: each answers `200 OK` and the response echoes the exact value sent (`8`, `72`, `1.0`, `3.0`) — not a clamped one. Steps 3–4: each answers `422` with the generic error body and leaves the previously stored value in place. |
| Status | Not run |

### TC-10-API-3.4 — Margins that leave no content box are rejected at the exact equality

| Field | Value |
|---|---|
| Description | Equality is the boundary a `>` comparison gets wrong: opposing margins summing to exactly the sheet dimension give a zero-width box, and a zero-width box paginates forever. |
| Preconditions | Document A2 exists, owned by account A; `page_size: A4`, `orientation: portrait` (width 210 mm). |
| Test data | Rejected: `margins_mm {top:20,right:90,bottom:20,left:120}` (90 + 120 = 210). Accepted: `margins_mm {top:20,right:89,bottom:20,left:120}` (= 209). |
| Steps | 1. `PUT` document A2 with the 90/120 margins and the current `version`.<br>2. Refetch `version`, then `PUT` with the 89/120 margins. |
| Expected result | Step 1: `422` with the generic error body; the stored margins are unchanged and are not clamped to a fitting value. Step 2: `200 OK` and the response echoes `right: 89`, `left: 120`. |
| Status | Not run |

### TC-10-API-3.5 — Geometry whose content box cannot hold one line is rejected

| Field | Value |
|---|---|
| Description | A box that is positive but shorter than a single line satisfies every per-field rule and still makes pagination emit pages without end. The rule is on the combination, not the fields. |
| Preconditions | Document A2 exists, owned by account A. |
| Test data | `{"page_size":"A5","orientation":"landscape","margins_mm":{"top":70,"right":10,"bottom":74,"left":10},"font_size_pt":11,"line_height":1.15,...}` — A5 landscape height 148 mm, vertical margins 144 mm, box 4 mm, one line ≈ 4.46 mm. |
| Steps | 1. `PUT` document A2 with that object and the current `version`.<br>2. Inspect the server log and any layout/render counter for the request. |
| Expected result | `422 Unprocessable Entity` with the generic error body; no pagination or render is invoked for the request (zero layout/render log records, no render worker taken); the stored `page_settings` and `version` are unchanged. |
| Status | Not run |

### TC-10-API-3.6 — Malformed numbers are rejected

| Field | Value |
|---|---|
| Description | `NaN`, `Infinity`, an overflowing literal and a numeric string are the four ways a number field stops being a number; any of them reaching the stylesheet or the DB is a corrupt document. |
| Preconditions | Document A2 exists, owned by account A. |
| Test data | (a) `margins_mm.top: -1`; (b) `line_height: NaN` and `font_size_pt: Infinity` (raw JSON tokens); (c) `font_size_pt: 1e400`; (d) `font_size_pt: "14"` and `margins_mm.left: "30mm"`. |
| Steps | 1. `PUT` document A2 with each variant (a)–(d) in turn, current `version` each time. |
| Expected result | Every variant answers `422 Unprocessable Entity` with the `{"error_code","message"}` body; none answers `200`, `400` or `500`; the stored `page_settings` is unchanged after all of them. |
| Status | Not run |

### TC-10-API-3.7 — An over-length header or footer is rejected, never truncated

| Field | Value |
|---|---|
| Description | Truncating a running head silently publishes a header the user did not write; the limit is 200 code points on the NFC form, not 200 bytes. |
| Preconditions | Document A2 exists, owned by account A. |
| Test data | Over-length: `header_text` = `Ё` × 201 (201 code points, 402 UTF-8 bytes). At the limit: `header_text` = `Ё` × 200. |
| Steps | 1. `PUT` document A2 with the 201-character header and the current `version`.<br>2. `GET` document A2 and read `page_settings.header_text`.<br>3. Refetch `version`, `PUT` with the 200-character header.<br>4. `GET` document A2 again. |
| Expected result | Step 1: `422` with the generic error body. Step 2: the stored header is the previous value — no 200-character prefix of the submission was stored. Step 3: `200 OK`. Step 4: `header_text` is exactly 200 `Ё` characters. |
| Status | Not run |

### TC-10-API-3.8 — A rejected request leaves the content byte-identical

| Field | Value |
|---|---|
| Description | A `PUT` is one transaction: content applied first and geometry rejected after would leave the user with a save they were told had failed. |
| Preconditions | Document A2 exists, owned by account A, content `<p>Первый абзац.</p>`, `version` `7`. |
| Test data | Body `{"content":"<p>Совершенно новый абзац.</p>","version":7,"page_settings":{...,"font_size_pt":500}}` |
| Steps | 1. `GET` document A2 and record `content`, `version` and `updated_at`.<br>2. `PUT` document A2 with the body above.<br>3. `GET` document A2 again. |
| Expected result | Step 2: `422` with the generic error body. Step 3: `content` is byte-identical to step 1 (`<p>Первый абзац.</p>`, not the new paragraph), `version` is still `7`, `page_settings` unchanged. |
| Status | Not run |

---

## 4. Write Semantics

### TC-10-API-4.1 — Omitted page settings leave the stored value untouched

| Field | Value |
|---|---|
| Description | Every autosave keystroke sends content only. If an omitted field were read as "clear", the editor would wipe the user's page setup within seconds of them configuring it. |
| Preconditions | Document A2 exists, owned by account A, with settings `S1` stored, `version` `7`. |
| Test data | Body `{"content":"<p>Второй абзац.</p>","version":7}` — the key `page_settings` is absent from the JSON entirely. |
| Steps | 1. `PUT /api/v1/documents/c31f8a05-6d47-4b92-8e10-2f5c9d7b3a64` with that body.<br>2. `GET` the same document. |
| Expected result | Step 1: `200 OK`; the response's `page_settings` equals `S1` and `version` is `8`. Step 2: `page_settings` still equals `S1` key for key and `content` is the new paragraph. |
| Status | Not run |

### TC-10-API-4.2 — Explicit absence resets the page settings to the default preset

| Field | Value |
|---|---|
| Description | The reset must return the row to `NULL` — writing a materialized default object instead would freeze today's preset into the document. |
| Preconditions | Document A2 exists with settings `S1`, `version` `8`. |
| Test data | Body `{"content":"<p>Второй абзац.</p>","version":8,"page_settings":null}` |
| Steps | 1. `PUT` document A2 with that body.<br>2. `GET` document A2.<br>3. Read the `page_settings` column of the row directly from the DB. |
| Expected result | Step 1: `200 OK`, response `page_settings` is `null`. Step 2: `page_settings` is `null`, not an object of preset values. Step 3: the column holds SQL `NULL`. |
| Status | Not run |

### TC-10-API-4.3 — A supplied object replaces the stored one wholesale

| Field | Value |
|---|---|
| Description | Per-key merging is the plausible wrong implementation; the contract is replace, so an omitted `header_text` clears the header rather than preserving it. |
| Preconditions | Document A2 exists with settings `S1` (`header_text` = `Кафедра ИВТ`, `footer_text` = `Текстери`). |
| Test data | Supplied object = `S1` with the `header_text` key removed entirely, all other keys present and unchanged. |
| Steps | 1. `PUT` document A2 with that object and the current `version`.<br>2. `GET` document A2. |
| Expected result | Step 1: `200 OK`. Step 2: `header_text` is `null` — not `Кафедра ИВТ`; `footer_text` is still `Текстери` and every supplied key still carries its supplied value. |
| Status | Not run |

### TC-10-API-4.4 — Only allow-listed keys are persisted

| Field | Value |
|---|---|
| Description | Storing the request blob verbatim would let anything the caller sends ride into the JSONB column and back out on the next read. |
| Preconditions | Document A2 exists, owned by account A. |
| Test data | Valid `S1`, sent inside a body that also carries the top-level server-owned fields `{"document_type":"generated","status":"published","id":"<other uuid>"}` |
| Steps | 1. `PUT` document A2 with that body and the current `version`.<br>2. Read the `page_settings` column of the row directly from the DB and list its top-level keys. |
| Expected result | Step 1: `200 OK` (unknown TOP-LEVEL fields are ignored, unlike unknown keys inside `page_settings`); `document_type` and `status` in the response are unchanged. Step 2: the column holds exactly the nine keys `page_size`, `orientation`, `margins_mm`, `font_size_pt`, `line_height`, `header_text`, `footer_text`, `show_page_numbers`, `skip_number_on_first_page` — no tenth key, no `document_type`, no raw request fragment. |
| Status | Not run |

### TC-10-API-4.5 — Header text is normalized and round-trips byte-exact

| Field | Value |
|---|---|
| Description | Normalizing on write but not on read (or the reverse) makes the stored bytes and the returned bytes differ, which breaks every byte comparison downstream, including the export. |
| Preconditions | Document A2 exists, owned by account A. |
| Test data | `header_text` submitted as `Отчёт e` + U+0301 + ` 🎓` (decomposed accent, one emoji, Cyrillic); its NFC form is `Отчёт é 🎓`. |
| Steps | 1. `PUT` document A2 with that `header_text` and the current `version`.<br>2. Read the column directly from the DB and hex-dump `header_text`.<br>3. `GET` document A2 and hex-dump the returned `header_text`. |
| Expected result | Step 1: `200 OK`. Step 2: the stored bytes are the NFC form — `é` is the single code point U+00E9 and no standalone U+0301 remains. Step 3: the returned bytes are identical to the stored bytes and the emoji and Cyrillic are intact (no `?`, no U+FFFD). |
| Status | Not run |

### TC-10-API-4.6 — A stale version is refused on a page-settings save

| Field | Value |
|---|---|
| Description | Settings ride the same version CAS as content; without it the second writer blindly overwrites the first writer's geometry. |
| Preconditions | Document A2 exists at `version` `7`; two clients have both read it at `version` `7`. |
| Test data | Writer 1 sends `S1` with `version: 7`. Writer 2 sends `S1` with `font_size_pt: 20` and `version: 7`. |
| Steps | 1. Writer 1 `PUT`s document A2 with `version: 7`.<br>2. Writer 2 `PUT`s document A2 with `version: 7`.<br>3. `GET` document A2. |
| Expected result | Step 1: `200 OK`, response `version` `8`. Step 2: `409 Conflict` with body `{"error_code": "VERSION_CONFLICT", "message": "The document was modified by another save. Refetch and retry."}`. Step 3: `font_size_pt` is `11` (writer 1's value), `version` is `8`. |
| Status | Not run |

### TC-10-API-4.7 — Replaying an identical save applies it once

| Field | Value |
|---|---|
| Description | A client that retries after a timeout must not end up with a different document than one that did not retry. |
| Preconditions | Document A2 exists at a known `version` `7` with known content. |
| Test data | Byte-identical body `{"content":"<p>Первый абзац.</p>","version":7,"page_settings":<S1>}` sent twice. |
| Steps | 1. `PUT` document A2 with the body.<br>2. `PUT` document A2 with the byte-identical body again.<br>3. `GET` document A2. |
| Expected result | Step 1: `200 OK`. Step 2: either `200 OK` (idempotent replay) or `409` with the version-conflict body — never a second, different mutation. Step 3: `content` and `page_settings` equal exactly what a single application produces; `page_settings` equals `S1` and is not doubled, merged or altered. |
| Status | Not run |

### TC-10-API-4.8 — A content save and a settings save do not silently drop each other

| Field | Value |
|---|---|
| Description | Two writers on one row under one version token is exactly where a lost update hides: whichever loses must be told so, not quietly discarded. |
| Preconditions | Document A2 exists at `version` `7`; client C reads it (content save) and client S reads it (settings save), both at `version` `7`. |
| Test data | C sends `{"content":"<p>Правка C.</p>","version":7}`. S sends `{"content":"<p>Первый абзац.</p>","version":7,"page_settings":<S1 with font_size_pt 20>}`. The pair is then repeated in the reverse issue order. |
| Steps | 1. Issue C's and S's `PUT`s concurrently against document A2.<br>2. Record the status of each.<br>3. `GET` document A2 and compare with each submission.<br>4. Repeat steps 1–3 with the order reversed. |
| Expected result | In each run exactly one `PUT` answers `200 OK` and the other answers `409` with the version-conflict body; `version` advances by exactly `1`; the stored state matches the `200` writer's submission in full — the losing writer's content or geometry appears nowhere in the row, and no field of the winning writer's submission was dropped. |
| Status | Not run |

---

## 5. Export Applies the Settings

### TC-10-API-5.1 — An export immediately after a settings save reflects the new geometry

| Field | Value |
|---|---|
| Description | An export reading a stale row hands the user the previous geometry seconds after they changed it — the failure looks like "the setting didn't work". |
| Preconditions | Document A1 exists, owned by account A, content `<p>Первый абзац.</p>`. |
| Test data | Settings `S1` (A5 landscape, header `Кафедра ИВТ`); export issued < 1 s after the save. |
| Steps | 1. `PUT /api/v1/documents/9d4b1e7a-3c62-4f08-b5d1-8e2a70c4f159` with `S1` and the current `version`.<br>2. Within 1 s, `GET /api/v1/documents/9d4b1e7a-3c62-4f08-b5d1-8e2a70c4f159/export?format=pdf`.<br>3. Read the PDF's `/MediaBox` and its text layer. |
| Expected result | Step 2: `200 OK`, `Content-Type: application/pdf`. Step 3: page size is 210 × 148 mm (A5 landscape, ±0.5 mm), not 210 × 297; the header area carries the literal text `Кафедра ИВТ`; the footer carries `Текстери`. |
| Status | Not run |

### TC-10-API-5.2 — Manual page breaks are honoured in both formats

| Field | Value |
|---|---|
| Description | The break is content, and both renderers have to turn it into a real page boundary rather than a stray empty element. |
| Preconditions | Document A6 exists, owned by account A, containing a manual page break between two paragraphs. |
| Test data | Document A6 id `1a5cd4e8-9b37-4c60-8f22-e07b6d1934ca`, content `<p>До разрыва.</p><div data-page-break="true"></div><p>После разрыва.</p>` |
| Steps | 1. `GET /api/v1/documents/1a5cd4e8-9b37-4c60-8f22-e07b6d1934ca/export?format=pdf` and read the per-page text.<br>2. `GET .../export?format=docx` and read `word/document.xml`. |
| Expected result | Step 1: `200 OK`; the PDF has at least 2 pages; `До разрыва.` is on page 1 and `После разрыва.` begins page 2 — they are never on the same page. Step 2: `200 OK`; `word/document.xml` carries `<w:br w:type="page"/>` between the two paragraph runs, with `После разрыва.` following it. |
| Status | Not run |

### TC-10-API-5.3 — A default-settings document exports exactly as it did before this story

| Field | Value |
|---|---|
| Description | The regression guard for story 17: a document that opts into nothing must produce the same output it produced before page settings existed. |
| Preconditions | Document A1 exists with `page_settings` `null` and no manual break; the reference PDF and DOCX produced before this story are stored as fixtures. |
| Test data | Reference fixtures `story17_reference.pdf` and `story17_reference.docx` for document A1's content |
| Steps | 1. Export document A1 as `pdf` and compare with `story17_reference.pdf`.<br>2. Export document A1 as `docx` and compare `word/document.xml` and `word/settings.xml` with the reference. |
| Expected result | Both answer `200 OK`; the PDF's page count, `/MediaBox` and extracted text are identical to the reference; the DOCX's section geometry and body XML are identical to the reference, ignoring only render timestamps; no header or footer part is present in either file. |
| Status | Not run |

### TC-10-API-5.4 — A partially applicable render fails instead of dropping an element

| Field | Value |
|---|---|
| Description | A `200` with the header silently missing is a wrong document that looks right — the user has no signal to check. Failing loudly is the only safe outcome. |
| Preconditions | Document A7 exists, owned by account A; each of the four render steps can be forced to fail with a seeded fault. |
| Test data | Document A7 id `d92b7f31-06ae-4c15-b7a3-4e58c1d206bf`; forced faults on geometry application, manual-break emission, header/footer emission, and page numbering. |
| Steps | 1. Export document A7 as `pdf` with the geometry fault seeded.<br>2. Repeat with the manual-break fault.<br>3. Repeat with the header/footer fault.<br>4. Repeat with the numbering fault.<br>5. Repeat all four as `docx`. |
| Expected result | Every one of the eight calls answers `500` with body exactly `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}`; no response body carries file bytes and no `Content-Disposition` header is sent; in no case is a `200` returned with the failing element absent from the file. |
| Status | Not run |

### TC-10-API-5.5 — An unresolvable document font fails the export rather than substituting metrics

| Field | Value |
|---|---|
| Description | The render library substitutes a fallback face on a per-resource failure and continues, producing a successful export whose line breaks and page count are all wrong. |
| Preconditions | Document A1 exists; the bundled Liberation Serif asset is made unreadable for the duration of the render. |
| Test data | Document A1; font asset renamed or permission-denied at render time |
| Steps | 1. `GET /api/v1/documents/9d4b1e7a-3c62-4f08-b5d1-8e2a70c4f159/export?format=pdf`.<br>2. Inspect the response body length and the server log. |
| Expected result | `500` with body exactly `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}`; zero file bytes are returned; the server log carries exactly one error-level record naming document A1's id; no PDF laid out in a substitute face is produced. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `an authenticated user` | Valid access-token Bearer header |
| `reads / saves page settings` | `GET` / `PUT /api/v1/documents/{id}` with the `page_settings` object |
| `saves content without mentioning page settings` | `PUT` body omitting the `page_settings` key entirely |
| `page settings explicitly cleared` | `PUT` body with `page_settings: null` |
| `refused as unprocessable` | HTTP 422 with the generic `{error_code, message}` body |
| `refused as not found` | HTTP 404, identical body for absent and foreign |
| `refused as a conflict` | HTTP 409 from the version CAS |
| `the persisted object` | The `page_settings` JSONB column read directly from the DB |
| `normalized form` | NFC |
| `exports the document` | `GET /api/v1/documents/{id}/export?format=pdf\|docx` |
| `the sanctioned error` | HTTP 500 with the generic client-safe body, no internals |
