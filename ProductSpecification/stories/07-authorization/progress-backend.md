# Story 7: Authorization — Backend Progress

Bootstrapped 2026-07-13 from `tests/01_API_Tests.md`, `tests/06_Integration_Tests.md`,
`tests/05_Security_Tests.md`, `tests/03_Load_Tests.md`, `tests/04_Infrastructure_Tests.md`
(spec phase complete — see `progress.md` for the Spec checklist and narrative). Owns:
Backend, Integration, Security, Load, and Infrastructure Scenarios (acceptance steps stay
inline per scenario — they aren't a separable layer). Frontend scenarios live in
`progress-frontend.md`. `ProductSpecification/stories.md` is the cross-file rollup.

Working branch: `feature/story-7-authorization-backend`, branched from `dev`.

## Backend Scenarios (01_API_Tests.md)

### Scenario 1.1: Reject malformed email
- [x] red-acceptance
- [x] design (see `decisions/register-validation-error-taxonomy-decision.md`)
- [x] red-usecase
- [x] green-usecase
- [x] red-usecase (coverage: Email constructor rejects non-string input) — test added already-green, existing isinstance guard covers it
- [x] green-usecase (coverage: Email constructor rejects non-string input)
- [x] adapters-discovery (Check 1 ports: [S] none — RegisterUser.execute takes no injected port for this scenario, no persistence on this path. Check 2 exceptions: ValidationException currently maps to {"detail": str(exc)} in exception_handlers.py, not the story's {"error_code","message"} shape → gap. Check 3 response shape: no /api/v1/auth/register endpoint exists yet (only generation router) → gap. Both gaps land in the same adapter module (rest), one pair.)
- [x] red-adapter rest
- [x] green-adapter rest (must update the shared `validation_exception_handler` in `backend/adapters/rest/src/error_handling/exception_handlers.py` to emit `{error_code, message}` -- not a router-local shadow handler; the red test's isolated mini-FastAPI app doesn't exercise the shared handler, so nothing else forces this. Also add/update `test_exception_handlers.py` to pin the new shape.)
- [x] red-adapter rest (coverage: get_register_user_usecase DI stub raises NotImplementedError) — test added already-green, existing stub's unconditional raise covers it
- [S] green-adapter rest (coverage: get_register_user_usecase DI stub raises NotImplementedError) — no production change needed, stub already raises NotImplementedError
- [x] green-acceptance

### Scenario 1.2: Reject email exceeding the length limit
- [x] red-acceptance
- [S] design — no new design needed, existing Email value object (MAX_EMAIL_LENGTH=254, built for Scenario 1.1) already covers overlong emails
- [S] red-usecase — Email constructor's existing length guard already rejects 256-char input; no new usecase behavior
- [S] green-usecase — nothing to implement, guard pre-exists
- [S] adapters-discovery — REST error mapping already wired for INVALID_EMAIL in Scenario 1.1; no new adapter surface
- [x] green-acceptance

### Scenario 1.3: Reject password failing the policy
- [x] red-acceptance
- [x] design — Password value object in backend/domain, mirroring Email's constructor-validation pattern (min 8/max 128 chars, ≥1 digit, ≥1 uppercase, ≥1 lowercase, ≥1 special char per `07_Authorization.md` Validation Rules table); single INVALID_PASSWORD error code for all sub-violations, consistent with INVALID_EMAIL taxonomy. Closed a premortem gap first: red-acceptance was missing a 6th sub-case (missing-lowercase) despite it being a spec rule — added `given_registration_request_with_password_missing_lowercase` fixture + test (still skipped, 6 skipped confirmed) before this design locks scope for red-usecase.
- [x] red-usecase
- [x] green-usecase
- [x] red-usecase (coverage: Password constructor rejects non-string input) — test added already-green, existing isinstance guard covers it
- [S] green-usecase (coverage: Password constructor rejects non-string input) — no production change needed, existing isinstance guard covers it
- [x] red-usecase (coverage: password at exact upper boundary (128 chars) satisfying all policy rules is accepted) — test added already-green; `Password._is_valid` uses `len(raw_value) > MAX_PASSWORD_LENGTH` (strict `>`), so 128 chars is correctly accepted, no off-by-one bug at the boundary
- [S] green-usecase (coverage: password at exact upper boundary (128 chars) satisfying all policy rules is accepted) — no production change needed, boundary check already correct
- [x] adapters-discovery (Check 1 ports: [S] none — RegisterUser.execute takes no injected port, no persistence on this scenario's path. Check 2 exceptions: [S] — validation_exception_handler maps any ValidationException generically to {"error_code","message"}, already covers INVALID_PASSWORD as of scenario 1.1's wiring. Check 3 response shape: [S] — /api/v1/auth/register endpoint already exists and already returns the generic error body; no new adapter surface needed.)
- [x] green-acceptance

### Scenario 1.4: Reject password/confirm_password mismatch
- [x] red-acceptance
- [x] design — usecase-level equality check in RegisterUser.execute after Password validates; raise ValidationException(error_code="PASSWORD_MISMATCH", message="The password confirmation does not match."), reusing existing exception mapping. No ADR (trivial, taxonomy already locked in register-validation-error-taxonomy-decision.md).
- [x] red-usecase
- [x] green-usecase
- [x] adapters-discovery (Check 1 ports: [S] none — RegisterUser.execute takes no injected port, no persistence on this scenario's path. Check 2 exceptions: [S] — validation_exception_handler already maps ValidationException generically to {"error_code","message"}, covers PASSWORD_MISMATCH as of scenario 1.1's wiring. Check 3 response shape: [S] — /api/v1/auth/register endpoint already exists and returns the generic error body; no new adapter surface needed.)
- [x] green-acceptance

### Scenario 1.5: Ignore server-owned fields in the request body
- [x] red-acceptance
- [x] design (see `decisions/account-persistence-design-decision.md`) — domain Account entity (is_verified pinned at construction, no setter), AccountRepository port, Clock port injected now (SystemClock adapter), SQLAlchemy accounts table+migration (email unique constraint deferred to 2.2, additive-safe), dedicated RegisterResponseDto (id/is_verified only, never password_hash), per-run-unique email fixture for the 1.5 acceptance test, DB-failure error mapping.
- [x] red-usecase
- [x] green-usecase
- [x] adapters-discovery (Check 1 ports: db — no SqlAlchemyAccountRepository/accounts table/migration exists → red-adapter db / green-adapter db needed. Check 1 ports: clock — [S] SystemClock already implemented inline in register_user.py, stdlib-only datetime.now(timezone.utc), no framework dependency, no separate adapter module needed. Check 2 exceptions: [S] — scenario 1.5's persistence is a bare insert with no uniqueness constraint yet (deferred to 2.2), so no new domain exception type is introduced by this scenario to map. Check 3 response shape: rest — auth_router.register() returns `None` with `response_model=None`, discarding RegisterUser.execute's returned Account; acceptance test expects a 201 body with `id`/`is_verified` → red-adapter rest / green-adapter rest needed, including container.py wiring a real AccountRepository into create_register_user() (currently `RegisterUser()` with no args, silently using the null-object fallback per the agent-review/premortem findings on the green-usecase commit).)
- [x] red-adapter db
- [x] green-adapter db
- [x] red-adapter rest
- [x] green-adapter rest
- [x] green-acceptance

### Scenario 2.1: Valid registration creates a pending account and returns a verification code
- [x] red-acceptance
- [x] design (see `decisions/verification-code-design-decision.md`) — new VerificationCode domain entity + verification_codes table (consumed_at column added now, unused, for 3.x/4.x additive-safety), secrets.randbelow CSPRNG generation, code stored/compared as fixed-length string end-to-end. Atomic Account+VerificationCode write deferred to scenario 2.5 (its own named scenario); email-uniqueness/concurrency deferred to 2.2/2.4a (their own named scenarios) — both accepted, tracked gaps per hazard-scan groups 2/3, not silent.
- [x] red-usecase
- [x] green-usecase
- [x] adapters-discovery (Check 1 ports: db — no SqlAlchemyVerificationCodeRepository/verification_codes table/migration exists → red-adapter db / green-adapter db needed. AccountRepository/Clock: [S] already sufficient from scenario 1.5. Check 2 exceptions: [S] — no new domain exception type introduced (bare insert, same as 1.5). Check 3 response shape: rest — RegisterResponseDto only has user_id/is_verified, missing verification_code/code_expires_at that the response schema (api-specs/auth_register.yaml) and the acceptance test require → red-adapter rest / green-adapter rest needed, including container.py wiring a real VerificationCodeRepository into create_register_user() (currently silently using the null-object fallback per the premortem finding on the green-usecase commit).)
- [x] red-adapter db
- [x] green-adapter db — SqlAlchemyVerificationCodeRepository.save() implemented; also closed carried-forward consumed_at reconstruction gap via VerificationCode.reconstitute() (both agent-review and premortem flagged it in the owed review batch for red-adapter db). Test-coverage: clean, remaining uncovered lines are the not-yet-exercised reconstitute() read-back path, correctly out of scope until 3.x/4.x consume the codes.
- [x] red-adapter rest — response-shape only (RegisterResponseDto missing email/verification_code/code_expires_at per api-specs/auth_register.yaml; `email` gap was missed at adapters-discovery time and independently caught by both agent-review and premortem, folded into this same red test before green-adapter rest locked scope); container.py null-object DI wiring gap deferred to green-adapter rest, not a separate red test
- [x] green-adapter rest — RegisterResponseDto.from_domain now built from full RegistrationResult (email/verification_code/code_expires_at added); auth_router.register() passes full result; container.py wires real SqlAlchemyVerificationCodeRepository, replacing null-object fallback. Test-coverage: 14 passed, 0 failed; register_response_dto.py and auth_router.py both 100% line/branch coverage — no gaps.
- [x] green-acceptance

### Scenario 2.2: Duplicate email is rejected, verified or pending
- [x] red-acceptance — two sub-cases (duplicate against verified account, duplicate against pending account); `/verify` endpoint doesn't exist yet so the "verified" setup calls the new `client.verify()` test-infra helper without asserting on it (404s silently today) — duplicate-rejection assertion fails identically either way since no duplicate check exists at all yet
- [x] design — DB-level unique constraint/index on `accounts.email` (case-sensitive, exact-match; case-fold uniqueness deferred to Scenario 2.3, out of scope here). `SqlAlchemyAccountRepository.save()` catches the resulting `IntegrityError` and raises a defined exception (closes the "no exception mapping" gap logged in `carryover.md`). `RegisterUser.execute` lets it propagate; new error code `EMAIL_ALREADY_REGISTERED` → 409 via the existing generic exception mapping wired since 1.1. No new rest adapter surface needed. Chosen over app-level check-then-insert to avoid the TOCTOU race Scenario 2.4a will test. No ADR (mechanical, low-ambiguity, matches this story's existing 1.5/2.1 pattern). Known gap not fixed here: the already-committed red-acceptance test's "verified account" sub-case can't actually verify yet (`/verify` doesn't exist until 3.x) — flagged by both review passes on the red-acceptance commit, left deferred/tracked, not blocking.
- [x] red-usecase — mocks `AccountRepository.save()` to raise `ConflictException` (reused from `generation_storage.py`'s optimistic-concurrency use), asserts `RegisterUser.execute` translates it to `ValidationException(error_code="EMAIL_ALREADY_REGISTERED")`; test-review strengthened to also assert no account and no verification code are persisted on the duplicate path (closes the scenario docstring's "no second account is created" clause)
- [x] green-usecase — RegisterUser.execute wraps AccountRepository.save() in try/except ConflictException, translates to ValidationException(error_code="EMAIL_ALREADY_REGISTERED"); duplicate rejection happens before verification-code generation, so no orphan code on the reject path. usecase suite: 45 passed, 0 failed.
- [x] adapters-discovery (Check 1 ports: db — `accounts.email` has no unique constraint/migration and `SqlAlchemyAccountRepository.save()` has no `IntegrityError`→`ConflictException` mapping → `red-adapter db` / `green-adapter db` needed. Check 2 exceptions: rest — `validation_exception_handler` maps every `ValidationException` to HTTP 400 uniformly, but `01_API_Tests.md` requires HTTP 409 for `EMAIL_ALREADY_REGISTERED` specifically (other error codes stay 400) → `red-adapter rest` / `green-adapter rest` needed for per-error-code status mapping. Check 3 response shape: [S] — endpoint already returns the generic `{error_code,message}` body; only the status code differs, covered by Check 2.)
- [x] red-adapter db — asserts `SqlAlchemyAccountRepository.save()` raises `ConflictException` on duplicate email; fails with `AssertionError: expected ConflictException, got None` as predicted (no unique constraint, no exception mapping yet)
- [x] green-adapter db — added `accounts.email` unique-constraint migration; `save()` catches `IntegrityError`, rolls back, raises `ConflictException`. Coverage: `account_storage.py` 100% lines/branches (`--cov-branch`); db suite 10 passed, 0 failed. No gaps to close; migration DDL not meaningfully coverable by unit tests.
- [x] red-adapter rest — asserts `validation_exception_handler` returns HTTP 409 for `EMAIL_ALREADY_REGISTERED`; fails with `assert 400 == 409` as predicted (handler currently maps every ValidationException to 400 uniformly); existing 400 test for other error codes still passes unchanged
- [x] green-adapter rest — `validation_exception_handler` now maps status via an explicit `_ERROR_CODE_STATUS_MAP` dict (`EMAIL_ALREADY_REGISTERED` → 409, default 400), avoiding a silent-default if/else per premortem guidance on the red commit. Coverage: `exception_handlers.py` 100% lines/branches. rest suite: 15 passed, 0 failed.
- [x] green-acceptance — both sub-cases pass (2 passed). Fixed a stale literal along the way: acceptance fixture `EXPECTED_DUPLICATE_EMAIL_ERROR`'s message text ("An account already exists for this email.") never matched the usecase's already-committed message ("An account with this email address already exists.") — aligned the fixture to the usecase text rather than the reverse, since the usecase/rest message was locked first (red-usecase/green-usecase, red-adapter rest/green-adapter rest all already pinned it). Known gap carried from red-acceptance still open: the "verified account" sub-case can't actually verify yet (`/verify` doesn't exist until 3.x) — harmless here since duplicate rejection doesn't depend on verification status, but tracked, not newly introduced.

### Scenario 2.3: Case-folded email uniqueness
- [x] red-acceptance — registers `user-{uuid}@example.ru` then `USER-{uuid}@Example.ru` (same local part, different case); fails with `expected 409 Conflict (duplicate email), got status_code=201` as predicted (current unique constraint is case-sensitive, mixed-case duplicate slips through)
- [x] design (see `decisions/case-folded-email-uniqueness-decision.md`) — normalize email to lowercase inside the `Email` value object (`Email.value` returns the canonical form); `RegisterUser.execute` persists `Email(email).value` instead of the raw request casing. No new migration: scenario 2.2's `uq_accounts_email` constraint already enforces uniqueness once storage is canonical. Rejected app-level case-insensitive check-then-insert (reopens the 2.2 TOCTOU race) and a separate functional unique index (leaves the raw column un-normalized, breaks future case-insensitive login). Addresses both credible premortem incidents on the red-acceptance commit.
- [x] red-usecase — two tests: `Email("User@Example.RU").value` should return lowercased `"user@example.ru"` (fails: raw value unchanged); `RegisterUser.execute` should persist the normalized email (fails: raw casing persisted). Both fail as predicted. test-review strengthened the usecase assertion to cover full Account round-trip (id/is_verified/created_at, not just email) and deduplicated `register_statements.py` back under the 200-line limit.
- [x] green-usecase — `Email.__init__` now lowercases `raw_value` after validation; `RegisterUser.execute` uses `email_value_object.value` (normalized) instead of the raw email string. Coverage: `register_user.py` 100%; `email.py` 95% (one pre-existing uncovered branch from scenario 1.1's length guard, out of scope here). domain 11 passed, usecase 46 passed, no regressions.
- [x] adapters-discovery (Check 1 ports: [S] none — RegisterUser.execute's injected ports (AccountRepository, Clock, VerificationCodeRepository) are unchanged since 2.1/2.2; email normalization happens purely inside the domain `Email` value object and the usecase, no new adapter surface. Check 2 exceptions: [S] — same `ConflictException`→`ValidationException(EMAIL_ALREADY_REGISTERED)`→409 path from 2.2, reused as-is since storage is now canonical and the existing `uq_accounts_email` constraint catches case-varied duplicates directly. Check 3 response shape: [S] — `RegisterResponseDto.from_domain` already returns `result.account.email` (now the normalized/lowercased value), no DTO change needed; scenario 2.3's red-acceptance test only asserts the duplicate-rejection error shape, identical to 2.2's already-wired `EXPECTED_DUPLICATE_EMAIL_ERROR`.)
- [x] green-acceptance — passes unskipped, no production change needed (email normalization already lands the DB unique constraint on the canonical value). Full authorization acceptance suite re-run for regression: 14 passed, 0 failed.

### Scenario 2.4: A retried identical registration request produces exactly one account
- [x] red-acceptance — test added already-green: an identical retry (same email/password/confirm_password) is already rejected by scenario 2.2's duplicate-email mechanism (409 EMAIL_ALREADY_REGISTERED, DB unique constraint); passed on first run, no RED phase occurred
- [S] design — no new design needed, 2.2's mechanism already satisfies this scenario
- [S] red-usecase — no new usecase behavior; RegisterUser.execute generates the verification code only after account save succeeds, so a duplicate-rejected retry never reaches code generation either ("exactly one code" falls out of "exactly one account" for free). Both review passes on the acceptance commit flagged that the acceptance test only proves the account-side (409 response shape) and asked whether the "exactly one verification code" half of the Gherkin is actually guarded anywhere: it is -- scenario 2.2's already-committed usecase test `TestRegisterUsecaseDuplicateEmail` (`backend/usecase/tests/auth/test_register_duplicate_email_usecase.py`) asserts `verification_code_repository.saved_codes == []` on the exact same duplicate-rejection code path this retry exercises, so a future regression that reorders code-generation before the uniqueness check would already fail that existing test. Not a new gap; the guard predates this scenario, just not visible from the acceptance layer alone.
- [S] green-usecase — nothing to implement
- [S] adapters-discovery — no new adapter surface, reuses 2.2's wiring end-to-end
- [x] green-acceptance — passes as-is (not skip-marked, stands as a normal regression test pinning already-shipped behavior). Note (agent-review): behaviorally near-identical to scenario 2.2's `given_duplicate_registration_against_pending_account` case -- adds no new production-code coverage, but is kept as its own scenario since 01_API_Tests.md documents it as a distinct spec requirement (retry-idempotency, not just duplicate-rejection) worth pinning by name.

### Scenario 2.4a: Concurrent registration for the same brand-new email creates exactly one account
- [x] red-acceptance — test added already-green: `given_two_concurrent_registrations_for_same_new_email()` fires two identical registration requests for a brand-new email via `asyncio.gather` (submitted at the same instant, not sequentially), asserting exactly one 201 and exactly one 409 EMAIL_ALREADY_REGISTERED among the pair. Verified empirically, not assumed: ran 5 consecutive times against the live backend (`BACKEND_PORT=8100`), all 5 passed (1 passed each run). Scenario 2.2's DB-unique-constraint mechanism (chosen specifically over app-level check-then-insert to avoid this exact TOCTOU race, per 2.2's design note) is confirmed race-safe under real concurrent HTTP requests — the losing request's `IntegrityError` is caught by `SqlAlchemyAccountRepository.save()` and mapped to `ConflictException` → `EMAIL_ALREADY_REGISTERED` → 409, same as the sequential case. No RED phase occurred.
- [S] design — no new design needed, 2.2's DB-constraint mechanism already satisfies this scenario (that was the whole point of choosing it in 2.2)
- [S] red-usecase — no new usecase behavior; `RegisterUser.execute`'s existing try/except around `AccountRepository.save()` (from 2.2) is what makes the losing concurrent request translate `ConflictException` to `EMAIL_ALREADY_REGISTERED` regardless of whether the race was sequential or concurrent — the DB is the sole serialization point, not application code
- [S] green-usecase — nothing to implement
- [S] adapters-discovery — no new adapter surface, reuses 2.2's db unique-constraint + rest status-mapping wiring end-to-end
- [x] green-acceptance — passes as-is (not skip-marked, stands as a normal regression test pinning already-shipped race-safety behavior under genuine concurrency, distinct from 2.4's sequential-retry case)

### Scenario 2.4b: Case-fold uniqueness is locale-invariant
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.4c: Unicode-normalization uniqueness for email
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.4d: Password length limit is measured in code points, not bytes
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.5: Registration writes the account and the verification code atomically
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.6: Verification code round-trips with leading zeros preserved
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.7: Password is NFC-normalized before hashing
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: Correct code activates the account
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.2: Incorrect code is rejected
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.3: Expired code is rejected, exact boundary enforced
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.4: Re-submitting an already-consumed code is idempotent
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.5: Verify against an already-verified account is rejected
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.6: Concurrent verify requests for the same account produce exactly one transition
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.1: Resend issues a new code and invalidates the previous one
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.2: Resend within the cooldown window is rejected
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.3: Resend invalidates the old code and issues the new one atomically
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.4: Concurrent resend requests do not both succeed within the cooldown
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.5: Resend against an already-verified account is rejected
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.1: Login rejected while account is unverified
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.2: Invalid credentials return a single generic error
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.3: Failed-attempt counter increments atomically across concurrent failures
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.4: Account locks out after N consecutive failed attempts
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.5: Lockout auto-expires after the cooldown window
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.5a: Lockout cooldown boundary is enforced at the exact expiry instant
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.6: Lockout read failure fails closed
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.6a: Verification-flag read failure fails closed
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.7: Malicious email/password input does not cause a validation hang
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.1: Valid credentials on a verified account issue a token pair
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.1a: Failed-attempt-counter reset and refresh-token persistence commit as one unit
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.2: Refresh returns a new access token for a valid refresh token
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.3: Refresh rejects an expired or invalid refresh token
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.4: Refresh rejects a token whose claim shape no longer matches current code
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.5: Access token is valid up to, not past, its exact expiry instant
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Integration Scenarios (06_Integration_Tests.md)

### Scenario 1: Full Register → Verify → Login → Refresh Pipeline
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2: Refresh Token Reuse After Access Token Expiry
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3: Login Immediately Usable Against a Protected Route
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Security Scenarios (05_Security_Tests.md)

### Scenario 1: Password Hashing
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2: Verification Code Never Logged Beyond the Mocked Response
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3: Mass Assignment on Registration
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4: SQL Injection via Email Field
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5: Log Injection via Email Field
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6: Rate Limiting — Login Brute Force
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 7: Rate Limiting — Resend-Code Abuse
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 8: JWT — Algorithm and Expiry Enforcement
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 9: Refresh Token Rejected After Signing-Key Rotation
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 10: Resend/Verify Credential Disclosure — Documented, Rate-Limited Exposure
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 11: Sentinel Secret Absent From Every Failure Path
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 12: Fail-Closed Paths Emit a Distinguishable Signal
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Load Scenarios (03_Load_Tests.md)

### Scenario 1.1: Sustained concurrent login/register traffic stays within the connection pool budget
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.2: Requests beyond pool capacity get a bounded wait or an explicit reject, never an unhandled hang
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1: Login endpoint sustains the configured request rate
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Infrastructure Scenarios (04_Infrastructure_Tests.md)

### Scenario 1: Database connection failure during auth request
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2: Database recovery after failure
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3: JWT signing secret misconfiguration at startup
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance
