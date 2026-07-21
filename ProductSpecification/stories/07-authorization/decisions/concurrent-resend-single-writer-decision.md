# Decision: Exactly-one-winner for concurrent resend (scenario 4.4)

**Date**: 2026-07-21 **Scenario**: 4.4 (story 7) **Status**: accepted

Backfill work unit. ADR because this closes the resend concurrency-bypass that
was a **tracked deferral** since 4.1 (green-adapter rest gap A, adapters-discovery
decision B), and because two premortem-CREDIBLE gaps carried from 4.3 (`f688a7e`)
must be resolved here. Same class of decision as
`concurrent-verify-single-transition-decision.md` (3.6).

## Problem

`ResendCode.execute` is a lock-free **read-check-then-insert**: `find_active_by_account_id`
(newest code) → `_enforce_cooldown` (is `now - newest.created_at >= 60s`?) →
`_issue_new_code` (INSERT a new code) → commit. Each `/resend-code` request runs in
its own session/transaction, and the backend runs multiple instances.

Two concurrent resends on an **eligible** account (newest code already >60s old) both
read the same stale `newest`, both pass the cooldown check, and both INSERT a new code
— two codes issued, two emails, cooldown bypassed. There is no DB atomicity on the
gate and no unique constraint to collide on (insert-only supersession deliberately
keeps multiple un-consumed rows per account).

Two further gaps this exposes (premortem on `f688a7e`):
1. **Tied `created_at` → non-deterministic winner.** `find_active_by_account_id` is
   `ORDER BY created_at DESC LIMIT 1` with no secondary tiebreak, and `created_at` is
   `clock.now()`, not a DB default. Two same-instant inserts get equal `created_at` →
   arbitrary row order → the resend *response* code (from the winning insert) can
   diverge from what `find_active` later returns, so the emailed code never verifies.
2. **Never-zero is unpinned at the db layer** — no test proves a rolled-back second
   insert leaves the prior committed row still returned by `find_active`.

## Decision

**Serialize resends per account with a row lock, keeping the cooldown-from-newest-code
model.** No migration.

`ResendCode.execute` acquires a `SELECT … FOR UPDATE` lock on the account row **before**
the cooldown read, in the same transaction as the insert+commit:

```
# new port method on AccountRepository, implemented in SqlAlchemyAccountRepository
async def lock_for_update(self, account_id: UUID) -> Account | None:
    result = await self._session.execute(
        select(AccountModel).where(AccountModel.id == account_id).with_for_update()
    )
    model = result.scalar_one_or_none()
    return model.to_domain() if model else None
```

Flow: `find_by_email` → `lock_for_update(account.id)` → `find_active_by_account_id`
(cooldown read, now under the lock) → if eligible `_issue_new_code` → commit (releases
the lock).

The two racers contend on the **accounts** row lock. The winner holds it across the
cooldown read + insert + commit; the loser blocks until the winner commits, then
acquires the lock, re-reads the newest code (now the winner's fresh code, <60s old),
fails the cooldown, and answers `RESEND_COOLDOWN_ACTIVE` / 429. **Exactly one succeeds.**

### Why this also closes gaps 1 and 2

- **Tie dissolved.** Because resends are serialized, at most one code is inserted per
  cooldown window — two codes can never share a `created_at`. The response code is the
  only new code, so it is exactly what `find_active` returns; no divergence. As
  **defense-in-depth** (a tie from some future non-resend path, or clock coarseness),
  `find_active_by_account_id`'s query also gains a deterministic secondary sort:
  `ORDER BY created_at DESC, id DESC` — a tie then still returns one stable row.
- **Never-zero.** Insert-only is unchanged: the old row is never mutated/deleted, so a
  rolled-back insert leaves the prior committed code as the active one. `red-adapter db`
  adds the missing db test (insert A + commit, drive a failing second insert / rollback,
  assert `find_active` still returns A, never None).

## The load-bearing test constraint

`red-adapter db` MUST use a **real two-racing-session** concurrency test (mirror
`account_concurrency_statements.py` / `verification_code_concurrency_statements.py` from
3.6 — own `session_factory`, two independent `AsyncSession`s raced via `asyncio.gather`,
TRUNCATE-teardown fixture). Seed an **eligible** account (a code with `created_at` >60s
in the past), race two resend operations, and assert: (1) **exactly one** issues a new
code (`saved_codes` gains exactly one row) and the other is cooldown-rejected; (2) the
final active code is the winner's, returned deterministically; (3) **never zero** — an
active code is always present. Plus the tied-`created_at` determinism test and the
rolled-back-insert never-zero test above.

## Alternatives rejected

- **Conditional `INSERT … WHERE NOT EXISTS (recent code)`.** Under READ COMMITTED the
  `NOT EXISTS` subquery reads a snapshot and the two inserts don't conflict (no unique
  constraint), so both can still insert. Not atomic without a lock.
- **Partial unique index "one un-consumed code per account".** Breaks insert-only
  supersession — the old code stays un-consumed, so the resend insert would be rejected
  outright. Wrong model.
- **CAS on a new `accounts.last_resend_at` column** (mirror 3.6's `transition_to_verified`).
  A clean atomic single-writer, but needs a **migration**, shifts the cooldown source
  from the newest code's `created_at` to an account column, and forces registration to
  initialize it. `FOR UPDATE` achieves the same exactly-one guarantee with no migration
  and no model shift; resend is a low-frequency operation so the short lock window (3.6's
  reason to avoid `FOR UPDATE` for the hot verify path) is acceptable here.

## Scope

No migration. Steps: `design` (this) → `red-adapter db` (two-racing-session
exactly-one-winner + never-zero + tied-`created_at` determinism) → `green-adapter db`
(`lock_for_update` + the `, id DESC` tiebreak in `find_active_by_account_id`) →
`red-usecase` / `green-usecase` (wire `lock_for_update` into `ResendCode.execute` before
the cooldown read; add the method to the `AccountRepository` port + Fake) →
`adapters-discovery` → `green-acceptance` `[S]` (not HTTP-observable, per `[S]`
red-acceptance). The lock must live in the same UnitOfWork transaction as the insert —
verify the resend wiring (`auth_wiring.create_resend_code`) shares one session across
repo + UoW (it does, mirroring `create_verify_account`).
