<!-- COPIED FILE. Source of truth: ProductSpecification/stories/17-export-document/tests/01_API_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> **Implementation Order**: sequential TDD — prerequisite/format guards → happy path →
> filename & encoding → safety (SSRF, deadline, disclosure).

# Export document — API Tests

Endpoint: `GET /api/v1/documents/{id}/export?format=pdf|docx`. Read-only.
Contract: `ProductSpecification/api-specs/documents_export.yaml`.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.export@textery.test` / `Qa!Export2026` |
| Account B (a stranger) | `qa.stranger@textery.test` / `Qa!Stranger2026` |
| Access token | `Authorization: Bearer <access token of account A>` |
| Document A1 | id `7f1c2d84-0b2e-4c31-9a55-2f7b41d0e913`, title `Отчёт по практике`, content `<p>Первый абзац.</p>` |
| Error body shape | flat `{"error_code": "<CODE>", "message": "<text>"}` — see `backend/adapters/rest/src/error_handling/exception_handlers.py` |

## 1. Prerequisite & Format Guards

### TC-17-API-1.1 — Export of a non-existent document is refused

| Field | Value |
|---|---|
| Description | Export must not distinguish "no such id" from any other unreadable id, and must return no bytes for one. |
| Preconditions | Account A signed in; no document with the id below exists. |
| Test data | `document_id = 00000000-0000-4000-8000-000000000000`, `format=pdf` |
| Steps | 1. `GET /api/v1/documents/00000000-0000-4000-8000-000000000000/export?format=pdf` with account A's Bearer token. |
| Expected result | `404 Not Found`; `Content-Type: application/json`; body `{"error_code": "NOT_FOUND", "message": "The requested resource was not found."}`; no `Content-Disposition` header and no file bytes. |
| Status | Not run |

### TC-17-API-1.2 — Export of another account's document is refused indistinguishably

| Field | Value |
|---|---|
| Description | A `403` would confirm the id exists. The refusal must be byte-identical to the non-existent case, so an id cannot be probed. |
| Preconditions | Document B1 exists and is owned by account B; account A signed in. |
| Test data | Document B1 id `2c9a77e0-51b4-4b1e-8f0a-6d3c9b2a4e18`, `format=pdf` |
| Steps | 1. `GET /api/v1/documents/2c9a77e0-51b4-4b1e-8f0a-6d3c9b2a4e18/export?format=pdf` with account A's token.<br>2. Repeat TC-17-API-1.1 and compare the two responses byte for byte. |
| Expected result | `404 Not Found`, never `403`; the status line, headers (bar `Date`) and body of both responses are identical. |
| Status | Not run |

### TC-17-API-1.3 — An unsupported or missing format is refused

| Field | Value |
|---|---|
| Description | `format` is an enum of exactly two values; anything else must fail before any render work starts. |
| Preconditions | Document A1 exists and is owned by account A. |
| Test data | `format=rtf`, `format=` (empty), and the request with no `format` parameter at all |
| Steps | 1. `GET /api/v1/documents/7f1c2d84-0b2e-4c31-9a55-2f7b41d0e913/export?format=rtf`.<br>2. Repeat with `?format=`.<br>3. Repeat with no `format` parameter. |
| Expected result | Each of the three answers `422 Unprocessable Entity` with the JSON error shape; no file bytes; the document is not read for rendering. |
| Status | Not run |

## 2. Happy Path

### TC-17-API-2.1 — A document exports as a valid PDF

| Field | Value |
|---|---|
| Description | The primary contract: a real PDF, typed as one, delivered as a download rather than rendered inline. |
| Preconditions | Document A1 exists, owned by account A, with non-empty content. |
| Test data | Document A1, `format=pdf` |
| Steps | 1. `GET /api/v1/documents/7f1c2d84-0b2e-4c31-9a55-2f7b41d0e913/export?format=pdf` with account A's token.<br>2. Save the response body to `out.pdf` and open it. |
| Expected result | `200 OK`; `Content-Type: application/pdf`; `Content-Disposition` starts with `attachment;`; the body's first five bytes are `%PDF-`; the file opens and shows the text `Первый абзац.` |
| Status | Not run |

### TC-17-API-2.2 — A document exports as a valid DOCX

| Field | Value |
|---|---|
| Description | Same contract for the second format, including the long wordprocessingml media type Word requires. |
| Preconditions | Document A1 exists, owned by account A. |
| Test data | Document A1, `format=docx` |
| Steps | 1. `GET /api/v1/documents/7f1c2d84-0b2e-4c31-9a55-2f7b41d0e913/export?format=docx`.<br>2. Save the body to `out.docx` and open it in Word or LibreOffice. |
| Expected result | `200 OK`; `Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document`; `Content-Disposition` starts with `attachment;`; the body's first two bytes are `PK`; the file opens and shows `Первый абзац.` |
| Status | Not run |

### TC-17-API-2.3 — An empty document exports to a valid file

| Field | Value |
|---|---|
| Description | An empty document is a legitimate state, not an error state — export must produce a readable near-empty file rather than a failure. |
| Preconditions | Document A2 exists, owned by account A, with `content = ""`. |
| Test data | Document A2 id `b48d3a19-77c0-4a6d-9d21-88ec5f0a1c34`, `format=pdf` and `format=docx` |
| Steps | 1. Export document A2 as `pdf`.<br>2. Export document A2 as `docx`. |
| Expected result | Both answer `200 OK` with a file that opens; the PDF has exactly one page; no `4xx`/`5xx` in either call. |
| Status | Not run |

### TC-17-API-2.4 — Export does not mutate the document

| Field | Value |
|---|---|
| Description | Export is read-only. A version bump here would break the editor's optimistic-concurrency check on the next save. |
| Preconditions | Document A1 exists at a known version. |
| Test data | Document A1, its `version` before the export (record it, e.g. `3`) |
| Steps | 1. `GET /api/v1/documents/{A1}` and record `version`.<br>2. Export document A1 as `pdf`.<br>3. `GET /api/v1/documents/{A1}` again. |
| Expected result | The `version`, `content` and `updated_at` in step 3 are equal to those in step 1. |
| Status | Not run |

## 3. Filename & Encoding

### TC-17-API-3.1 — The filename is derived from the title, encoded for Cyrillic

| Field | Value |
|---|---|
| Description | A raw Cyrillic filename in the header is not transportable; RFC 5987 is what makes the browser save it under the document's own name. |
| Preconditions | Document A1 exists with title `Отчёт по практике`. |
| Test data | Title `Отчёт по практике`, `format=pdf` |
| Steps | 1. Export document A1 as `pdf`.<br>2. Read the `Content-Disposition` response header. |
| Expected result | The header is `attachment; filename*=UTF-8''%D0%9E%D1%82%D1%87%D1%91%D1%82%20%D0%BF%D0%BE%20%D0%BF%D1%80%D0%B0%D0%BA%D1%82%D0%B8%D0%BA%D0%B5.pdf`; the browser's Save dialog offers `Отчёт по практике.pdf`. |
| Status | Not run |

### TC-17-API-3.2 — A document with no title uses a default filename

| Field | Value |
|---|---|
| Description | An absent title must not produce an empty, `null`, or `undefined.pdf` download name. |
| Preconditions | Document A3 exists, owned by account A, with `title = null`. |
| Test data | Document A3 id `5a1e9c7b-2f44-4de8-a0b6-9c1f7d33e502`, `format=pdf` and `format=docx` |
| Steps | 1. Export document A3 as `pdf` and read `Content-Disposition`.<br>2. Export document A3 as `docx` and read `Content-Disposition`. |
| Expected result | The names are exactly `document.pdf` and `document.docx`; neither is empty and neither contains the words `null` or `undefined`. |
| Status | Not run |

### TC-17-API-3.3 — A title with header-breaking characters cannot inject into the header

| Field | Value |
|---|---|
| Description | CR/LF in a response header is header injection; a quote ends the filename token early. Both must be impossible from a user-chosen title. |
| Preconditions | Document A4 exists, owned by account A. |
| Test data | Title `отчёт"\r\nX-Injected: 1` (literal CR and LF characters), `format=pdf` |
| Steps | 1. Save document A4 with the title above.<br>2. Export document A4 as `pdf`.<br>3. Inspect the raw response headers. |
| Expected result | `200 OK`; no `X-Injected` header is present; the `Content-Disposition` value contains no raw CR, LF or `"` — they are stripped or percent-encoded; the response has exactly one header block. |
| Status | Not run |

