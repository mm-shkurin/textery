<!-- COPIED FILE. Source of truth: ProductSpecification/stories/10-editor-pages/tests/05_Security_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Editor pages — Security Tests

Attack surface added by this story: one client-writable object (`page_settings`) persisted
as JSONB, and free user text (`header_text` / `footer_text`) rendered into three different
sinks — editor HTML, a PDF stylesheet, and DOCX header XML.

Out of scope here, tested globally: unauthenticated access, security headers, CORS, HTTPS.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.pages@textery.test` / `Qa!Pages2026` |
| Account B (a stranger) | `qa.stranger@textery.test` / `Qa!Stranger2026` |
| Document A2 (caller's) | id `c31f8a05-6d47-4b92-8e10-2f5c9d7b3a64`, `version` `7`, settings `S1` |
| Document B1 (owned by B) | id `2c9a77e0-51b4-4b1e-8f0a-6d3c9b2a4e18` |
| Absent id | `00000000-0000-4000-8000-000000000000` |
| Settings `S1` | `{"page_size":"A5","orientation":"landscape","margins_mm":{"top":35,"right":15,"bottom":25,"left":40},"font_size_pt":11,"line_height":1.15,"header_text":"Кафедра ИВТ","footer_text":"Текстери","show_page_numbers":true,"skip_number_on_first_page":false}` |
| 404 body | `{"error_code": "NOT_FOUND", "message": "The requested resource was not found."}` |
| 422 body shape | `{"error_code": "<CODE>", "message": "<generic text>"}` — exactly these two keys |
| Owner sentinel | `SENTINEL-OWNER-7f3a91` seeded into account A's display name |
| Limits | content ≤ 200 000 code points, ≤ 5 000 blocks, ≤ 10 levels of nesting; header/footer ≤ 200 code points |

---

## 1. Authorization

### TC-10-SEC-1.1 — Page settings of a foreign document cannot be read, written, or exported

| Field | Value |
|---|---|
| Description | Geometry adds two more verbs against a document id; each must refuse a foreign id exactly like the absent one, or the new surface becomes an id oracle. |
| Preconditions | Document B1 exists and is owned by account B; account A signed in. |
| Test data | Document B1 id `2c9a77e0-51b4-4b1e-8f0a-6d3c9b2a4e18`; absent id `00000000-0000-4000-8000-000000000000`; save body `{"content":"<p>x</p>","version":1,"page_settings":<S1>}`; `format=pdf` |
| Steps | 1. `GET /api/v1/documents/{B1}` with account A's token.<br>2. `PUT /api/v1/documents/{B1}` with the save body.<br>3. `GET /api/v1/documents/{B1}/export?format=pdf`.<br>4. Repeat all three against the absent id and diff each pair (status line, headers bar `Date`, body, and elapsed time). |
| Expected result | All six calls answer `404 Not Found` with body exactly `{"error_code": "NOT_FOUND", "message": "The requested resource was not found."}`; never `403`, never `409`, never `422`; each foreign-id response is byte-identical to its absent-id counterpart and their response times are within the same order of magnitude. |
| Status | Not run |

---

## 2. Mass Assignment

### TC-10-SEC-2.1 — Only the allow-listed page-settings keys are persisted

| Field | Value |
|---|---|
| Description | A JSONB column that accepts whatever the caller sends is an attacker-controlled store that reads back out to every client of the document. |
| Preconditions | Document A2 exists, owned by account A, with settings `S1` stored. |
| Test data | Body `{"content":"<p>Первый абзац.</p>","version":7,"page_settings":{<S1 keys>, "owner_id":"<account B id>", "__proto__":{"admin":true}}}` |
| Steps | 1. `PUT /api/v1/documents/c31f8a05-6d47-4b92-8e10-2f5c9d7b3a64` with that body.<br>2. Read the `page_settings` column of the row directly from the DB and list its top-level keys.<br>3. Grep the whole column value for `owner_id` and `__proto__`. |
| Expected result | Step 1: `422 Unprocessable Entity` with the two-key generic error body. Step 2: the column still holds exactly the nine allow-listed keys of `S1` — `page_size`, `orientation`, `margins_mm`, `font_size_pt`, `line_height`, `header_text`, `footer_text`, `show_page_numbers`, `skip_number_on_first_page`. Step 3: neither string appears anywhere in the column; no fragment of the submitted body was stored verbatim. |
| Status | Not run |

### TC-10-SEC-2.2 — Server-owned fields remain unwritable

| Field | Value |
|---|---|
| Description | Story 5's posture is that server-owned fields are ignored rather than rejected; adding a writable object must not open a side door that makes them writable again. |
| Preconditions | Document A2 exists, owned by account A, `document_type` `manual`, `status` `draft`. |
| Test data | Body `{"content":"<p>Первый абзац.</p>","version":7,"page_settings":<S1>,"document_type":"generated","status":"published","owner_id":"<account B id>","id":"<other uuid>"}` |
| Steps | 1. `PUT` document A2 with that body.<br>2. `GET` document A2 with account A's token.<br>3. Attempt `GET` document A2 with account B's token.<br>4. Read the row's owner column directly from the DB. |
| Expected result | Step 1: `200 OK` — the server-owned top-level fields are ignored, not rejected. Step 2: `document_type` is still `manual`, `status` still `draft`, `document_id` unchanged; `page_settings` equals `S1`. Step 3: `404` with the not-found body — ownership did not move. Step 4: the owner column still names account A. |
| Status | Not run |

---

## 3. Injection Into Render Sinks

### TC-10-SEC-3.1 — Header text carrying markup cannot execute in the editor

| Field | Value |
|---|---|
| Description | `header_text` is plain text on the way in and HTML on the way out; if the editor interpolates it unescaped, every reader of the document runs the author's script. |
| Preconditions | Document A2 owned by account A; the header saved with the payload below; account A opens the editor with a console listener attached. |
| Test data | `header_text` = `<script>window.__pwned=1</script><img src=x onerror="window.__pwned=2"><a href="javascript:window.__pwned=3">клик</a>` |
| Steps | 1. `PUT` document A2 with that `header_text` and the current `version`.<br>2. Open `/documents/c31f8a05-6d47-4b92-8e10-2f5c9d7b3a64` and wait for the layout.<br>3. Read the header area's rendered text and its DOM.<br>4. Evaluate `window.__pwned` and click the rendered header text. |
| Expected result | The header area displays the payload as literal visible characters, starting with `<script>`; the header subtree contains no `<script>`, `<img>` or `<a>` element and no `onerror` attribute; `window.__pwned` is `undefined` after step 4 and no console error or CSP violation is raised. |
| Status | Not run |

### TC-10-SEC-3.2 — Header text cannot break out of the DOCX header XML

| Field | Value |
|---|---|
| Description | An unescaped `<` or `&` in `word/header1.xml` produces a file Word refuses to open — or, worse, one whose XML the author controls. |
| Preconditions | Document A2 owned by account A, exported as `docx` after the header below is saved. |
| Test data | `header_text` = `</w:t></w:r><w:r><w:t>ВЗЛОМ` + `& "кавычки" <tag>` + the control characters U+0000 and U+000B |
| Steps | 1. `PUT` document A2 with that `header_text`.<br>2. `GET /api/v1/documents/c31f8a05-6d47-4b92-8e10-2f5c9d7b3a64/export?format=docx`.<br>3. Unzip the result and parse `word/header1.xml` with a strict XML parser.<br>4. Open the file in Word or LibreOffice and read the header. |
| Expected result | Step 2: `200 OK`. Step 3: the parser reports a well-formed document; the payload appears as escaped character data (`&lt;/w:t&gt;`, `&amp;`, `&quot;`) inside a single `<w:t>` run, and the control characters are stripped or escaped — never emitted raw. Step 4: the header displays the literal submitted text, and no extra `ВЗЛОМ` run exists outside it. |
| Status | Not run |

### TC-10-SEC-3.3 — The page-number placeholder syntax in user text is not interpreted

| Field | Value |
|---|---|
| Description | A header template that substitutes into user text lets the author drive the numbering engine from their own document body. |
| Preconditions | Document A2 owned by account A, laid out to at least 2 pages. |
| Test data | `header_text` = `Страница {page} из {pages} — {{page}} — PAGE \* MERGEFORMAT` |
| Steps | 1. `PUT` document A2 with that `header_text`.<br>2. Open the editor and read the header on sheets 1 and 2.<br>3. Export as `pdf` and read the header text on each page.<br>4. Export as `docx` and read `word/header1.xml`. |
| Expected result | In all three targets the header reads literally `Страница {page} из {pages} — {{page}} — PAGE \* MERGEFORMAT`; no `{page}` is replaced with `1` or `2`; `word/header1.xml` carries the text inside `<w:t>` and does not turn it into a `PAGE` field (`<w:fldChar>` / `<w:instrText>` are absent from the user-text run). |
| Status | Not run |

### TC-10-SEC-3.4 — Geometry values cannot inject into the generated stylesheet

| Field | Value |
|---|---|
| Description | If the numbers reach `@page` as interpolated request strings, a crafted value closes the declaration and writes arbitrary CSS into every render. |
| Preconditions | Document A2 owned by account A; the generated stylesheet for a render can be captured. |
| Test data | (a) `font_size_pt: "12pt; } body { display:none } @page {"`; (b) `margins_mm.top: "20mm"`; (c) `line_height: "1.5;"` |
| Steps | 1. `PUT` document A2 with variant (a), then (b), then (c), current `version` each time.<br>2. After each, export document A2 as `pdf` and capture the stylesheet the renderer was handed.<br>3. Grep every captured stylesheet for `display:none`, `mm"` and the submitted strings. |
| Expected result | Each `PUT` answers `422` with the two-key generic error body — rejected at the boundary before any render. The stylesheets captured in step 2 come from document A2's still-stored `S1` and contain none of the submitted strings; every geometry declaration is a bare number plus a unit emitted by the code (`font-size: 11pt`, `margin-top: 35mm`), with no request-derived text. |
| Status | Not run |

