# OAuth sign-in — Security Tests (Extended)

> These are additional edge case tests. Implement after core tests pass.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Provider identity P1 | provider `yandex`, subject `1000000000000123`, email `qa.oauth@textery.test`, account id `4c8f1a92-6d3b-4e77-9a10-5b2f8c7d1e04` |
| Provider identity P2 | provider `yandex`, subject `2000000000000456`, email `qa.stranger@textery.test`, account id `d31b8e07-95a4-4c62-b8e3-70f2a1c94d68` |
| Handoff code for P1 | `hc_9f3b7c2a1d4e4f8b9c0a6d5e2f31b847` |
| Exchange call | `POST /api/v1/auth/oauth/exchange` body `{"code": "<code>"}` |
| App default target | `/` (the `safeRedirectTarget` fallback) |

---

## 1. Handoff-code hardening

### TC-16-SEC-1.1 — A handoff code from a different session cannot be exchanged elsewhere

| Field | Value |
|---|---|
| Description | The code carries the identity, not the caller: if a stolen or copied code could be redeemed into a different browser's session as a different account, the whole handoff would be a lateral-movement primitive. |
| Preconditions | A handoff code was minted for P1's sign-in attempt; a second, unrelated browser/session belonging to P2 is available. |
| Test data | P1's code `hc_9f3b7c2a1d4e4f8b9c0a6d5e2f31b847`, presented from P2's browser with P2's cookies/headers and a different `X-Forwarded-For` source |
| Steps | 1. Mint the code through P1's sign-in but do not spend it.<br>2. From the unrelated context, POST the exchange with P1's code.<br>3. Decode the returned access token, if any. |
| Expected result | The exchange binds only to the identity the code was minted for: any session it yields is for account `4c8f1a92-6d3b-4e77-9a10-5b2f8c7d1e04` (P1) — never P2's `d31b8e07-…`; nothing in the request context (cookies, headers, source) can redirect the code onto another account; the code is spent exactly once either way. |
| Status | Not run |

---

## 2. Redirect hardening

### TC-16-SEC-2.1 — A protocol-relative or scheme-crafted redirect target is rejected

| Field | Value |
|---|---|
| Description | `startsWith('//')` alone is not the guard: browsers normalize a backslash in the authority position, and a `javascript:`/`data:` scheme is a script execution rather than a navigation. |
| Preconditions | A signed-out visitor; the exchange resolves a valid session. |
| Test data | Targets `//evil.test`, `/\evil.test`, `/\/evil.test`, `//\evil.test`, `https://evil.test/steal`, `javascript:alert(1)`, `data:text/html,<script>alert(1)</script>` |
| Steps | 1. Complete the callback sign-in once per crafted target.<br>2. After each, read the resulting URL, the document origin and the network log. |
| Expected result | Every run lands on the in-app default `/`; the document origin never becomes `evil.test`; no request to `evil.test` appears in the network log; no script executes for the `javascript:`/`data:` targets. |
| Status | Not run |