### TC-17-API-3.4 — Multibyte content renders intact

| Field | Value |
|---|---|
| Description | Mojibake and replacement glyphs are the failure this catches: the font and the encoding path must carry every character the editor accepts. |
| Preconditions | Document A5 exists, owned by account A. |
| Test data | Content `<p>Привет 🎓 é (e + U+0301)</p>`, both formats |
| Steps | 1. Export document A5 as `pdf` and extract its text layer.<br>2. Export document A5 as `docx` and read `word/document.xml`. |
| Expected result | Both contain `Привет`, the graduation-cap emoji and the accented `é` exactly as stored; no `?`, no `�`, no empty tofu box in the rendered PDF. |
| Status | Not run |

### TC-17-API-3.5 — A save immediately followed by an export reflects the latest content

| Field | Value |
|---|---|
| Description | Export reading a lagging replica would hand the user the previous version of their own document seconds after they saved it. |
| Preconditions | Document A1 exists; the read path is pointed at a replica with induced lag, or single-primary reads are recorded (see the note). |
| Test data | New content `<p>Свежий абзац.</p>`, new title `Свежий отчёт`, export within 1 second of the save |
| Steps | 1. `PUT /api/v1/documents/{A1}` with the new content and title.<br>2. Immediately (< 1 s) export document A1 as `pdf`. |
| Expected result | The PDF contains `Свежий абзац.` and the filename reflects `Свежий отчёт` — not the previous content or title. |
| Status | Not run |
| Note | If the deployment has no read replica, record that reads are single-primary and that the lag model is unnecessary. |

