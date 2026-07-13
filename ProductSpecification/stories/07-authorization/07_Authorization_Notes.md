# Authorization - Notes & Considerations

## Warnings

### Functional Warnings

- Resend-code must invalidate the previous code (single active code per account) — a
  stale code accepted after a resend would let an attacker who observed an old code in
  transit/logs still verify.
- Login lockout counter must reset on successful login and must be scoped per-account
  (not per-IP) unless a separate IP-based limit is added later — an account-only lockout
  is bypassable by rotating source IP but is the agreed baseline for this story.
- Registration on an email that exists but is unverified: reject as duplicate rather than
  silently re-issuing a code — resend-code is the intended path for "I didn't get my
  code", keeping one clear route avoids ambiguous UX and avoids a bypass of the 60s
  resend cooldown via re-registration.

### UI/UX Warnings

- Verification-code screen must clearly show the mocked code isn't emailed — for a live
  product this would be a security bug, but here it's the intentional mock; the frontend
  should surface the code directly (e.g., "Your code: 123456 (dev mode, no email sent)")
  so testers aren't confused.
- Distinguish "wrong password" vs "account locked" vs "not verified" errors in the login
  form so users know which action to take next (retry vs wait vs verify).
- Refreshing/navigating away from the verify-code screen must not force an unwanted
  resend (which would immediately hit the 60s cooldown) — decide whether the entered
  code survives a refresh or the screen re-fetches state without auto-triggering resend.
- Network/loading states need their own treatment distinct from validation errors: a
  failed request (timeout, 5xx) should show a retry-capable error, not an indefinite
  spinner or a validation-style message.

### Technical Warnings

- Rate-limit/lockout state MUST live in the database, not in-process memory — the
  backend runs as multiple instances (`.claude/rules/coding-rules.md` Deployment). An
  in-memory counter would let an attacker distribute attempts across instances and never
  trip the lockout.
- Never log the verification code or password anywhere persistent logs could retain them
  beyond the mocked API response (structured logs, error trackers) — even though the
  code is "mocked", treat it like a real credential in logging discipline.
- Token secret/signing key must come from `infra/.env`, never hardcoded or committed —
  per Infrastructure guardrails.

---

## Suggestions & Future Enhancements

### Functional Suggestions

- Password reset / forgot-password flow (out of scope this story, flagged in
  `interview.md`) — natural next story once this lands.
- Yandex ID / VK ID OAuth (explicitly deferred per interview.md).

### UI/UX Suggestions

- Password-strength meter on the registration form as the user types.

### Technical Suggestions

- Consider a dedicated `verification_codes` table separate from `users` so code history/
  audit isn't mixed with account state — decide at design-preview time.

---

## Technical Notes

### Load Considerations

Per `ExpectedLoad.md`: hundreds of concurrent users. Auth endpoints are synchronous
(no LLM/external call), so no async/queue requirement — but DB writes for lockout
counters and code issuance must use connection pooling sized for that concurrency, same
as the rest of the backend. This needs a concrete guard, not just a sizing statement:
a load/backend scenario that exercises concurrent login/register/verify (including the
failure branches — locked-out login, expired-code verify, duplicate-email register) and
asserts the connection pool returns to baseline afterward, plus a defined behavior
(bounded wait vs. explicit reject) when the pool is exhausted.

Max input length: `email` (255 chars) and `password` (128 chars) need an explicit upper
bound rejected with 4xx before hashing/DB write — an unbounded string is a resource-
amplification vector even though the password policy only states a minimum today.

### Security Considerations

- OWASP: password hashing (bcrypt), account enumeration (registration/login error
  messages should avoid confirming whether an email exists where practical — balance
  against the "reject as duplicate" UX decision above, which does reveal existence by
  design; acceptable trade-off for this story per interview.md, revisit if security
  scenario phase flags it), brute-force protection (lockout), rate limiting (resend
  cooldown).
- JWT: short-lived access token limits blast radius of a leaked token; refresh token
  rotation is a candidate future hardening (out of scope this story — plain refresh
  reuse is the MVP baseline).
- IDOR / credential disclosure via resend-code (hazard scan group 5 GAP): because the
  mocked verification code is returned directly in the `resend-code`/`register` response
  body (product requirement), any caller who supplies a victim's email can retrieve that
  account's live code — a real account-takeover path if this endpoint shape were ever
  exposed against a real mailbox. Accepted for this mock/demo scope (see Core
  Requirements in the main spec); the 60s resend cooldown is the only friction. Flag
  explicitly before any production mail-based rollout — would need a
  registration-session token instead of raw email.
- Client-safe error contract: every failure path (bad credentials, locked, unverified,
  expired/invalid code, invalid/expired refresh token, unexpected server error) must
  return a defined, generic error shape — no stack traces, SQL fragments, or internal
  ids leak to the caller. Needs a named test per failure family, not just the happy path.
- Sentinel-secret test: seed a known password/code, trigger every failure path, assert
  the sentinel never appears in the response body or in captured log output.
- Mass assignment: registration must bind only `email`/`password` from the request body
  — a client-supplied `is_verified`, `id`, or similar field must be ignored, not bound
  onto the created user. Needs an explicit test.
- Fail-closed: a DB error/timeout while reading the lockout counter or verification flag
  during login must deny the login, not silently allow it through on an unhandled
  exception path.
- Email field is a sink for query/log/response output as well as an input — parameterize
  the uniqueness lookup and sanitize before writing to structured logs to avoid
  log-forging via crafted email values (e.g. embedded CR/LF).

### Infrastructure Notes

- JWT signing secret via `infra/.env`. No new infra services required — auth uses the
  existing Postgres.

### Integration Notes

No external API integrations in this story (mocked email, no OAuth). See `interview.md`
for the full scope boundary — Yandex ID/VK ID are separate integrations deferred to a
follow-up story.

---

## Additional Context

See `interview.md` for the full round-by-round decision record: password policy
rationale, rate-limit specifics, cross-story dependencies (story 1 auth-gating, story 8
billing, story 13 profile), and the explicit OAuth deferral decision.
