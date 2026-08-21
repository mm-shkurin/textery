<!-- COPIED FILE. Source of truth: ProductSpecification/stories/17-export-document/tests/05_Security_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Export document — Security Tests

Stack-aware scenarios for the export endpoint. Generic auth, headers, CORS, HTTPS covered
globally and omitted.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.export@textery.test` / `Qa!Export2026` |
| Account B (a stranger) | `qa.stranger@textery.test` / `Qa!Stranger2026` |
| Access token | `Authorization: Bearer <access token of account A>` |
| Document A1 | id `7f1c2d84-0b2e-4c31-9a55-2f7b41d0e913`, title `Отчёт по практике` |
| Document B1 (owned by B) | id `2c9a77e0-51b4-4b1e-8f0a-6d3c9b2a4e18` |
| Absent document id | `00000000-0000-4000-8000-000000000000` |
| Error body shape | flat `{"error_code": "<CODE>", "message": "<text>"}` |

## 1. Authorization / IDOR

### TC-17-SEC-1.1 — A foreign or absent document is refused indistinguishably

| Field | Value |
|---|---|
| Description | A `403` on a foreign document confirms the id exists, turning export into an id oracle. Both refusals must be one answer. |
| Preconditions | Document B1 exists and is owned by account B; no document exists under the absent id; account A signed in. |
| Test data | Document B1 id, absent id, `format=pdf` |
| Steps | 1. `GET /api/v1/documents/2c9a77e0-51b4-4b1e-8f0a-6d3c9b2a4e18/export?format=pdf` with account A's token.<br>2. `GET /api/v1/documents/00000000-0000-4000-8000-000000000000/export?format=pdf` with the same token.<br>3. Compare the two responses byte for byte, and compare their response times. |
| Expected result | Both answer `404 Not Found`, never `403`; both bodies are `{"error_code": "NOT_FOUND", "message": "The requested resource was not found."}`; status line and headers (bar `Date`) are identical; no `Content-Disposition` and no file bytes in either; the timing difference does not distinguish the two. |
| Status | Not run |

## 2. Header Injection

### TC-17-SEC-2.1 — A title cannot inject into the response headers

| Field | Value |
|---|---|
| Description | CR/LF in a response header splits the response; a bare quote ends the filename token early. A user-chosen title reaches `Content-Disposition`, so both must be impossible. |
| Preconditions | Document A4 exists and is owned by account A. |
| Test data | Document A4 id `9d21b7c5-4e63-4a70-8b12-3f0e5c8a6d47`, title `отчёт"\r\nX-Injected: 1` with literal CR and LF characters, `format=pdf` |
| Steps | 1. Save document A4 with that title.<br>2. `GET /api/v1/documents/9d21b7c5-4e63-4a70-8b12-3f0e5c8a6d47/export?format=pdf`.<br>3. Read the raw response headers off the socket. |
| Expected result | `200 OK`; the response has exactly one header block; no `X-Injected` header is present; the `Content-Disposition` value contains no raw CR, LF or `"` — they are stripped or percent-encoded — and still ends in `.pdf`. |
| Status | Not run |

## 3. SSRF

### TC-17-SEC-3.1 — Embedded URLs cause no outbound request

| Field | Value |
|---|---|
| Description | A renderer that fetches whatever the document references makes every export an SSRF request issued from inside the network, against a target the attacker chooses. |
| Preconditions | Document A7 exists and is owned by account A; an HTTP listener runs on the internal address below with an empty access log; outbound DNS and sockets are observed for the duration of the render. |
| Test data | Document A7 id `1b6f0a3d-8c92-4f57-9e30-7a4d2c5b8e61`, content `<p><img src="http://127.0.0.1:9099/pixel.png"><img src="http://169.254.169.254/latest/meta-data/"><img src="https://example.com/x.png"></p>`, listener on `127.0.0.1:9099`, `format=pdf` |
| Steps | 1. `GET /api/v1/documents/1b6f0a3d-8c92-4f57-9e30-7a4d2c5b8e61/export?format=pdf`.<br>2. Read the listener's access log.<br>3. Read the observed DNS lookups and outbound sockets for the render window. |
| Expected result | `200 OK` and a file is produced; the listener log has zero entries; zero outbound sockets and zero DNS lookups to any non-database host occurred during the render; the produced PDF simply omits the images rather than failing. |
| Status | Not run |

## 4. Fail-Closed

### TC-17-SEC-4.1 — An invalid format is rejected, never defaulted

| Field | Value |
|---|---|
| Description | Defaulting an unknown `format` to PDF makes the enum advisory; the parameter must be validated before any render work begins. |
| Preconditions | Document A1 exists and is owned by account A. |
| Test data | `format=rtf`, `format=html`, `format=PDF%00`, `format=` (empty), and no `format` parameter at all |
| Steps | 1. `GET /api/v1/documents/7f1c2d84-0b2e-4c31-9a55-2f7b41d0e913/export?format=rtf`.<br>2. Repeat for each of the other four values.<br>3. Inspect each response's status, `Content-Type` and body. |
| Expected result | Each of the five answers `422 Unprocessable Entity` with `Content-Type: application/json` and the JSON error shape; no response carries `Content-Disposition` or file bytes of any format; nothing is rendered. |
| Status | Not run |

## 5. Disclosure

### TC-17-SEC-5.1 — Render errors leak no internal detail

| Field | Value |
|---|---|
| Description | A filesystem path, a database message or a stack frame in an error body tells an attacker the stack, the layout and the query — and a log that echoes the same string leaks it to anyone with log access. |
| Preconditions | Each failure path (render failure, deadline abort, storage error) can be triggered with a seeded sentinel. |
| Test data | Sentinels `/srv/textery/secret-path`, `relation "documents" does not exist`, `File "/app/usecase/src/document/export_document.py", line 42`; the fixed redaction token used in place of internal detail |
| Steps | 1. Trigger each failure path with its sentinel seeded.<br>2. Read each response body in full.<br>3. Read the client-level application log lines emitted for each. |
| Expected result | Every response is `500` with exactly `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}`; no sentinel string — raw, encoded or partially quoted — appears in any response body or in the client-level log lines; internal detail is replaced by the fixed redaction token rather than re-encoded. |
| Status | Not run |
