# Story 7: Authorization — Progress

Owns the story-level narrative, decisions, and the Spec checklist — shared context that
doesn't belong to one layer. `progress-backend.md` (Backend + Integration + Security +
Load + Infrastructure Scenarios) and `progress-frontend.md` (Frontend Scenarios, not yet
created — start it when frontend work begins) own the per-scenario checklists.
`ProductSpecification/stories.md` is the cross-file rollup.

## Spec Checklist

- [x] interview — `interview.md`
- [x] story — `07_Authorization.md`, `07_Authorization_Notes.md`
- [x] mockups — `mockups/` (5 screens × desktop/mobile, screenshots taken)
- [x] api-spec — `endpoints.md`, `ProductSpecification/api-specs/auth_*.yaml`
- [x] test-spec — `tests/` (main + extended), hazard-catalogue scan folded in

## Key Decisions

- Scope is email+password only this iteration — Yandex ID / VK ID OAuth explicitly
  deferred (see `interview.md` Scope).
- Design diverges from the Figma mockups' actual flow (email+OTP passwordless as
  primary, password as secondary) — user explicitly chose to keep email+password at
  registration per the original spec; Figma was used only for visual style/copy
  reference in the mockups, not for the flow itself.
- Verification code returned directly in the register/resend API response (mocked, no
  real email) — accepted resend/verify credential-disclosure trade-off, documented in
  `07_Authorization_Notes.md` Security Considerations and tested in
  `tests/05_Security_Tests.md` #10.
- 16 hazard-catalogue GAPs found across story-spec and test-spec scans (both phases) —
  all folded into named requirements/scenarios rather than dismissed; see
  `07_Authorization.md`/`07_Authorization_Notes.md` and `tests/01_API_Tests.md` §2.4a-d,
  §3.6, §5.5a, §5.6a, §5.7, §6.1a, §6.4, §6.5 for the backend-relevant ones.

## Backend Work

Branch `feature/story-7-authorization-backend`, branched from `dev` 2026-07-13.
Per-scenario checklist in `progress-backend.md`.

## What the backend actually does today

*Narrative summary of shipped behaviour, written 2026-07-16. The per-scenario checklist in
`progress-backend.md` records how each piece got there; this section records what exists,
so a reader doesn't have to reconstruct the feature from 63 checkboxes.*

**Registration is live and complete.** `POST /api/v1/auth/register` is wired into the
composition root and works end to end. A request carries an email, a password and a
confirmation; everything about validating them lives in the domain, and the usecase's only
job is to translate a domain `ValueError` into a `ValidationException` that the REST layer
renders as a 400 `{error_code, message}`. The `Email` value object caps length at 254
characters, NFC-normalizes, enforces a bounded-Unicode local part (Letter, Mark and
Decimal_Number categories only — control, format and separator characters are rejected),
and lowercases the result so the stored form is canonical. That canonicalization is what
makes case-varied and NFC/NFD-varied duplicates collide on a single database unique
constraint rather than needing an application-level check. `Password` mirrors the same
shape: 8–128 **code points** (never bytes), at least one digit, uppercase, lowercase and
special character, NFC-normalized before both the policy check and the equality test
against `confirm_password` — so a password typed in decomposed form and confirmed in
precomposed form is correctly treated as a match rather than a false mismatch.

**Duplicate rejection is enforced by the database, not by the application.** A unique
constraint on `accounts.email` is the sole serialization point: `SqlAlchemyAccountRepository.save()`
catches the resulting `IntegrityError` and raises `ConflictException`, which the usecase
translates to `EMAIL_ALREADY_REGISTERED` → 409. This was chosen over check-then-insert
specifically to close the TOCTOU race, and the choice has been verified under genuine
concurrency rather than assumed — two simultaneous registrations for the same fresh email
reliably produce exactly one 201 and one 409.

**A successful registration writes the account and its verification code atomically.** A
`UnitOfWork` port owns the single commit; the repositories only flush and add, never commit
on their own, and all three share one `AsyncSession`. Any failure on that path triggers a
best-effort rollback and surfaces a sanitized `RegistrationFailedException` — a generic 500
that never leaks driver detail. The verification code itself is a six-digit string drawn
from a CSPRNG across the full million-value space, zero-padded, expiring ten minutes out,
and treated as an opaque string end to end (VARCHAR column, `str` DTO field, no integer
coercion anywhere) so leading zeros survive. The response returns the account id, email,
verification status, the code and its expiry — never the password.

**Verification, login and refresh are now wired and live.** `VerifyAccount` normalizes and
validates the email, validates the submitted code's shape, looks up the account and its
active code, and on a match verifies the account, consumes the code and commits — with the
same rollback-and-sanitize discipline as registration. `POST /api/v1/auth/verify`,
`/login` and `/refresh` are all routed on the auth router **and wired into the composition
root** (`main.py` `dependency_overrides` for `get_verify_account_usecase`,
`get_login_user_usecase`, `get_refresh_access_token_usecase`) — the earlier "verify held
back until scenario 3.2" state no longer holds. Remaining hardening lives in the still-open
scenarios: `find_by_email`/`find_active_by_account_id` return `Optional` and some paths
dereference unconditionally, so edge cases (unknown email, wrong/expired/replayed code —
scenarios 3.2–3.6) still need their rejection branches. Consult `progress-backend.md` for
exactly which scenarios are green.

**Passwords are hashed with bcrypt.** `BcryptPasswordHasher`
(`backend/adapters/security/src/hashing/bcrypt_password_hasher.py`) implements the
`PasswordHasher` port, which is a required (no-fallback) constructor argument;
`register_user.py` hashes on the way in and `login_user.py` verifies on the way out. The
earlier "plaintext, no hashing anywhere" note is superseded — hashing shipped. See
`carryover.md` for the remaining quirk list.
