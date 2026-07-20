# Decision: Exactly-one-transition for concurrent verify (scenario 3.6)

**Date**: 2026-07-20 **Scenario**: 3.6 (story 7) **Status**: accepted

Backfill work unit (Phase C of `_project_audit/FRAMEWORK_BACKFILL_PLAN.md`). ADR because
this is a real concurrency-control decision with a load-bearing constraint the premortem
on `0ae5e4f` surfaced.

## Problem

`VerifyAccount.execute` does a lock-free **check-then-act**: it reads
`account.is_verified` (False), then later `_apply_verification` calls
`account.verify()` → `account_repository.save()` → `verification_code.consume()` →
`verification_code_repository.save()` → `unit_of_work.commit()`. Each `/verify` request
runs in its **own session/transaction** (`auth_wiring.create_verify_account` builds a fresh
`session_factory()` per request).

Two concurrent verifies with the same correct code on a pending account therefore both read
`is_verified=False`, both take the pending tail, and both perform the transition:
`account_storage.save()` does an unconditional `existing.is_verified = account.is_verified`
(get-then-set, last-writer-wins), and `verification_code_storage.save()` unconditionally
overwrites `consumed_at`. Both commit, both answer `200`. The HTTP outcome is correct (both
200, matching scenario 3.6's "the other observes the verified state, not an error"), but the
spec's **"exactly one request transitions the account"** is violated: two UPDATEs mutate the
row, `consumed_at` is written twice. Not HTTP-observable — both answers are identical 200s —
so `test_verify_concurrent_acceptance.py` (already green) can only pin the both-200 half; the
exactly-one-transition half must be pinned at the DB adapter.

Harmless today (the double-write is field-level idempotent, and nothing hangs off the verify
path — no welcome email, token, or credit). The guard must land **before** any such
side-effect is attached, or the unguarded race becomes a double-effect incident.

## Decision

Introduce a **conditional single-row transition** in the account storage adapter, exposed as
a new port method so the winner/loser outcome is observable and testable:

```
# usecase port (AccountRepository)
async def transition_to_verified(self, account_id: UUID) -> bool: ...
    # True  -> this call flipped the row (is_verified false -> true): the transition
    # False -> the row was already verified (a concurrent racer, or a prior verify) won
```

Adapter implementation (`SqlAlchemyAccountRepository`), mirroring the compare-and-set idiom
already in `generation_storage.py` but with **inverted zero-row semantics**:

```
result = await self._session.execute(
    update(AccountModel)
    .where(AccountModel.id == account_id, AccountModel.is_verified.is_(False))
    .values(is_verified=True)
)
return result.rowcount == 1
```

`rowcount == 1` → we transitioned it. `rowcount == 0` → already verified; in
`generation_storage.py:91` a zero-row UPDATE is an *error* (NotFoundException/ConflictException),
but **here zero-row is success**: the account is verified regardless of who did it, which is
exactly the idempotent-observation outcome scenario 3.6 wants. `transition_to_verified` never
raises for the zero-row case.

The verification-code consume is likewise made conditional so only the winner stamps it:

```
update(VerificationCodeModel)
  .where(VerificationCodeModel.id == code_id, VerificationCodeModel.consumed_at.is_(None))
  .values(consumed_at=now)
```

### Usecase change (small, deliberate)

`_apply_verification` changes from `account.verify(); await account_repository.save(account)`
to `won = await account_repository.transition_to_verified(account.id)`. Whether `won` is True
or False, the method returns success (the loser resolves to idempotent success — no
exception, no special-casing needed at the call site because the DB already reflects the
verified state). This is a minimal deviation from "usecase untouched": the usecase must call
the atomic method instead of the read-modify-write `verify()`+`save()` pair, but it gains no
new branch — both outcomes are success. The `_apply_verification` rollback/try-except stays.

`account.verify()` (the in-memory setter) is retained for the non-concurrent domain invariant
and for any caller that reconstitutes+returns an Account, but the **persisted** transition now
goes through `transition_to_verified`, not the unconditional `save()` update branch.

## The load-bearing test constraint (premortem on 0ae5e4f)

`red-adapter db` MUST assert **both**:
1. Of two racing sessions calling `transition_to_verified` on the same pending row, **exactly
   one returns True** (`rowcount == 1`); the other returns **False** (`rowcount == 0`).
2. The losing session (`False`) **raises nothing** and the final row is verified.

Assertion (2) is what keeps the DB fix compatible with the both-200
`test_verify_concurrent_acceptance.py` pin already committed: if green naively copied
`generation_storage`'s zero-row→raise, the loser's 0-row would become
`VerificationFailedException` via `_apply_verification`'s broad except and silently break the
acceptance test. The exactly-one-transition fix and the both-200 idempotency pin are in
tension; assertion (2) reconciles them.

## Alternatives rejected

- **`SELECT … FOR UPDATE` row lock then read-modify-write.** Serializes the two requests and
  works, but holds a write lock across the usecase's remaining awaits (code consume, commit),
  widening the lock window; the compare-and-set is lock-free and single-statement.
- **Optimistic version column on `accounts`.** Needs a migration and a version-mismatch
  decode path; the boolean `is_verified false→true` is already a natural one-way CAS guard,
  no new column required.
- **Keep the guard entirely inside `save()` (no new port method).** Then the winner/loser
  outcome is invisible to the usecase and to the red-adapter db test, so "exactly one
  transition" cannot be asserted at the layer where it is provable. Rejected for testability.

## Scope

No migration (uses the existing `accounts.is_verified` / `verification_codes.consumed_at`
columns). Steps: `red-adapter db` (two-racing-session concurrency test per the constraint
above) → `green-adapter db` (`transition_to_verified` + conditional consume + usecase call
site) → `adapters-discovery` (confirm no rest/response-shape change; the port gains a method,
the Fake gains it too). `green-acceptance` already landed (both-200 pin). A `red-usecase`/
`green-usecase` pair may be needed for the small `_apply_verification` call-site change and
the Fake's `transition_to_verified` — decide at `adapters-discovery`.
