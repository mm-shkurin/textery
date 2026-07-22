# Decision: Account lockout after N consecutive failed attempts (scenario 5.4)

**Date**: 2026-07-22 **Scenario**: 5.4 (story 7), forward-scoping 5.5/5.5a/5.6 **Status**: accepted

Design step for 5.4. ADR because 5.4 introduces new authentication semantics (a
lockout gate that rejects even correct credentials), a new error-code in the 403
taxonomy, a counter-reset write on the previously commit-free login happy path,
and it sets the seam 5.5 (cooldown auto-expiry) builds on. Same class of decision
as `atomic-failed-attempt-counter-decision.md` (5.3), which this continues.

> **Autonomous-loop note:** produced without live user approval (session running
> under `/loop`). Defaults below are chosen to match the provisional acceptance
> constant and the interview's stated intent; the threshold **N** and the
> `ACCOUNT_LOCKED` error-code string are the two values a human should sanity-check.

## Problem

5.3 gave every wrong-password login an atomic `failed_attempt_count += 1`. 5.4 must
turn that counter into a gate: once an account reaches **N consecutive** failures,
further logins are rejected **"locked out"** — even one carrying the correct
password (acceptance §5.4: "even with the correct password → rejected, account
locked out"). The response is **HTTP 403 with a distinct error_code**, separate
from the not-verified 403, so the client can show the account-locked screen with a
retry countdown (UI §5.4). "Consecutive" means a successful login must **reset** the
counter to 0 (notes.md:10).

## Decision

### 1. Threshold N = 5, lockout is a derived predicate (no new column)

`LOCKOUT_THRESHOLD = 5`. An account is locked iff `failed_attempt_count >= 5`.
No new column: the 5.3 counter already carries the state. 5 balances brute-force
resistance against locking a legitimate user out on a few fat-fingered retries, and
matches the provisional constant the red-acceptance test already encodes.

Locking is **derived**, not stored — there is no `is_locked` / `locked_at` boolean
to keep in sync with the counter. This keeps 5.4 minimal and correct-by-construction
(the count is the single source of truth).

### 2. Expose `failed_attempt_count` on the domain so LoginUser can read it

5.3's increment was a pure DB-side `UPDATE` that never read the domain value. 5.4
must **read** the count to decide lockout, so:

- `Account.reconstitute(...)` gains a `failed_attempt_count: int` parameter and a
  read-only `failed_attempt_count` property (mirrors how `is_verified` was added).
- `AccountModel.to_domain()` passes the row's `failed_attempt_count` through
  (today it drops it — the same reconstruction-gap class as the old `is_verified`
  bug; a round-trip test must pin it: write count=5, assert `to_domain().failed_attempt_count == 5`).
- `Account.create(...)` is unchanged — a new account has count 0 by construction.

### 3. Lockout gate runs BEFORE password verification (but AFTER the null check)

`LoginUser.execute` order becomes:

```
account = find_by_email(...)
if account is None:            raise INVALID_CREDENTIALS      # 401, unchanged (5.2)
if account.failed_attempt_count >= LOCKOUT_THRESHOLD:
                              raise ACCOUNT_LOCKED             # 403, NEW — before password
if not verify(password):      record_failed_attempt; raise INVALID_CREDENTIALS  # 401 (5.3)
if not account.is_verified:   raise UNVERIFIED                # 403, unchanged (5.1)
reset_failed_attempts; commit; return issue_pair(...)         # success — reset then issue
```

The gate is **after** the `account is None` check on purpose: an unknown email has
no row and no counter, so it still takes the generic 401 path — the lockout branch
can only be reached for an account that demonstrably exists. This does mean a
**locked** account answers 403 to a *wrong* password where an unlocked one answers
401, so 403-vs-401 confirms existence *once an account is already locked*. Accepted:
locking an account requires N failures against a real row, so the attacker who sees
the 403 already caused it and already knows the account exists — no new information
(same reasoning that gates UNVERIFIED behind a correct password). The generic-401
existence protection for **un-attacked** emails is untouched.

### 4. Reset-on-success must COMMIT on the happy path (premortem carry from 5.3 bf7c7cc)

On a successful login the counter resets to 0 via a new atomic
`AccountRepository.reset_failed_attempts(account_id)` = single DB-side
`UPDATE accounts SET failed_attempt_count = 0 WHERE id = :id` (mirrors 5.3's
increment; no read-modify-write, no lost-update race). **This reset lands on
LoginUser's happy path, which since 5.3 has a UoW wired but never calls `commit()`.**
A naive `reset(); return issue_pair()` without an explicit `commit()` issues the
UPDATE on the session and then discards it on `session.close()` — the exact silent
no-op class 5.3 closed for the failure path. So the success branch must
`reset_failed_attempts → commit` before issuing tokens.

**Red-usecase guard (plant before wiring the reset):** a test asserting that on a
successful login the UoW's `commit()` is invoked (e.g. `FakeUnitOfWork.commit_call_count == 1`)
AND `reset_failed_attempts` was called — so a missing commit goes RED, not silently green.

Wrap the reset+commit like `_record_failed_attempt`: a commit failure on the reset
must not turn a valid login into a 5xx — but here failing closed differs. A reset
that fails to persist leaves the count where it was; the login still succeeds
(tokens issued) but the stale count persists. That is acceptable (worst case: the
user's next failure trips lockout one attempt early); do NOT block token issuance on
the reset commit. Swallow + log, same shape.

### 5. Error-code taxonomy: `ACCOUNT_LOCKED` → 403

New `ValidationException(error_code="ACCOUNT_LOCKED", message=...)`. Add
`"ACCOUNT_LOCKED": 403` to `_ERROR_CODE_STATUS_MAP` (rest). Distinct from
`"UNVERIFIED": 403` — both are 403 but carry different error_codes so the client
routes to the account-locked screen vs the verify screen. Message is client-safe and
generic (e.g. "This account is temporarily locked due to repeated failed logins.").

## Rejected alternatives

- **Stored `is_locked` boolean / `locked_at` column now.** Rejected for 5.4 — a
  second field to keep consistent with the counter, and 5.4 needs no timestamp. See
  the 5.5 seam below.
- **Lockout check after password verification.** Fails the scenario: the correct
  password would authenticate before the gate fires. Rejected.
- **Reset via ORM load-then-save.** Reintroduces the 5.3 lost-update race and needs
  no read here. Rejected — the atomic `SET = 0` UPDATE is simpler and safe.
- **A different N per environment / configurable N.** Out of scope; a constant is
  enough for 5.4. Configurability can come later without a schema change.

## 5.5 / 5.5a / 5.6 seams

- **5.5 (cooldown auto-expiry) needs a timestamp** the derived predicate does not
  carry: "locked for a cooldown window" requires knowing *when* the Nth failure
  happened. 5.5 will add a `last_failed_attempt_at` (or `locked_at`) timestamp,
  set on the increment, and change the lockout predicate to
  `count >= N AND now - last_failed_attempt_at < cooldown`. 5.4 deliberately does
  not add it — the pure count gate is the correct minimum for "locks out after N".
- **5.5a (exact expiry instant)** will pin the boundary comparison (`<` vs `<=`) on
  that timestamp — do not pre-decide it here.
- **5.6 (lockout read fails closed):** a DB error while reading the count must DENY
  the login (no token). Separate scenario; the read is `find_by_email`, so 5.6 wraps
  that failure into a denial rather than a 5xx.

## Scope / steps

`design` (this) → `red-usecase` (lockout gate rejects correct password at count≥N
with ACCOUNT_LOCKED; reset-on-success calls reset+commit — plant the commit guard;
expose `failed_attempt_count` on the domain) → `green-usecase` → `adapters-discovery`
(**db:** add `red/green-adapter db` for `reset_failed_attempts` atomic UPDATE + a
`to_domain` round-trip pinning `failed_attempt_count`; **rest:** map `ACCOUNT_LOCKED`
→ 403 — a 1-row `_ERROR_CODE_STATUS_MAP` add, likely its own `red/green-adapter rest`;
**wiring:** [S], `create_login_user` already passes a real UoW since 5.3) →
`green-acceptance` (un-skip `test_login_lockout_acceptance`, confirm **1 passed / 0
skipped** against a **freshly built** image — not the stale RED :8100 image — and add
the premortem below-threshold guard). ADR — done.

**Premortem #1 below-threshold guard (fold into green-acceptance):** the current
acceptance test drives exactly N wrong attempts then asserts locked — proving only
`production_N ≤ 5`. Add the complementary assertion: `N-1` wrong attempts followed by
a correct-password login **succeeds (200)** and resets the counter, pinning that
lockout fires *at* N, not before.