---

## 4. Disclosure

### TC-10-SEC-4.1 — Page-settings rejections expose no internals

| Field | Value |
|---|---|
| Description | A JSON-path fragment, a validator class name or a DB message in a 422 body maps the server's internals one rejected request at a time. |
| Preconditions | Document A2 owned by account A; each distinct rejection reason can be triggered. |
| Test data | Reasons: unknown key `gutter_mm`; unknown enum `B5`; `font_size_pt: 500`; `margins_mm.top: -1`; `line_height: NaN`; margins summing to the sheet dimension; a sub-line content box; a 201-character header. Forbidden substrings: `Traceback`, `PageSettings`, `pydantic`, `body -> page_settings`, `relation "documents"`, `/app/`, `.py`, `line ` |
| Steps | 1. `PUT` document A2 once per reason.<br>2. Capture each response body in full.<br>3. Grep every body for each forbidden substring and list its JSON keys. |
| Expected result | Every response is `422` with exactly the two keys `error_code` and `message`, both strings; no body contains any forbidden substring; no body names a field path, a class, a file, a line number or a database object. |
| Status | Not run |

### TC-10-SEC-4.2 — Header and footer text does not leak into unsanitized sinks

| Field | Value |
|---|---|
| Description | The log is a sink like any other: an unescaped newline in user text forges a log record, and echoing the text back reflects the payload to whoever reads the log. |
| Preconditions | Document A2 owned by account A; the application log is captured for the request. |
| Test data | `header_text` = `SENTINEL-HDR-4c81` + CR + LF + `level=ERROR msg="подделка"` + `[31m`, submitted with an out-of-range `font_size_pt: 500` so the request is rejected |
| Steps | 1. `PUT` document A2 with that body.<br>2. Read the response body.<br>3. Read every log record emitted for the request. |
| Expected result | Step 2: `422` with the two-key generic body, which does not contain `SENTINEL-HDR-4c81` at all. Step 3: if the sentinel appears in the log it appears escaped on a single record — no raw CR or LF splits it across lines, no forged `level=ERROR` record exists, and no raw ANSI escape sequence is written. |
| Status | Not run |

