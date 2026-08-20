> These are additional edge case tests. Implement after core tests pass.

# Editor pages — Security Tests (Extended)

Surfaces: the free header/footer text on its way into three render sinks, the structural
limits on content, and whether a rejection can be used to enumerate another account's ids.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.pages@textery.test` / `Qa!Pages2026` |
| Account B (a stranger) | `qa.stranger@textery.test` / `Qa!Stranger2026` |
| Document A2 (caller's) | id `c31f8a05-6d47-4b92-8e10-2f5c9d7b3a64`, `version` `7`, settings `S1` |
| Document B1 (owned by B) | id `2c9a77e0-51b4-4b1e-8f0a-6d3c9b2a4e18`, current `version` `4` |
| Absent id | `00000000-0000-4000-8000-000000000000` |
| Settings `S1` | A5, landscape, margins 35/15/25/40 mm, 11 pt, line height 1.15, header `Кафедра ИВТ`, footer `Текстери` |
| Limits | header/footer ≤ 200 code points (NFC); content ≤ 200 000 code points, ≤ 5 000 blocks, ≤ 10 levels of nesting |
| 404 body | `{"error_code": "NOT_FOUND", "message": "The requested resource was not found."}` |
| 422 body shape | `{"error_code": "<CODE>", "message": "<generic text>"}` — exactly these two keys |
| Render deadline | 30 s (story 17 configuration) |

## 1. Text Handling

### TC-10-SEC-1.1 — Bidirectional control characters cannot reorder the rendered header

| Field | Value |
|---|---|
| Description | An unterminated RLO turns the rest of the running head — and anything drawn after it — backwards, letting an author spoof text they did not write. |
| Preconditions | Document A2 owned by account A; the header below is saved and the document is opened and exported. |
| Test data | `header_text` = `Кафедра` + U+202E + `ИВТ 2026` (RLO with no PDF terminator); control header `Кафедра ИВТ 2026` |
| Steps | 1. `PUT` document A2 with that `header_text` and the current `version`.<br>2. Open the editor and screenshot the header band; read its computed text direction.<br>3. Export as `pdf` and read the header band's glyph order.<br>4. Export as `docx` and read `word/header1.xml`. |
| Expected result | In all three targets the visible order of the surrounding text (the folio, the footer, the page content) is the same as with the control header — the override does not escape the header run; the bidi character is stripped or isolated (wrapped in an isolate, or emitted with an explicit terminator) rather than emitted bare; no `200` render shows reversed page content. |
| Status | Not run |

### TC-10-SEC-1.2 — A header of combining marks cannot expand without bound

| Field | Value |
|---|---|
| Description | 200 code points of stacked marks is a legal header by every count and can still draw a glyph tower that consumes the render deadline or paints over the page body. |
| Preconditions | Document A2 owned by account A, laid out to at least 2 pages, settings `S1` (header band height fixed by the 35 mm top margin). |
| Test data | `header_text` = `а` followed by 199 × U+0301 (200 code points, one grapheme cluster) |
| Steps | 1. `PUT` document A2 with that `header_text` and the current `version`.<br>2. Export as `pdf`, timing the request.<br>3. Measure the header's painted bounding box against the 35 mm top margin band.<br>4. Open the editor and measure the same. |
| Expected result | Step 1: `200 OK` — the header is at the limit and legal. Step 2: `200 OK` well inside the 30 s render deadline, with no deadline abort. Steps 3–4: the header's painted box stays inside the top margin band in both targets — it is clipped or the cluster is capped, and it never overlaps the content frame. |
| Status | Not run |

### TC-10-SEC-1.3 — Normalization cannot be used to slip past the length limit

| Field | Value |
|---|---|
| Description | Checking length before normalizing, or after when normalization shrinks the string, are two different limits; the contract is that NFC comes first and the check applies to it. |
| Preconditions | Document A2 owned by account A. |
| Test data | A header whose NFC form is longer than its submitted form: 195 code points of `ﬁ`-style compatibility and Hangul jamo sequences that expand to 205 code points under NFC. Control: a 190-code-point string that stays 190 under NFC. |
| Steps | 1. `PUT` document A2 with the expanding header and the current `version`.<br>2. `GET` document A2 and read `header_text`.<br>3. `PUT` the 190-code-point control header. |
| Expected result | Step 1: `422` with the two-key generic body — the limit is applied to the NFC form (205 > 200), not the 195-code-point submission. Step 2: the stored header is the previous value; nothing was truncated to 200. Step 3: `200 OK`, showing the rule is a limit and not a blanket refusal. |
| Status | Not run |

---

## 2. Structural Abuse

### TC-10-SEC-2.1 — Deeply nested content is refused before layout is attempted

| Field | Value |
|---|---|
| Description | Nesting depth drives recursive layout work and stack depth; refusing it only after the layout has run makes the guard useless. |
| Preconditions | Document A2 owned by account A; the layout/render invocation counters are readable. |
| Test data | Content of 11 nested `<div>` elements wrapping one paragraph (limit 10); control: the same shape at 10 levels. Both far under 200 000 code points. |
| Steps | 1. Record the layout and render invocation counters.<br>2. `PUT` document A2 with the 11-level payload and the current `version`.<br>3. Re-read the counters.<br>4. `PUT` the 10-level control payload. |
| Expected result | Step 2: `422` with the two-key generic body, and no stack-overflow or `500`. Step 3: both counters are unchanged — no layout and no render ran. Step 4: `200 OK`, confirming the bound is inclusive at 10. |
| Status | Not run |

### TC-10-SEC-2.2 — A document of many empty blocks is refused before layout

| Field | Value |
|---|---|
| Description | 5 001 empty blocks is a tiny payload with a large layout cost; a rejection whose time scales with the block count proves the document was measured before being refused. |
| Preconditions | Document A2 owned by account A. |
| Test data | (a) 5 001 × `<p></p>` (limit 5 000); (b) 50 000 × `<p></p>`; control (c) 5 000 × `<p></p>`. A minimal `422` (an unknown `page_settings` key) is timed as the baseline. |
| Steps | 1. Time a minimal `422` on document A2 as the baseline.<br>2. `PUT` payload (a) and record status and elapsed time.<br>3. `PUT` payload (b) and record status and elapsed time.<br>4. `PUT` control (c). |
| Expected result | (a) and (b) answer `422` with the two-key generic body; control (c) answers `200 OK`. The elapsed times for (a) and (b) are within the same order of magnitude as the step-1 baseline and do not grow with the block count — the ten-times-larger payload (b) is not measurably slower to reject than (a). |
| Status | Not run |

---

## 3. Enumeration

### TC-10-SEC-3.1 — Rejection reasons do not disclose whether a document exists

| Field | Value |
|---|---|
| Description | If validation runs before the ownership check, a `422` on a foreign id and a `404` on an absent id tell the attacker which ids are real, one request at a time. |
| Preconditions | Document B1 exists and is owned by account B; account A signed in. |
| Test data | Invalid body `{"content":"<p>x</p>","version":4,"page_settings":{"font_size_pt":500,"gutter_mm":1}}`, sent against document B1 and against the absent id |
| Steps | 1. `PUT /api/v1/documents/2c9a77e0-51b4-4b1e-8f0a-6d3c9b2a4e18` with the invalid body, as account A.<br>2. `PUT /api/v1/documents/00000000-0000-4000-8000-000000000000` with the same body.<br>3. Diff the two responses (status, headers bar `Date`, body) and compare their elapsed times over 50 repetitions each. |
| Expected result | Both answer `404 Not Found` with body exactly `{"error_code": "NOT_FOUND", "message": "The requested resource was not found."}` — never `422`, which would prove the values were checked and therefore that the id resolved; the two responses are byte-identical and their median elapsed times differ by less than the run-to-run noise of the absent-id case. |
| Status | Not run |

### TC-10-SEC-3.2 — A conflict response does not disclose another account's state

| Field | Value |
|---|---|
| Description | `404` must take precedence over `409`: a conflict on a foreign id would confirm both that the id exists and that the guessed version was wrong — or, worse, right. |
| Preconditions | Document B1 exists at `version` `4`, owned by account B; account A signed in. |
| Test data | Valid bodies against document B1 with `version` `1`, `4` (the correct one) and `99` |
| Steps | 1. `PUT` document B1 as account A with `version: 1` and valid `page_settings`.<br>2. Repeat with `version: 4`.<br>3. Repeat with `version: 99`.<br>4. Diff all three responses against each other and against the absent-id response. |
| Expected result | All three answer `404` with the not-found body; none answers `409` and none differs when the guessed version happens to be the correct `4`; all four responses (including the absent-id one) are byte-identical, so nothing distinguishes a correct version guess from a wrong one. |
| Status | Not run |
