# Export document — Integration Tests

End-to-end from a stored document through the real render pipeline.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.export@textery.test` / `Qa!Export2026` |
| Document A1 | id `7f1c2d84-0b2e-4c31-9a55-2f7b41d0e913`, title `Отчёт по практике` |
| Structured fixture (A10) | id `3e7d5b90-6c18-4a2f-b4d9-0e8a1f7c25b3`, content `<h1>Введение</h1><p>Первый <strong>абзац</strong> с <em>акцентом</em>.</p><ul><li>Пункт один</li><li>Пункт два</li></ul>` |
| Multibyte fixture (A5) | id `c4f8e2a1-9b07-4d36-85ea-1c6b3d0f9472`, content `<p>Привет 🎓 é (e + U+0301)</p>` |
| Export request | `GET /api/v1/documents/{id}/export?format=pdf|docx` with account A's Bearer token |
| PDF signature | first five bytes `%PDF-`, `Content-Type: application/pdf` |
| DOCX signature | first two bytes `PK`, `Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document` |

## 1. Round-Trip

### TC-17-INT-1.1 — A document exports to a well-formed PDF and DOCX

| Field | Value |
|---|---|
| Description | Unit-level render tests pass on a renderer that emits a file no reader opens. This runs the real pipeline end to end and opens the result. |
| Preconditions | Document A10 exists and is owned by account A with the structured content above; the real render backend (not a stub) is wired. |
| Test data | Document A10, both formats; expected structure: one `Введение` heading, one bold `абзац`, one italic `акцентом`, a two-item list |
| Steps | 1. `GET /api/v1/documents/3e7d5b90-6c18-4a2f-b4d9-0e8a1f7c25b3/export?format=pdf`, save as `out.pdf`.<br>2. Repeat with `format=docx`, save as `out.docx`.<br>3. Extract the PDF text layer; unzip `out.docx` and read `word/document.xml`.<br>4. Open both files in a reader (PDF viewer, Word or LibreOffice). |
| Expected result | Both answer `200 OK` with the format's `Content-Type` and `Content-Disposition: attachment; …`; `out.pdf` starts with `%PDF-`, `out.docx` starts with `PK`; both open without a repair prompt; each contains `Введение` as a heading, `абзац` in bold, `акцентом` in italic, and the two list items in order. |
| Status | Not run |

### TC-17-INT-1.2 — Multibyte content survives the render pipeline

| Field | Value |
|---|---|
| Description | Mojibake, `?` substitution and tofu boxes appear only in the real font-and-encoding path — a stubbed renderer never reproduces them. |
| Preconditions | Document A5 exists and is owned by account A with the multibyte content above; the bundled document font is present in the image. |
| Test data | Document A5, both formats; expected characters `Привет`, the graduation-cap emoji, `é` written as `e` + U+0301 |
| Steps | 1. Export document A5 as `pdf` and extract its text layer.<br>2. Export document A5 as `docx` and read `word/document.xml`.<br>3. Render the PDF to an image and inspect the glyphs visually. |
| Expected result | Both files answer `200 OK` and contain `Привет`, the emoji and the accented `é` exactly as stored; no `?`, no `�` and no empty tofu box appears in either the extracted text or the rendered page. |
| Status | Not run |

## 2. Consistency

### TC-17-INT-2.1 — The export reflects the latest saved state end to end

| Field | Value |
|---|---|
| Description | An export reading a lagging replica hands the user the previous version of the document seconds after they saved it — through the editor, where the mismatch is invisible until the file is opened. |
| Preconditions | Document A1 exists and is open in the editor as account A; the full stack (editor → save → export) is running. |
| Test data | New content `<p>Свежий абзац.</p>`, new title `Свежий отчёт`, export issued within 1 s of the save returning |
| Steps | 1. Edit document A1 in the editor to the new content and title, and save (`PUT /api/v1/documents/{A1}`), waiting for the `2xx`.<br>2. Within 1 s, export document A1 as `pdf`.<br>3. Extract the PDF text and decode the `Content-Disposition` filename. |
| Expected result | `200 OK`; the PDF text contains `Свежий абзац.` and not the previous content; the decoded filename is `Свежий отчёт.pdf`; the document's `version` is unchanged by the export itself. |
| Status | Not run |
