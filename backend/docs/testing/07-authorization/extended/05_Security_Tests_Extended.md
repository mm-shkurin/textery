<!-- COPIED FILE. Source of truth: ProductSpecification/stories/07-authorization/tests/extended/05_Security_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Authorization — Security Tests (Extended)

Shared test data for both cases below:

| Name | Value |
|---|---|
| Account V (verified) | `qa.sec.verified@textery.test` / `Qa!SecVerified2026` |
| Unknown email | `qa.sec.ghost@textery.test` (no account) |
| Error body shape | `{"error_code": "<CODE>", "message": "<generic client-safe text>"}` |
| Login endpoint | `POST /api/v1/auth/login` |

---

## TC-07-SEC-E1 — Timing consistency between "unknown email" and "wrong password" login responses

| Field | Value |
|---|---|
| Description | The bodies are already identical, so the remaining enumeration oracle is the clock: an unknown email that returns after one query while a wrong password also pays for a bcrypt verify is a measurable difference an attacker can sort a mailing list by. |
| Preconditions | Account V is verified, unlocked, and not near the lockout threshold (counter reset between batches); the backend is otherwise idle. |
| Test data | Batch A: 100 logins for `qa.sec.ghost@textery.test` with password `WrongPass1!`. Batch B: 100 logins for account V with password `WrongPass1!`. Both from the same client, interleaved to cancel drift. |
| Steps | 1. Send the two batches interleaved (A, B, A, B, …), recording each response's wall-clock duration.<br>2. Compute the median and p95 for each batch.<br>3. Confirm every response in both batches is the same `401` body. |
| Expected result | Both batches return `401 {"error_code": "INVALID_CREDENTIALS", "message": "The email address or password is incorrect."}`; the two medians differ by less than the p95-minus-median spread within either batch, so timing alone does not separate the two populations. If a gap is measurable, the case fails and the fix is a dummy hash verification on the unknown-email path — not a wider tolerance. |
| Status | Not run |

## TC-07-SEC-E2 — XSS via email field reflected in any client-rendered error message

| Field | Value |
|---|---|
| Description | Whatever the user typed can come back inside an error; rendering it as HTML rather than text turns the login form into a self-XSS delivery point, and a shared link into a stored one. |
| Preconditions | The frontend is running against a backend that echoes the submitted email in its error path (or a stubbed error response that does). |
| Test data | `email` = `<img src=x onerror="window.__xss=1">@textery.test`, and `<script>window.__xss=1</script>@textery.test` |
| Steps | 1. Submit registration on `/register` with the first payload; submit login on `/login` with the same.<br>2. Repeat with the second payload.<br>3. After each, inspect the rendered error node and evaluate `window.__xss` in the console. |
| Expected result | The error area shows the payload as literal visible text (angle brackets displayed, not parsed); `document.querySelector` finds no injected `img` or `script` element inside the error node; `window.__xss` is `undefined` after every attempt; no alert or console error from executed markup. |
| Status | Not run |
