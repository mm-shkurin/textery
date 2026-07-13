# Interview: Story 7 — Authorization (email+password, mocked verification code)

## Scope

In scope for this iteration:
- Registration with email + password.
- Email verification via a 6-digit mocked code (no real mail integration — code is
  returned directly in the API response body).
- Login with email + password (only after verification).
- JWT access + refresh token issuance and refresh flow.
- Basic rate limiting on login attempts and resend-code requests.

Out of scope (explicitly deferred): Yandex ID OAuth, VK ID OAuth. The story title in
`stories.md` lists them alongside email+password, but the user confirmed only
email+password ships in this iteration — OAuth providers become a follow-up story/task
once this lands. NOT YET IMPLEMENTED.

Also out of scope: real email delivery (SMTP/mail provider integration), password
reset/forgot-password flow (not raised this round — revisit if needed before test-spec
sign-off), account deletion, profile management (story 13).

## Key Architectural Decisions

DECISION: Registration creates the user account immediately with `is_verified=false`
(pending state) rather than staging in a separate table — login is blocked until the
verification code is confirmed.

DECISION: Verification code is a 6-digit numeric code, TTL 10 minutes, returned directly
in the registration/resend API response body (mocked — no real email sending). This
matches the product brief's "email verification code mocked — no real mail integration".

DECISION: Sessions use JWT — short-lived access token + longer-lived refresh token, per
the tech profile (`PyJWT`, `ProductSpecification/technology.md` "Auth (story 7+)" row).
Exact TTLs to be finalized during `/api-spec` (typical: access ~15-30min, refresh
~7-30 days).

DECISION: Passwords hashed with bcrypt (via `passlib` or equivalent), never stored or
logged in plaintext.

## Business Rules & Constraints

- Password policy: minimum 8 characters, at least 1 digit, at least 1 uppercase letter,
  at least 1 lowercase letter, at least 1 special character. Enforced server-side on
  registration.
- Verification code: 6 digits, expires 10 minutes after issuance. A new registration or
  explicit resend issues a new code (invalidates the previous one).
- Rate limiting (basic, in-scope for this story — not deferred to a later security/load
  pass):
  - Resend-code requests: no more than one per 60 seconds per account/email.
  - Login attempts: lock out after N consecutive failed attempts (exact N to be decided
    at api-spec/design time, e.g. 5).
- Login is rejected with a clear error while `is_verified=false`.
- Email must be unique per account; duplicate registration attempts on an existing
  (verified or pending) email are rejected with a clear error.

## Already Implemented (REUSE)

NOT YET IMPLEMENTED — no existing `User`/`Auth` domain entities, usecases, or adapters
were found under `backend/domain/src`, `backend/usecase/src`, or `backend/adapters/*/src`.
This story starts the auth slice from scratch. Story 1 (auto-generate: доклад) has
existing backend/frontend scaffolding and conventions to follow, but no auth-specific
code to reuse.

## NOT Yet Implemented (Gaps)

- `User` domain entity (email, password hash, verification state, timestamps).
- Registration usecase (create pending user + generate verification code).
- Verify-code usecase.
- Resend-code usecase (with rate limit).
- Login usecase (credential check + JWT issuance).
- Refresh-token usecase.
- REST adapter: `POST /auth/register`, `POST /auth/verify`, `POST /auth/resend-code`,
  `POST /auth/login`, `POST /auth/refresh`.
- DB adapter: user repository + migration for the users table.
- JWT signing/verification infrastructure (secret/key management — via `infra/.env`,
  per infra rules; no hardcoded secrets).
- Frontend: registration form, verification-code entry screen, login form, token storage
  and auth-guarded routing.
- Yandex ID / VK ID OAuth — deferred, see Scope.

## Cross-Story Dependencies

- Story 1 (auto-generate: доклад) currently has no auth gate — once this story ships,
  document generation and history endpoints will need to require an authenticated user.
  That wiring (protecting existing endpoints) is a follow-up, not part of this story's
  scope unless raised again before implementation starts.
- Story 8 (Billing/tariffs) will depend on the `User` entity this story creates (tariff
  assignment per user).
- Story 13 (Profile management) will extend the `User` entity/usecases introduced here.

## Testing Considerations

- Verification code being returned in the API response (rather than sent via email) is
  what makes this testable end-to-end without a mail integration — acceptance tests can
  register, read the code from the response, then verify.
- Rate-limit scenarios (resend cooldown, login lockout) need explicit test coverage in
  this story's backend/security scenarios, not deferred to a separate load pass — the
  user confirmed basic rate limits are in scope now.

## Performance/Rate Limits

Per `ExpectedLoad.md`, the platform targets hundreds of concurrent users. Auth endpoints
are synchronous (no LLM call involved) so no async/queue concern here, but rate-limit
state (login lockout counters, resend cooldown) must be stored in the database or a
shared cache — never in-process memory — per the "Deployment" rule in
`.claude/rules/coding-rules.md` (backend runs as multiple instances).
