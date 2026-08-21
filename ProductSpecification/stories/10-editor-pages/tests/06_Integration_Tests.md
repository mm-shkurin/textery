# Editor pages — Integration Tests

Story 10 calls no external HTTP service. Its integration seams are the two render
libraries and the font asset — the places where a value crosses out of the application's
own types into someone else's engine, and where a unit conversion or an unpinned ambient
silently changes the result.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.pages@textery.test` / `Qa!Pages2026` |
| Document A2 (self-distinct fixture) | id `c31f8a05-6d47-4b92-8e10-2f5c9d7b3a64`, content `<p>Первый абзац.</p>`, settings `S1` |
| Settings `S1` | `page_size` `A5`, `orientation` `landscape`, `margins_mm` `{top:35,right:15,bottom:25,left:40}`, `font_size_pt` `11`, `line_height` `1.15`, header `Кафедра ИВТ`, footer `Текстери`, `show_page_numbers` `true`, `skip_number_on_first_page` `true` |
| Realised A5-landscape sheet | 210 × 148 mm; content box 155 × 88 mm (210 − 15 − 40, 148 − 35 − 25) |
| Same box in CSS px @96 dpi | 585.8 × 332.6 px (×96/25.4), ±1 px |
| Same sheet in DOCX twips | page 11906 × 8391; `w:top` 1984, `w:right` 850, `w:bottom` 1417, `w:left` 2268 |
| Font size in DOCX | `w:sz` `22` (half-points); line `w:line` `253` (11 pt × 1.15 × 20) |
| Sheet dimensions | A4 210 × 297 mm (11906 × 16838 tw), A5 148 × 210 mm (8391 × 11906 tw), Letter 215.9 × 279.4 mm (12240 × 15840 tw) |
| Document font | bundled Liberation Serif (`LiberationSerif-Regular.ttf`), identical file in image and frontend bundle |
| 500 body | `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}` |

---

## 1. Geometry Across the Render Boundaries

### TC-10-INT-1.1 — The realised page geometry matches the settings in every target

| Field | Value |
|---|---|
| Description | Every value in the fixture differs from every other and from the default preset — the default is the one fixture that passes with all three conversions broken, because each side is likely to have it hardcoded. |
| Preconditions | Document A2 exists, owned by account A, saved with settings `S1`; a second document A11 carries the same margins on `Letter` portrait. |
| Test data | `S1` (A5 landscape); document A11 id `f5a3b7c2-48e1-4d09-b263-90c7e5148a3d`, `page_size` `Letter`, `orientation` `portrait`, same margins/font/line height |
| Steps | 1. Open document A2 in the editor and measure the rendered sheet box and content box in CSS px.<br>2. Export document A2 as `pdf` and read `/MediaBox` and the text frame in mm.<br>3. Export document A2 as `docx` and read `w:pgSz`, `w:pgMar`, `w:sz` and `w:spacing` from `word/document.xml`.<br>4. Repeat steps 1–3 for document A11. |
| Expected result | Editor: sheet 793.7 × 559.4 px, content box 585.8 × 332.6 px (±1 px). PDF: `/MediaBox` 210 × 148 mm and a content frame of 155 × 88 mm (±0.5 mm). DOCX: `w:pgSz w:w="11906" w:h="8391" w:orient="landscape"`, `w:pgMar w:top="1984" w:right="850" w:bottom="1417" w:left="2268"`, `w:sz w:val="22"`, `w:spacing w:line="253"`. Document A11 gives 215.9 × 279.4 mm in the PDF and `w:pgSz w:w="12240" w:h="15840"` in the DOCX — the imperial sheet is not silently converted to A4. |
| Status | Not run |

### TC-10-INT-1.2 — Numbers are formatted under an invariant locale

| Field | Value |
|---|---|
| Description | Catches the silent failure where a comma-decimal number becomes an invalid stylesheet declaration, is dropped, and the document simply paginates differently with no error. |
| Preconditions | Document A12 exists with fractional geometry; the process can be started under a comma-decimal locale. |
| Test data | Document A12 id `7ba21c60-df34-4e58-9a17-c6f0b83d5e42`, `line_height` `1.15`, `margins_mm` `{top:20.5,right:15.25,bottom:20.5,left:30.75}`, `font_size_pt` `11.5`; locales `C.UTF-8` and `ru_RU.UTF-8` (`LC_ALL`, `LC_NUMERIC`) |
| Steps | 1. Export document A12 as `pdf` and as `docx` under `LC_ALL=C.UTF-8`; store both files.<br>2. Restart the backend with `LC_ALL=ru_RU.UTF-8` and `LC_NUMERIC=ru_RU.UTF-8` and export the same document in both formats.<br>3. Compare the two PDFs' `/MediaBox`, page count and text-frame geometry, and the two DOCX files' `w:pgSz`, `w:pgMar` and `w:spacing`.<br>4. Capture the stylesheet handed to the PDF renderer in each run. |
| Expected result | Both runs answer `200 OK`; the geometry values compared in step 3 are identical between locales, and the page counts match. Step 4: every number in the stylesheet uses `.` as the decimal separator (`margin-left: 30.75mm`, `line-height: 1.15`) in both runs — no `30,75` appears, and no declaration is silently dropped. |
| Status | Not run |

---

## 2. Render Library Behaviour

### TC-10-INT-2.1 — The PDF renderer honours manual breaks, headers and numbering

| Field | Value |
|---|---|
| Description | Geometry, breaks, running heads and folios are four independent WeasyPrint features; each can be lost on its own without the others noticing. |
| Preconditions | Document A13 exists, owned by account A, with settings `S1` (`skip_number_on_first_page` `true`) and a manual break. |
| Test data | Document A13 id `2d6ef803-51ab-4c74-9fb0-8a3c47e19d5b`, content `<p>До разрыва.</p><div data-page-break="true"></div><p>После разрыва.</p>`, header `Кафедра ИВТ`, footer `Текстери` |
| Steps | 1. `GET /api/v1/documents/2d6ef803-51ab-4c74-9fb0-8a3c47e19d5b/export?format=pdf`.<br>2. Extract the text of each page separately.<br>3. Read the header band and footer band of each page. |
| Expected result | `200 OK` and a 2-page PDF; page 1 carries `До разрыва.` and page 2 begins with `После разрыва.`; both pages carry `Кафедра ИВТ` in the top margin band and `Текстери` in the bottom band; page 1 shows no folio while page 2 shows `2` — not `1`. |
| Status | Not run |

### TC-10-INT-2.2 — The DOCX renderer emits breaks, headers and section geometry

| Field | Value |
|---|---|
| Description | Word repaginates on open, so page-end equality is unreachable for DOCX by any implementation and must not be asserted — what can be asserted is the XML the file carries. |
| Preconditions | Document A13 (as in TC-10-INT-2.1) exists with settings `S1`. |
| Test data | Same document, `format=docx`; expected `w:pgSz w:w="11906" w:h="8391" w:orient="landscape"`, `w:pgMar w:top="1984" w:right="850" w:bottom="1417" w:left="2268"` |
| Steps | 1. `GET /api/v1/documents/2d6ef803-51ab-4c74-9fb0-8a3c47e19d5b/export?format=docx`.<br>2. Unzip and read `word/document.xml`, `word/header1.xml`, `word/footer1.xml` and `[Content_Types].xml`. |
| Expected result | `200 OK`; `word/document.xml` carries `<w:br w:type="page"/>` between the two paragraphs and the `w:sectPr` values above; a header part carrying `Кафедра ИВТ` and a footer part carrying `Текстери` exist and are referenced from `w:sectPr` and declared in `[Content_Types].xml`; the footer carries a `PAGE` field for the numbering. No assertion is made — and none may be added — about which page any content lands on when Word opens the file. |
| Status | Not run |

---

## 3. Font Resolution

### TC-10-INT-3.1 — A resolvable font renders without touching the network

| Field | Value |
|---|---|
| Description | A renderer that fetches whatever the document references turns every export into an outbound request from inside the network; the bundled face must be read from disk. |
| Preconditions | The bundled font asset is present in the image; an HTTP listener runs on `127.0.0.1:9099` with an empty access log; outbound sockets are observed against a fake network. |
| Test data | Document A2 (settings `S1`, header `Кафедра ИВТ`), `format=pdf`; listener `127.0.0.1:9099` |
| Steps | 1. Export document A2 as `pdf`.<br>2. Read the PDF's embedded-font list.<br>3. Read the listener's access log and the recorded outbound sockets and DNS lookups for the render. |
| Expected result | `200 OK` and a valid PDF whose embedded font is Liberation Serif — no substituted family. The listener log has zero entries; zero outbound sockets and zero DNS lookups to any non-database host were made during the render. |
| Status | Not run |

### TC-10-INT-3.2 — An unresolvable font fails the render instead of substituting

| Field | Value |
|---|---|
| Description | The render library catches per-resource fetch failures and continues, so without this guard a missing face yields a successful export in substituted metrics — right-looking bytes with wrong line breaks and a wrong page count. |
| Preconditions | Document A2 exists; the bundled font asset is made unreadable for the duration of the render; the server log is captured. |
| Test data | Document A2 id `c31f8a05-6d47-4b92-8e10-2f5c9d7b3a64`, both formats; font file `chmod 000` at render time |
| Steps | 1. Export document A2 as `pdf` and record status, body length and log.<br>2. Export document A2 as `docx` and record the same.<br>3. Export a control document with the font restored. |
| Expected result | Steps 1–2: `500` with body exactly `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}`; zero file bytes and no `Content-Disposition`; each emits exactly one error-level log record naming document A2's id. Step 3: `200 OK`, proving the failure was attributable to the font and not a wedged worker. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `self-distinct in every field` | A5 landscape, margins 35/15/25/40 mm, 11 pt, line height 1.15 |
| `that target's own unit` | CSS px in the browser, mm in the PDF, EMU / half-points / twips in the DOCX |
| `an imperial sheet size` | `Letter` (215.9 × 279.4 mm) |
| `the default locale` | The application's pinned invariant formatting locale |
| `an attributable server-side signal` | Log/metric keyed by document id, distinct from the happy path |
| `no outbound network request` | Observed against a fake network, as in story 17's SSRF guard |
