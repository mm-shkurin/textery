# Decision: VerifyAccount usecase and read-path additions

**Date**: 2026-07-15 **Scenarios**: 3.1 (and forward-compatible with 3.2–3.6)

`POST /api/v1/auth/verify` needs to look up a pending account by email, find its
active verification code, compare it to the submitted code, and — on match —
transition the account to verified. Today both repository ports only expose
`save()`; there is no read path at all, and `Account` has no way to represent
a verified account after reconstruction (`carryover.md` quirk from scenario 1.5:
`Account.__init__` hardcodes `is_verified=False`, no setter, no `reconstitute`).

| Rejected | Why |
|----------|-----|
| Add a `verify(email, code)` method directly on `AccountRepository`, doing the comparison in SQL | Leaks domain policy (code matching, active/expired distinction) into the adapter layer — violates Clean Architecture's "adapters implement, don't decide" rule; also blocks scenario 3.2/3.3's usecase-level rejection-reason tests. |
| Reuse `RegisterUser`'s account-creation `Account.create()` for the transition, mutating `is_verified` via a new public setter | A public setter reopens the invariant scenario 1.5 deliberately closed ("no code path can flip it to True at creation time") to arbitrary mutation from anywhere; narrower is safer. |

**Chosen**: new `VerifyAccount` usecase (own top-level entry point, does not call `RegisterUser` — usecases don't compose). Domain gains a narrow `Account.verify()` instance method (the only mutator of `_is_verified`, replacing the property-only invariant with a single controlled transition) and an `Account.reconstitute(...)` factory (closes the carryover.md gap: DB row → domain object round-trip that preserves the real `is_verified` value, distinct from `create()` which always starts `False`). Both repository ports gain one new read method each, scoped to exactly what this usecase needs — no generic `find_all`/CRUD surface.

## Model

- `backend/domain/src/auth/account.py`:
  - `Account.reconstitute(id, email, password_hash, created_at, is_verified) -> Account` — rebuilds from storage, unlike `create()` which always starts unverified.
  - `Account.verify() -> None` — sets `_is_verified = True`. No-op-safe: idempotent re-call sets True→True (scenario 3.4's replay case reuses this without a special branch).
- `backend/domain/src/auth/verification_code.py` — unchanged (already has `code`, `expires_at`, `consumed_at`, `reconstitute()` from scenario 2.1/2.5).
- `backend/usecase/src/auth/account_repository.py` — add `find_by_email(email: str) -> Optional[Account]`.
- `backend/usecase/src/auth/verification_code_repository.py` — add `find_active_by_account_id(account_id: UUID) -> Optional[VerificationCode]` (scoped to "active" = not yet consumed; expiry comparison happens in the usecase against the injected `Clock`, not in the query, so scenario 3.3's exact-boundary test stays usecase-testable with a `FakeClock`).
- New `backend/usecase/src/auth/verify_account.py`: `VerifyAccount` usecase.
  - Ports: `account_repository: AccountRepository`, `verification_code_repository: VerificationCodeRepository`, `clock: Clock`. Reuses the same `Clock` port `RegisterUser` already depends on — no new port type.
  - `execute(email: str, code: str) -> None`:
    1. `find_by_email(email)` — not found or already verified → domain-appropriate rejection (this scenario, 3.1, only needs the happy path; not-found/already-verified error codes are 3.5's scope, added there, not invented early).
    2. `find_active_by_account_id(account.id)` — no active code → rejection (3.2/3.3's scope).
    3. Compare `code` to the found code's `.code` as strings (never coerced to int, per `auth_verify.yaml`).
    4. On match: `account.verify()`, persist via `account_repository.save()` (same `save()` method already used for insert — becomes an upsert/update at the adapter layer, decided at `adapters-discovery` when the real SQL adapter is touched, not here).
- No new response DTO needed beyond what `auth_verify.yaml` already specifies (`{"is_verified": true}`) — deferred to `adapters-discovery`/`red-adapter rest`.

## Edge Cases (scoped to 3.1; later sub-scenarios own the rest, not duplicated here)

| Case | Owner scenario |
|------|----------------|
| Wrong code | 3.2 |
| Expired code, exact-boundary instant | 3.3 |
| Replay of an already-consumed code | 3.4 |
| Already-verified account | 3.5 |
| Concurrent verify requests, same account | 3.6 |

Scenario 3.1's `VerifyAccount.execute` implementation only needs to *not break* on these paths later — it doesn't need to fully handle them now. The design intentionally keeps `find_active_by_account_id` returning `Optional[VerificationCode]` (not raising) so 3.2/3.3 can extend the usecase's `None`-handling branch without a signature change.