### TC-17-API-3.6 — A long multibyte title is truncated on a grapheme boundary

| Field | Value |
|---|---|
| Description | Truncating by bytes can split a UTF-8 sequence or an emoji ZWJ cluster, producing a filename the OS refuses or shows broken. |
| Preconditions | Document A6 exists, owned by account A. |
| Test data | Title = `Отчёт🎓` repeated until it exceeds the filename cap (e.g. 300 characters), `format=pdf` |
| Steps | 1. Save document A6 with that title.<br>2. Export it as `pdf` and decode the `filename*` value. |
| Expected result | The decoded name is at or below the cap; it ends on a whole character (no lone surrogate, no partial UTF-8 sequence, no split emoji); it still ends in `.pdf`. |
| Status | Not run |
| Note | If there is no filename length cap, record that explicitly instead of running this case. |

## 4. Safety

### TC-17-API-4.1 — Embedded external URLs do not cause an outbound request

| Field | Value |
|---|---|
| Description | A renderer that fetches whatever the document references turns every export into an SSRF request from inside the network. |
| Preconditions | Document A7 exists, owned by account A; an HTTP listener is running on the internal address named below and its access log is empty. |
| Test data | Content `<p><img src="http://127.0.0.1:9099/pixel.png"></p>`, listener on `127.0.0.1:9099`, `format=pdf` |
| Steps | 1. Export document A7 as `pdf`.<br>2. Read the listener's access log. |
| Expected result | `200 OK` and a file is produced; the listener log has zero entries; no DNS lookup or socket to any non-database host is made during the render. |
| Status | Not run |

### TC-17-API-4.2 — A pathological document aborts within the render deadline

| Field | Value |
|---|---|
| Description | Without a deadline a single crafted document occupies a worker indefinitely; without freeing the worker afterwards, aborting achieves nothing. |
| Preconditions | Document A8 exists whose render exceeds the deadline; the clock is injectable at the deadline boundary. |
| Test data | Render deadline `30 s`; clock pinned to `deadline − 1 s`, then to `deadline + 1 s` |
| Steps | 1. Export document A8 with the clock just under the deadline.<br>2. Export document A8 with the clock just over it.<br>3. After each, issue a normal export of document A1. |
| Expected result | Step 1 completes with `200 OK`; step 2 answers `500` with the generic error body; in both cases the step-3 export of A1 answers `200 OK` promptly, proving the worker was freed and no render was left detached. |
| Status | Not run |

### TC-17-API-4.3 — Error bodies expose no internal detail

| Field | Value |
|---|---|
| Description | A stack frame, a filesystem path or a database message in an error body tells an attacker the stack, the layout and the query. |
| Preconditions | Each failure path can be triggered with a seeded sentinel value. |
| Test data | Sentinels `/srv/textery/secret-path`, `relation "documents" does not exist`, `File "/app/usecase/src/document/export_document.py", line 42` |
| Steps | 1. Trigger each failure path (render failure, deadline abort, storage error) with its sentinel seeded.<br>2. Read the response body of each.<br>3. Read the application log lines emitted at client level. |
| Expected result | Every response is `500` with exactly `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}`; no sentinel string appears in any response body. |
| Status | Not run |

### TC-17-API-4.4 — A render failure emits an attributable signal

| Field | Value |
|---|---|
| Description | A generic client message is right for the user and useless for operations — the failure must still be locatable server-side by document id. |
| Preconditions | Document A8 (failing render) and document A1 (succeeding render) both exist. |
| Test data | Document A8 id `e0b4f271-3a55-4d0c-b7ef-1a9c62d4b807`, document A1 id as above |
| Steps | 1. Export document A8 and capture the server log.<br>2. Export document A1 and capture the server log. |
| Expected result | Step 1 emits exactly one error-level record containing document A8's id; step 2 emits no error-level record. |
| Status | Not run |

### TC-17-API-4.5 — An over-limit document cannot drive an unbounded render

| Field | Value |
|---|---|
| Description | If a row larger than the save limit can ever exist, export is where it becomes an out-of-memory render. |
| Preconditions | Document A9 exists whose stored content exceeds the content limit, written directly to storage. |
| Test data | Content limit `1 000 000` characters; document A9 content `1 500 000` characters |
| Steps | 1. Export document A9 as `pdf`.<br>2. Observe the process's peak memory during the call. |
| Expected result | The export refuses at its own boundary (`422`) or clamps the content to the limit and returns `200`; peak memory stays within the worker's configured ceiling; the process does not restart. |
| Status | Not run |
| Note | If the content limit is guaranteed at save (story 5) so an over-limit row is unreachable, record that guarantee as the guard instead of running this case. |
