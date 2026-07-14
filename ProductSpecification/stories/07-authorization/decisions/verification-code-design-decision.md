# Decision: Verification code as a separate entity/table, schema forward-safe now

**Date**: 2026-07-14 **Scenarios**: 2.1

Scenario 2.1 requires a real 6-digit verification code + 10-minute expiry returned on registration — no verification-code concept exists anywhere in the codebase yet.

| Rejected | Why |
|----------|-----|
| Flat columns on `Account` (`verification_code`, `code_expires_at`) | Story's own Core Requirements explicitly call for a separate "Verification-code value object/entity ... associated account" — flat columns can't hold future resend history or a `consumed_at` state cleanly. |
| `random.randint` for code generation | Hazard-scan group 7: non-cryptographic PRNG for a security-relevant secret (guessability via the future verify endpoint). Trivial fix, no tradeoff — use `secrets.randbelow`. |
| Enforce atomic Account+VerificationCode write now | Story spec names this exact requirement as its own scenario, **2.5** ("Registration writes the account and the verification code atomically"). Hazard-scan group 2 confirmed a real orphan-account window exists in the interim — accepted and tracked here (see Edge Cases), not silently absorbed, per the scan's own recommendation. Retrofitting a unit-of-work commit strategy now would touch already-shipped 1.5 repository code for a guard that scenario 2.5 owns. |
| Add `accounts.email` unique constraint now | Story spec names this as **scenario 2.4a** (concurrent registration, same email) and **2.2** (duplicate rejection semantics). Hazard-scan group 3 confirmed a real concurrency race exists in the interim — accepted and tracked, not silently absorbed. |

**Chosen**: new `VerificationCode` domain entity + `verification_codes` table, schema includes a `consumed_at` column now (unused by 2.1, but additive-now avoids a later ALTER against dirty data once 3.x/4.x need it). Code generated via `secrets.randbelow`, stored/compared as a fixed-length string end-to-end.

## Model

- `backend/domain/src/auth/verification_code.py`: `VerificationCode.create(id, account_id, code, expires_at)` — `code: str` (always `f"{secrets.randbelow(1_000_000):06d}"`), `consumed_at: Optional[datetime] = None` internal, no public setter (mirrors `Account`'s pinning pattern).
- `backend/usecase/src/auth/verification_code_repository.py`: `VerificationCodeRepository` port — `save(code) -> None`.
- `backend/adapters/db/src/model/auth/verification_code_model.py` + `verification_code_storage.py`: mirrors `account_model.py`/`account_storage.py`.
- `backend/adapters/db/migrations/versions/*_verification_codes_table.py`: `id` (UUID pk), `account_id` (UUID, FK to `accounts.id`, not null), `code` (String(6), not null — fixed-length string column, never numeric), `expires_at` (DateTime with timezone, not null), `consumed_at` (DateTime with timezone, nullable), `created_at` (DateTime with timezone, not null).
- `RegisterUser.execute` gains `VerificationCodeRepository` as an injected port; generates the code via `secrets.randbelow`, issues `expires_at = clock.now() + timedelta(minutes=10)`, persists both Account and VerificationCode (two separate `save()` calls — see Edge Cases), returns both to the REST layer.
- `RegisterResponseDto` gains `verification_code: str`, `code_expires_at: datetime`.

## Edge Cases

| Case | Behavior |
|------|----------|
| Process crashes between `Account.save()` and `VerificationCode.save()` | **Accepted, tracked gap** — orphan pending account with no code, until Scenario 2.5 wraps both writes in one transaction. Not guarded by any test in 2.1. |
| Two concurrent first-registrations for the same brand-new email | **Accepted, tracked gap** — no DB unique constraint on `accounts.email` yet; both could succeed, creating two accounts. Scenario 2.4a owns the concurrency guard, 2.2 owns the rejection semantics. |
| Code with a leading zero (e.g. `"007123"`) | Stored/compared as a string end-to-end — `code` column is `String(6)`, never numeric; no `int()` coercion anywhere in the read/write/compare path. |
| Repeated registration attempts accumulate `verification_codes` rows | **Accepted, tracked gap** — no cap/invalidation in 2.1; Scenario 4.x (resend) owns invalidating old codes, "single active code per account" as a whole is a cross-scenario invariant, not fully enforced until then. |
