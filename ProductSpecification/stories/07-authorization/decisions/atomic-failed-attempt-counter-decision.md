# Decision: Atomic failed-attempt counter (scenario 5.3)

**Date**: 2026-07-21 **Scenario**: 5.3 (story 7), forward-scoping 5.4 **Status**: accepted

Backfill work unit. ADR because 5.3 introduces new persistent state (a counter
column + migration) plus a concurrency-control decision (atomic increment), and
because 5.4 (lockout-after-N) builds directly on the shape chosen here. Same class
of decision as `concurrent-verify-single-transition-decision.md` (3.6) and
`concurrent-resend-single-writer-decision.md` (4.4).

## Problem

A wrong-password login must be counted so 5.4 can lock an account out after N
consecutive failures. `LoginUser.execute` today is **read-only**: `find_by_email`
→ verify password → verify `is_verified` → issue tokens; on a wrong password it
raises a generic `INVALID_CREDENTIALS` (5.2). There is no counter and no write.

The backend runs multiple instances. Counting via **ORM load-then-save**
(`account.failed_attempt_count += 1; save()`) loses increments under concurrency:
two simultaneous wrong-password logins both read count=0, both write 1 → the
counter reflects **one** failure, not two (5.3's exact failure mode: "not one lost
to a race"). The DSL note is explicit: *"DB column updated via atomic increment
(`UPDATE ... SET count = count + 1`), never ORM load-then-save."*

## Decision

### 1. New column `failed_attempt_count` on `accounts`

`failed_attempt_count INTEGER NOT NULL DEFAULT 0`. Additive, safe for existing
rows (they default to 0). New alembic migration chained off the current head
(`f6a7b8c9d0e1`, accounts_email_unique) — verify the head with `alembic heads` at
green-adapter db time.

### 2. Atomic increment via a single DB-side UPDATE (never ORM load-then-save)

New `AccountRepository` port method + `SqlAlchemyAccountRepository` impl:

```
async def increment_failed_attempts(self, account_id: UUID) -> None:
    await self._session.execute(
        update(AccountModel)
        .where(AccountModel.id == account_id)
        .values(failed_attempt_count=AccountModel.failed_attempt_count + 1)
    )
```

`.values(failed_attempt_count=AccountModel.failed_attempt_count + 1)` emits SQL
`SET failed_attempt_count = failed_attempt_count + 1` — the database does the
arithmetic in one statement, so two concurrent calls serialize on the row and both
land (final = 2). No read-modify-write in application code, no lost update. This is
inherently atomic **without** a `FOR UPDATE` lock (unlike 4.4, where the guard had
to prevent a second *insert*; here the single UPDATE's row lock is the whole
mechanism). No commit inside — the caller owns the transaction (codebase pattern).

### 3. `LoginUser` increments-then-commits on the wrong-password branch

`LoginUser` gains a `UnitOfWork` (it currently has none — login was read-only). On
the **found-account + wrong-password** branch only:

```
if not self.password_hasher.verify(...):
    await self.account_repository.increment_failed_attempts(account.id)
    await self.unit_of_work.commit()   # persist the failure BEFORE raising
    raise self._invalid_credentials()
```

- Increment only when `find_by_email` returned an account AND the password is wrong
  — an unknown email (`account is None`) has no row to increment, and a *correct*
  password that is merely `UNVERIFIED` is not a failed attempt (the password was
  right; that branch stays unchanged, no increment).
- **Commit before raise** so the counter persists even though the login fails.
- The generic `INVALID_CREDENTIALS` response contract (5.2) is unchanged — the
  increment is a silent side effect, not visible in the 401 body (5.3 red-acceptance
  is `[S]` precisely because it is not HTTP-observable).

`create_login_user` (`auth_wiring.py`) must share ONE session across the account
repo and the UoW (same coupling the resend guard needed — see
`concurrent-resend-single-writer-decision.md`) so the increment and its commit are
one transaction. Pin it with a wiring same-session test (mirror
`test_resend_wiring.py`) at adapters-discovery.

## The load-bearing test constraint

`red-adapter db` MUST use a **real two-racing-session** test (mirror
`account_concurrency_statements.py`): seed a verified account with
`failed_attempt_count = 0`, race two `increment_failed_attempts` calls on two
independent `AsyncSession`s via `asyncio.gather`, and assert the final persisted
count is **exactly 2**. Falsification: an ORM load-then-save implementation yields
**1** (both read 0, both write 1), so the test genuinely fails against the
non-atomic version and passes only against DB-side `SET count = count + 1`.

## Alternatives rejected

- **ORM load-then-save** (`account.failed_attempt_count += 1; save()`). The exact
  race 5.3 forbids — lost updates under concurrency. Rejected by the scenario.
- **A separate `login_attempts` table** (one row per attempt, count via `COUNT(*)`).
  Handles concurrency (inserts don't conflict) but is heavier: unbounded growth,
  a reset story for 5.4's "consecutive" semantics, and a join on every login.
  The single counter column with an atomic increment is simpler and matches the
  DSL's stated shape. Rejected for weight.
- **`SELECT ... FOR UPDATE` then increment** (like 4.4). Works but is unnecessary:
  a single `UPDATE ... SET c = c + 1` already serializes on the row lock and is
  one statement — no explicit lock or second read needed. Rejected as heavier
  than required.

## Scope

Migration (new column). Steps: `design` (this) → `red-adapter db`
(two-racing-session, final count == 2) → `green-adapter db`
(`increment_failed_attempts` + migration + the column on `AccountModel`) →
`red-usecase` / `green-usecase` (LoginUser increments-then-commits on wrong
password; add the port method to the Fake + a UoW to LoginUser) →
`adapters-discovery` (rest: [S] — no response change, 401 unchanged; wiring:
same-session pin for `create_login_user`) → `green-acceptance` `[S]` (not
HTTP-observable). **5.4 seam:** 5.4 reads this counter to lock out at N — expose
`failed_attempt_count` on the domain `Account` + `AccountModel.to_domain` when 5.4
needs to read it (5.3's increment is a pure UPDATE and does not read the domain
value, so the domain field can wait for 5.4 unless a reset/read is wanted sooner).
Likely ADR — done.
