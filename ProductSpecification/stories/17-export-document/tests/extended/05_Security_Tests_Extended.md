> These are additional edge case tests. Implement after core tests pass.

# Export document — Security Tests (Extended)

Stack-aware scenarios for the export endpoint. Generic auth, headers, CORS, HTTPS covered
globally and omitted.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.export@textery.test` / `Qa!Export2026` |
| Access token | `Authorization: Bearer <access token of account A>` |
| Document A1 | id `7f1c2d84-0b2e-4c31-9a55-2f7b41d0e913`, title `Отчёт по практике` |
| Internal listener | an HTTP listener on `127.0.0.1:9099`, access log emptied before each case |
| Error body shape | flat `{"error_code": "<CODE>", "message": "<text>"}` |

## 1. SSRF Variants

### TC-17-SEC-EXT-1.1 — Embedded resources via CSS and other tags cause no request

| Field | Value |
|---|---|
| Description | Core case 4.1 blocks `<img src>`. A renderer that blocks only that tag still fetches CSS `url()`, `@import`, `<link>`, `<object>` and SVG references — each is an equally usable SSRF vector from inside the network. |
| Preconditions | Document A13 exists, owned by account A, with the content below; the listener on `127.0.0.1:9099` is running and its access log is empty; outbound DNS is captured. |
| Test data | Document A13 id `6a0d3f92-8e14-4b7c-95f2-4d1b7e0c8a36`, content `<style>@import url("http://127.0.0.1:9099/a.css"); body{background:url(http://127.0.0.1:9099/b.png)}</style><link rel="stylesheet" href="http://127.0.0.1:9099/c.css"><object data="http://127.0.0.1:9099/d.svg"></object><svg><image href="http://127.0.0.1:9099/e.png"/></svg>`, `format=pdf` |
| Steps | 1. Export document A13 as `pdf`.<br>2. Read the listener's access log.<br>3. Read the captured DNS and socket activity for the render. |
| Expected result | `200 OK` and a `%PDF-` file is produced; the listener's access log has zero entries — none of `a.css`, `b.png`, `c.css`, `d.svg`, `e.png` was requested; no socket to any host other than the database is opened during the render. |
| Status | Not run |

## 2. Filename Edge Cases

### TC-17-SEC-EXT-2.1 — A path-traversal-shaped title cannot escape the filename

| Field | Value |
|---|---|
| Description | The title becomes the download name. Path separators and `..` sequences that survive into `Content-Disposition` let a title steer where a client writes the file. |
| Preconditions | Document A14 exists, owned by account A. |
| Test data | Document A14 id `0f5b8c27-3d61-4a09-8e73-b2c46a1d9e58`; title `../../etc/passwd` (also test `..\..\windows\system32\config` and `/absolute/отчёт`), `format=pdf` |
| Steps | 1. Save document A14 with the title `../../etc/passwd`.<br>2. Export it as `pdf` and read `Content-Disposition`.<br>3. Repeat steps 1–2 with `..\..\windows\system32\config` and with `/absolute/отчёт`. |
| Expected result | `200 OK` in every case; the decoded `filename*` value in each is a single safe name containing no `/`, no `\` and no `..` segment (separators stripped or replaced), it is not empty, and it ends in `.pdf`; saving the download writes into the download directory only, never a parent of it. |
| Status | Not run |
