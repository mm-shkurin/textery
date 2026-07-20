# Decision: Idempotent verify replay (3.4) and already-verified rejection (3.5)

**Date**: 2026-07-20 **Scenarios**: 3.4, 3.5 (story 7) **Status**: accepted

Backfill work unit (Phase C of `_project_audit/FRAMEWORK_BACKFILL_PLAN.md`). Written as
a real ADR because the sprint-1 trimmed cycle expired 2026-07-17 and because premortem on
commit `852281b` surfaced a genuine design fork, not a mechanical choice.

## Problem

`VerifyAccount.execute` (`backend/usecase/src/auth/verify_account.py`) has no
`account.is_verified` branch. Every call — including one against an account that is already
verified — runs the whole tail unconditionally:

```
account.verify()                                   # idempotent, fine
verification_code.consume(consumed_at=clock.now()) # OVERWRITES _consumed_at with a fresh time
await account_repository.save(account)
await verification_code_repository.save(verification_code)  # UPDATE ... consumed_at = <new>
await unit_of_work.commit()                        # a SECOND commit
```

Two scenarios expose this:

- **3.4** — re-submit the *same* code after the account is already verified. Spec
  (`api-specs/auth_verify.yaml` `200`): "Re-submitting the same already-consumed code again
  returns this same 200 (idempotent re-run … **not a duplicate state transition**)." Today
  the HTTP answer is correctly `200`, but internally `consumed_at` is rewritten to the
  replay time and a second transaction commits — the "no duplicate state transition" clause
  is **violated**, invisibly over HTTP (premortem CREDIBLE finding on `852281b`).
- **3.5** — verify against an already-verified account with *any* code. Spec (`409`):
  "Account already verified — verify against a verified account is rejected." Today a
  non-matching code on a verified account answers `400 INVALID_OR_EXPIRED_CODE` (the
  `not matches` branch), never `409 ALREADY_VERIFIED`.

3.4 ("same code") and 3.5 ("any code") overlap. They are reconciled by the submitted code:
the same code that verified the account → idempotent success; any *other* code → rejected.

## Decision

Insert one `is_verified` branch in `VerifyAccount.execute`, **after** the account and the
active code are fetched (both `None` cases still answer the generic `400`, unchanged — no
account-existence oracle introduced), and **before** the pending-path
`matches`/expiry/verify/consume/commit tail:

```
account = await account_repository.find_by_email(normalized_email)
if account is None: raise self._invalid_or_expired()          # 400, unchanged
verification_code = await verification_code_repository.find_active_by_account_id(account.id)
if verification_code is None: raise self._invalid_or_expired() # 400, unchanged

if account.is_verified:
    # 3.4 vs 3.5 fork. The account already transitioned; do NOT transition again.
    if verification_code.matches(code):
        return            # 3.4: idempotent 200, NO consume/save/commit -> consumed_at preserved
    raise self._already_verified()  # 3.5: 409 ALREADY_VERIFIED

# pending path (existing, unchanged):
if not verification_code.matches(code): raise self._invalid_or_expired()
if self.clock.now() >= verification_code.expires_at: raise self._invalid_or_expired()
account.verify(); verification_code.consume(...); save; save; commit
```

`_already_verified()` returns `ValidationException(error_code="ALREADY_VERIFIED", message=...)`.
The REST error-code→status map (`backend/adapters/rest/.../exception_handlers.py`,
`_ERROR_CODE_STATUS_MAP`) gains `ALREADY_VERIFIED -> 409` (same mechanism `EMAIL_ALREADY_REGISTERED -> 409`
already uses since scenario 2.2).

### Why early-return, not "rewrite but preserve consumed_at"

Both close the premortem finding. Early-return is chosen because:

- It touches **zero** persistence on the replay path — no second `save`, no second
  `commit()`, no rollback surface. "No duplicate state transition" becomes true *by
  construction*, not by carefully preserving a field on a write that still happens.
- It removes the latent double-side-effect vector directly: when `verify()` later gains a
  real side effect (welcome email, credit grant), the replay path never reaches it because
  it returns before the tail. The "preserve consumed_at" variant would still re-enter the
  tail and would need a separate guard for every future side effect.
- `consumed_at` is preserved for free (we never call `consume` again).

## Guarantee the tests must pin (red-usecase — assert NEGATIVELY)

A guard that only *counts* calls goes green on the current buggy behavior (`save`==2,
`consume`==2). red-usecase must assert the invariant negatively against the current
unconditional tail so it genuinely goes RED:

- **3.4** (verified account, matching code): after the second `execute`,
  `verification_code_repository.save` and `account_repository.save` call-counts stay at
  **1**, `unit_of_work.commit` call-count stays at **1**, and `consumed_at` equals the
  **first** consume time (not the replay clock). The Fake clock must advance between the two
  `execute` calls so an overwrite would be detectable.
- **3.5** (verified account, non-matching code): `execute` raises
  `ValidationException(error_code="ALREADY_VERIFIED")`; neither repository's `save` is
  called; no commit.

Both are genuine RED today: 3.4's second call currently re-saves/re-commits with a moving
`consumed_at`; 3.5 currently raises `INVALID_OR_EXPIRED_CODE`, not `ALREADY_VERIFIED`.

## Accepted, documented trade-off (oracle)

`409 ALREADY_VERIFIED` reveals that the email exists *and* is verified, whereas the unknown
account and wrong-code paths stay a generic `400`. This is an account-status oracle — but it
is **spec-mandated** (`auth_verify.yaml` `409`), and it is the same class of already-accepted
disclosure as this story's existing timing-oracle note in `_invalid_or_expired`'s docstring.
Not closed here; named so it is not rediscovered as a bug.

## Scope

Covers 3.4 and 3.5. 3.6 (concurrency: exactly one transition, the other observes the
verified state) builds on this branch — the loser of the race re-reads a now-verified
account and takes the 3.4 idempotent-success path — and is designed in its own step.
