<!-- COPIED FILE. Source of truth: ProductSpecification/stories/10-editor-pages/tests/extended/01_API_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Editor pages — API Tests (Extended)

Endpoints: `GET`/`PUT /api/v1/documents/{id}`, `GET /api/v1/documents/{id}/export`.
Contracts: `ProductSpecification/api-specs/documents_get.yaml`, `documents_save.yaml`.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.pages@textery.test` / `Qa!Pages2026` |
| Access token | `Authorization: Bearer <access token of account A>` |
| Document A2 (configured) | id `c31f8a05-6d47-4b92-8e10-2f5c9d7b3a64`, `version` `7`, settings `S1` |
| Settings `S1` | `{"page_size":"A5","orientation":"landscape","margins_mm":{"top":35,"right":15,"bottom":25,"left":40},"font_size_pt":11,"line_height":1.15,"header_text":"Кафедра ИВТ","footer_text":"Текстери","show_page_numbers":true,"skip_number_on_first_page":false}` |
| Limits | content ≤ 200 000 code points; `header_text`/`footer_text` ≤ 200 code points |
| 409 body | `{"error_code": "VERSION_CONFLICT", "message": "The document was modified by another save. Refetch and retry."}` |
| Error body shape | `{"error_code": "<CODE>", "message": "<generic text>"}` |

## 1. Page Settings Edges

### TC-10-API-1.1 — Zero margins are accepted

| Field | Value |
|---|---|
| Description | `minimum: 0` is inclusive; a `> 0` check would reject a legitimate borderless layout, and the content box must then equal the whole sheet rather than a clamped inset. |
| Preconditions | Document A2 exists, owned by account A, `page_size` `A4`, `orientation` `portrait`. |
| Test data | `margins_mm {top:0,right:0,bottom:0,left:0}`, A4 portrait (210 × 297 mm), 11 pt, line height 1.15 |
| Steps | 1. `PUT /api/v1/documents/c31f8a05-6d47-4b92-8e10-2f5c9d7b3a64` with those margins and the current `version`.<br>2. `GET` document A2.<br>3. Export document A2 as `pdf` and measure the text frame. |
| Expected result | Step 1: `200 OK`. Step 2: all four margins read back exactly `0` — not clamped to a minimum. Step 3: the PDF's content frame is 210 × 297 mm (±0.5 mm), equal to the full sheet. |
| Status | Not run |

### TC-10-API-1.2 — An empty header text is distinguishable from an absent one

| Field | Value |
|---|---|
| Description | `""` and `null` are different intents — "a header exists and is blank" versus "no header" — and collapsing them loses the user's choice on the next read. |
| Preconditions | Document A2 exists, owned by account A, with `header_text` `Кафедра ИВТ` stored. |
| Test data | `header_text: ""` in a full `S1` object |
| Steps | 1. `PUT` document A2 with `header_text: ""` and the current `version`.<br>2. `GET` document A2 and read the JSON type of `header_text`.<br>3. Read the `page_settings` column directly from the DB. |
| Expected result | Step 1: `200 OK`. Step 2: `header_text` is the JSON string `""`, not `null` and not absent from the object. Step 3: the stored JSONB carries `"header_text": ""`. |
| Status | Not run |

### TC-10-API-1.3 — Whitespace-only header text is trimmed to nothing

| Field | Value |
|---|---|
| Description | A running head of spaces reserves band height on every page for text nobody can see; it must normalize to empty rather than be stored as-is. |
| Preconditions | Document A2 exists, owned by account A. |
| Test data | `header_text` = `"   \t   "` (spaces, a tab and a no-break space) |
| Steps | 1. `PUT` document A2 with that `header_text` and the current `version`.<br>2. `GET` document A2 and read `header_text`.<br>3. Export document A2 as `pdf` and read the header band of every page. |
| Expected result | Step 1: `200 OK`. Step 2: `header_text` reads `""` — no whitespace is preserved. Step 3: no header band text is drawn on any page and the content frame is not shortened to make room for one. |
| Status | Not run |

### TC-10-API-1.4 — A fractional margin round-trips without drift

| Field | Value |
|---|---|
| Description | A margin stored through a float→string→float path drifts by a fraction of a millimetre per save, which changes the page count of a long document over a session. |
| Preconditions | Document A2 exists, owned by account A. |
| Test data | `margins_mm {top:20.5,right:15.25,bottom:20.5,left:30.75}`, `line_height` `1.15`, `font_size_pt` `11.5` |
| Steps | 1. `PUT` document A2 with those values and the current `version`.<br>2. `GET` document A2 and compare each number with what was sent.<br>3. Export document A2 as `pdf` twice, five minutes apart.<br>4. Compare the two PDFs' `/MediaBox`, page count and text-frame geometry. |
| Expected result | Step 2: the returned numbers are exactly `20.5`, `15.25`, `20.5`, `30.75`, `1.15`, `11.5` — no `20.499999` and no rounding to `20`. Step 4: the two exports carry identical geometry and the same page count. |
| Status | Not run |

### TC-10-API-1.5 — Landscape swaps the effective content box

| Field | Value |
|---|---|
| Description | If orientation is applied only to the drawn sheet and not to the fit check, margins that fit sideways pass in portrait too — and pagination then runs on a box that does not exist. |
| Preconditions | Document A2 exists, owned by account A. |
| Test data | `page_size` `A5` (148 × 210 mm), `margins_mm {top:20,right:20,bottom:20,left:20}`, `font_size_pt` `11`, `line_height` `1.15`, plus a horizontal pair of `left:80,right:60` — 140 mm, which fits the 210 mm landscape width but exceeds the 148 mm portrait width |
| Steps | 1. `PUT` document A2 with `orientation: "landscape"` and margins `{top:20,right:60,bottom:20,left:80}` and the current `version`.<br>2. Refetch `version`, then `PUT` the identical object with `orientation: "portrait"`. |
| Expected result | Step 1: `200 OK`; the content box is 70 × 170 mm. Step 2: `422 Unprocessable Entity` with the generic error body — the same margins are refused in portrait because 80 + 60 = 140 mm leaves only 8 mm of the 148 mm width; the stored landscape settings are unchanged. |
| Status | Not run |

---

## 2. Interaction With Content

### TC-10-API-2.1 — Content at the size limit still accepts a settings change

| Field | Value |
|---|---|
| Description | A limit checked against the whole request rather than the content field would make a maximal document permanently unconfigurable. |
| Preconditions | Document A14 exists, owned by account A, with content of exactly 200 000 code points. |
| Test data | Document A14 id `ae09317c-6b25-4f80-92d1-cd5f7a41e836`; body resends the identical 200 000-character content plus settings `S1` |
| Steps | 1. `GET` document A14 and record `content` and `version`.<br>2. `PUT` document A14 with the identical content and settings `S1`.<br>3. `GET` document A14. |
| Expected result | Step 2: `200 OK` — not `400 CONTENT_TOO_LONG` and not `413`. Step 3: `page_settings` equals `S1` and `content` is byte-identical to step 1. |
| Status | Not run |

### TC-10-API-2.2 — A document consisting only of manual breaks is handled

| Field | Value |
|---|---|
| Description | Emitting a page per break plus one trailing page for the empty flow after the last break is the natural off-by-one, and it prints a blank sheet the user did not ask for. |
| Preconditions | Document A15 exists, owned by account A, whose content is three consecutive manual breaks and nothing else. |
| Test data | Document A15 id `50c8d3b6-9e14-4a27-83f5-6d1b0ac9427e`, content `<div data-page-break="true"></div><div data-page-break="true"></div><div data-page-break="true"></div>` |
| Steps | 1. `GET` document A15.<br>2. Export document A15 as `pdf` and count the pages.<br>3. Export as `docx` and count the `<w:br w:type="page"/>` elements. |
| Expected result | Step 1: `200 OK` with the three breaks intact in `content`. Step 2: the PDF has exactly 4 pages — one before each break plus the final one — and no fifth, empty page beyond the last break. Step 3: exactly 3 page-break elements, with no trailing empty paragraph after the last. |
| Status | Not run |

### TC-10-API-2.3 — A manual break as the very first block does not create a leading blank page

| Field | Value |
|---|---|
| Description | A break at position 0 closes a page that has no content on it; the renderer must not print that empty page before the document starts. |
| Preconditions | Document A16 exists, owned by account A, beginning with a manual break. |
| Test data | Document A16 id `c7f24a95-30de-4b61-a8c9-15e0b6d3728f`, content `<div data-page-break="true"></div><p>Первый абзац.</p>` |
| Steps | 1. `GET` document A16 and confirm the break is the first node in `content`.<br>2. Export as `pdf` and read the text of page 1.<br>3. Export as `docx` and read the first body element of `word/document.xml`. |
| Expected result | Step 2: the PDF's page 1 carries `Первый абзац.` — there is no blank page 1 ahead of it, and the page count equals that of the same content without the leading break. Step 3: no empty paragraph precedes the first content paragraph. |
| Status | Not run |

---

## 3. Concurrency Edges

### TC-10-API-3.1 — A settings save and a settings save race resolves to one winner

| Field | Value |
|---|---|
| Description | A blended object — one writer's font size with the other's margins — is a geometry neither client chose and neither can reproduce. |
| Preconditions | Document A2 exists at `version` `7`; two clients have both read `version` `7`. |
| Test data | Client 1 sends `S1`. Client 2 sends `{"page_size":"Letter","orientation":"portrait","margins_mm":{"top":20,"right":20,"bottom":20,"left":20},"font_size_pt":14,"line_height":1.5,"header_text":null,"footer_text":null,"show_page_numbers":false,"skip_number_on_first_page":true}`. Both use `version: 7`. |
| Steps | 1. Issue both `PUT`s concurrently against document A2.<br>2. Record both statuses.<br>3. `GET` document A2 and compare the stored object with each submission field by field. |
| Expected result | Exactly one answers `200 OK` and the other answers `409` with the version-conflict body; `version` is `8`. The stored object equals one of the two submissions in all nine keys — never `page_size` from one and `font_size_pt` from the other. |
| Status | Not run |

### TC-10-API-3.2 — A conflict response carries the information needed to retry

| Field | Value |
|---|---|
| Description | A conflict the client cannot recover from is a dead end; the refetch must yield the version and the settings that make the resubmission succeed. |
| Preconditions | Client 2 from TC-10-API-3.1 has just received `409` on document A2. |
| Test data | Document A2; client 2's rejected object; the fresh `version` obtained by refetching |
| Steps | 1. Record client 2's `409` response.<br>2. `GET` document A2 and read `version` and `page_settings`.<br>3. `PUT` client 2's original object again with the version from step 2.<br>4. `GET` document A2. |
| Expected result | Step 1: `409` with body exactly `{"error_code": "VERSION_CONFLICT", "message": "The document was modified by another save. Refetch and retry."}` and no document fields. Step 2: `200 OK` with `version` `8` and the winner's settings. Step 3: `200 OK` with `version` `9`. Step 4: `page_settings` equals client 2's object in all nine keys. |
| Status | Not run |