### TC-10-SEC-4.3 — DOCX metadata stays redacted after the headers extension

| Field | Value |
|---|---|
| Description | Story 17 redacted `docProps`; the new header/footer parts are a fresh place for the owner's identity to reappear. |
| Preconditions | Account A's profile carries the sentinel `SENTINEL-OWNER-7f3a91`; document A2 has header `Кафедра ИВТ` and footer `Текстери` set. |
| Test data | Sentinel `SENTINEL-OWNER-7f3a91`; expected author constant `Textery` |
| Steps | 1. Export document A2 as `docx`.<br>2. Unzip and grep every part — `docProps/core.xml`, `docProps/app.xml`, `word/document.xml`, `word/header1.xml`, `word/footer1.xml` — for the sentinel.<br>3. Read `dc:creator` and `cp:lastModifiedBy` in `docProps/core.xml`. |
| Expected result | Step 2: zero matches for `SENTINEL-OWNER-7f3a91` in any part, including the new header and footer XML; no email address and no account id appears either. Step 3: both fields read exactly `Textery` — the neutral product constant story 17 already asserts. |
| Status | Not run |

---

## 5. Resource Abuse

### TC-10-SEC-5.1 — Geometry that would paginate without end is refused

| Field | Value |
|---|---|
| Description | A content box smaller than one line is a free denial of service: every render loops emitting pages until it exhausts memory or the deadline. |
| Preconditions | Document A2 owned by account A; the layout/render counters are readable. |
| Test data | `{"page_size":"A5","orientation":"landscape","margins_mm":{"top":70,"right":10,"bottom":74,"left":10},"font_size_pt":11,"line_height":1.15,...}` — 4 mm box against a ≈4.46 mm line |
| Steps | 1. Record the layout and render invocation counters.<br>2. `PUT` document A2 with that object and the current `version`.<br>3. Re-read the counters and the request's elapsed time. |
| Expected result | Step 2: `422` with the two-key generic body, returned in under 100 ms. Step 3: both counters are unchanged — no layout and no render was started; no render worker was held; the stored `page_settings` is untouched. |
| Status | Not run |

