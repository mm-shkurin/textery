<!-- COPIED FILE. Source of truth: ProductSpecification/stories/05-manual-mode/tests/extended/05_Security_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Manual input mode (non-AI document creation) — Security Tests (Extended)

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the owner) | `qa.manual@textery.test` / `Qa!Manual2026` |
| Document A1 | id `3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3`, `content` `<p>Первый абзац.</p>`, `version` `2` |
| Save request | `PUT /api/v1/documents/{document_id}` with `{"content": …, "version": …}` |
| Create request | `POST /api/v1/documents` `{"document_type": "реферат"}` + `Idempotency-Key` header (1–128 chars) |
| Error body shape | `{"error_code": "<CODE>", "message": "<generic text>"}` |

## 1. Sanitizer Robustness

### TC-05-SEC-EXT-1.1 — Nested and obfuscated injection payloads are neutralized the same as simple ones

| Field | Value |
|---|---|
| Description | A denylist or a single-pass stripper is defeated by nesting (`<scr<script>ipt>` reassembles after one pass), mixed case, and entity-encoded handlers — the allowlist must give the same answer for all of them as for the plain payload. |
| Preconditions | Document A1 exists and is owned by account A, signed in. |
| Test data | Payloads, each saved in turn: (a) `<script>alert(1)</script>` (plain baseline); (b) `<scr<script>ipt>alert(1)</scr</script>ipt>` (nested); (c) `<ScRiPt>alert(1)</ScRiPt>` and `<IMG SRC=x OnErRoR=alert(1)>` (mixed case); (d) `<img src=x onerror=&#97;lert(1)>` (entity-encoded handler); (e) `<a href="jav&#x09;ascript:alert(1)">ссылка</a>` |
| Steps | 1. `PUT /api/v1/documents/{A1}` with each payload in turn.<br>2. After each, `GET /api/v1/documents/{A1}` and read the raw `content`.<br>3. Render each returned content in a browser. |
| Expected result | For every payload the stored `content` carries no executable markup — no `script` element in any casing or nesting, no `on*` attribute in any casing or entity form, no `javascript:` URL however obfuscated; each result is equivalent to the plain payload (a)'s result; step 3 raises no alert for any of the five. |
| Status | Not run |

## 2. Header Injection

### TC-05-SEC-EXT-2.1 — A malformed idempotency key is rejected, not passed through

| Field | Value |
|---|---|
| Description | The idempotency key is a client-controlled header value that reaches storage and the logs. Raw CR/LF in it is log injection at best and a forged response header at worst. |
| Preconditions | Account A signed in; the application log is captured for the duration. |
| Test data | Headers: `Idempotency-Key: key-1\r\nX-Injected: 1` (literal CR and LF), `Idempotency-Key:` (empty), and a 129-character key (past the 1–128 bound) |
| Steps | 1. `POST /api/v1/documents` with the CR/LF-bearing key.<br>2. Repeat with the empty key and with the 129-character key.<br>3. Inspect each response's raw headers.<br>4. Search the idempotency-key storage and the application log for the injected value. |
| Expected result | Each of the three is refused with `422 Unprocessable Entity` carrying `{"error_code": "INVALID_IDEMPOTENCY_KEY", …}` and no document is created; no `X-Injected` header appears in any response and each response has exactly one header block; neither the key store nor the log contains a raw CR or LF or an `X-Injected: 1` line. |
| Status | Not run |