### TC-10-SEC-5.2 — Structure beyond the declared limits is refused

| Field | Value |
|---|---|
| Description | The code-point limit alone does not bound work: 5 001 empty blocks or 11 levels of nesting are small payloads with large layout cost, and a rejection whose timing tracks the payload leaks that the work was done anyway. |
| Preconditions | Document A2 owned by account A. |
| Test data | (a) content of 5 001 `<p></p>` blocks (limit 5 000); (b) content nested 11 `<div>` levels deep (limit 10); (c) the legal cases: 5 000 blocks and 10 levels. Each payload well under 200 000 code points. |
| Steps | 1. `PUT` document A2 with payload (a) and record status and elapsed time.<br>2. `PUT` with payload (b) and record status and elapsed time.<br>3. `PUT` each legal payload from (c).<br>4. Compare the rejection times against the elapsed time of a minimal 422. |
| Expected result | (a) and (b) answer `422` with the two-key generic body; the legal payloads in (c) answer `200 OK`. The rejections are within the same order of magnitude as a minimal `422` — they do not scale with the payload, proving the document was not laid out or rendered before being refused. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `refused as not found` | HTTP 404, identical body for absent and foreign |
| `refused at the boundary` | HTTP 422 before any render, layout or persist |
| `the generic error shape` | `{error_code, message}` with a sanctioned message |
| `the page-number placeholder syntax` | Whatever token the header/footer template uses for the page number |
| `a sentinel identity value` | A unique string seeded into the owner's profile |
| `the neutral product constant` | The fixed author value already asserted by story 17 |
| `well-formed` | The exported DOCX parses as valid OOXML |
