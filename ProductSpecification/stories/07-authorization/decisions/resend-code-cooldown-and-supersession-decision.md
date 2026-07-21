# Decision: Resend cooldown, supersession, and atomicity (scenario 4.x)

**Date**: 2026-07-21 **Scenario**: 4.1 (story 7), forward-scoping 4.2–4.5 **Status**: accepted

Backfill work unit. ADR because resend introduces a real anti-abuse control
(cooldown) plus a concurrency guard (4.4) — the same class of decision as the
verify single-transition ADR (`concurrent-verify-single-transition-decision.md`),
and three credible premortem findings on the red-acceptance commit (`e37cfe0`)
turn on choices made here.

## Problem

`POST /api/v1/auth/resend-code` must issue a fresh verification code for a
pending account and stop the previous code from verifying, subject to a 60-second
cooldown. The `verification_codes` table today has `id, account_id, code,
expires_at, consumed_at, created_at` — no per-account cooldown state and no
ordering key other than `created_at`. `VerifyAccount` finds the code to check via
`find_active_by_account_id` = **most recent by `created_at desc, limit 1`**, and
deliberately does not filter consumed/expired rows (that is what makes the 3.4
idempotent-replay path work — see `carryover.md`).

Four things must be decided: (1) what starts the cooldown clock, (2) how the old
code stops verifying, (3) how "exactly one code issued" survives concurrency and a
mid-write failure, (4) the error taxonomy.

## Decision

### 1. Cooldown is measured from the most-recent code's `created_at` (registration counts)

The 60-second window runs from the `created_at` of the account's newest code,
**including the code registration issued**. A resend is allowed only when
`now - max(created_at) >= 60s`. This is exactly what scenario 4.1's Gherkin states
("resend, **more than 60 seconds after the previous issuance**") and what 4.2
requires ("issued 30 seconds ago → rejected").

Rejected alternative: **cooldown from the last _resend_ only** (registration does
not start it), which would let a just-registered account resend immediately. That
is the abuse vector premortem Incident 1 named — register once, then blast the
email provider with unlimited immediate resends. We keep the secure model.

**Consequence for the committed 4.1 acceptance test (premortem Incident 1).** The
red-acceptance test resends **immediately** after registration and asserts `200` +
a fresh code. Under this cooldown model that immediate resend is inside the window
and must be **rejected**, not succeed. The acceptance layer has no server-clock
lever (established for 3.6/2.4b/3.4), so 4.1's cooldown-gated *success* and
supersession are proven at the **usecase layer with a FakeClock** (advance the
clock past 60s, resend, assert new code + old code no longer verifies). At
`green-acceptance` the committed HTTP test is reworked to what is black-box
observable **without** crossing the cooldown — either the cooldown *rejection*
(which needs no wait) or marked `[S]` deferred with the real proof at the usecase
layer. We do **not** weaken the cooldown to make the immediate-resend assertion
pass. `red-usecase` owns the FakeClock proof.

### 2. Supersession is insert-only; "active" = most recent; the cooldown makes ordering deterministic

Resend **inserts** a new code. The old code stops verifying because
`find_active_by_account_id` returns only the newest row — the old code is never the
one `VerifyAccount` checks, so it cannot transition the account. No row is deleted
or mutated on the resend path.

Premortem Incident 2 warned this "shadow, not invalidate" scheme is nondeterministic
when two codes share `created_at` (a FakeClock returning a fixed instant would give
both the same timestamp, and `order_by(created_at desc).limit(1)` has no tiebreak).
**Resolved by decision 1:** a legitimately issued resend is always ≥60s after the
previous code, so two codes for the same account can never share a `created_at`.
The cooldown *is* the ordering guarantee — no secondary sort key and no migration
are needed. Tests must therefore advance the FakeClock past the cooldown before a
resend (they must anyway, to get past the cooldown gate), which also gives the two
codes distinct timestamps. A test that issues two codes at the same instant is not
exercising a legal resend and is out of contract.

### 3. Atomicity (4.3) and concurrency (4.4): a conditional single-writer guard

Insert-only makes "never zero codes" trivial: the old row persists until the new
insert commits, so there is no window with zero active codes (4.3 — "the new-code
write would fail after the old is invalidated" cannot happen because nothing is
invalidated first). If the insert fails, the old code is still the active one.

For 4.4 (two concurrent resends must not both issue), the cooldown check and the
insert must be **one atomic conditional write**, mirroring the verify
compare-and-set (3.6): issue a new code only if no code for the account has
`created_at > now - 60s`. Exactly one concurrent racer's guard passes; the other
sees the just-inserted row (or loses the write race) and is rejected as
cooldown-active. The concrete mechanism (a conditional `INSERT ... WHERE NOT
EXISTS (...)` / a per-account guard row) and its two-racing-session db test are
scoped to **4.3/4.4's own red-adapter db / green-adapter db steps** — this ADR
fixes the approach, not the SQL. 4.1 alone needs only the sequential cooldown +
insert; the atomic guard lands with 4.4.

### 4. Error taxonomy

- **Resend within cooldown** → new error code `RESEND_COOLDOWN_ACTIVE` → **HTTP
  429** (Too Many Requests — the semantically correct status for a rate/lockout
  control; added to `_ERROR_CODE_STATUS_MAP` the same per-code way as
  `EMAIL_ALREADY_REGISTERED`→409). Message generic ("A verification code was
  recently sent. Please wait before requesting another.").
- **Resend against an already-verified account** (4.5) → reuse `ALREADY_VERIFIED`
  → **409**, exactly as the verify path (3.5).
- **Resend for an unknown email** → the same generic `INVALID_OR_EXPIRED_CODE`-class
  client-safe rejection the verify path uses for unknown accounts, so resend does
  not become an account-existence oracle (consistent with
  `verify-account-design-decision.md`). Final code/shape pinned at red-usecase.
- **The superseded old code at `/verify`** stays the generic **`INVALID_OR_EXPIRED_CODE`
  / 400** (premortem Incident 3). A superseded code is not literally expired, but
  giving supersession its own code would turn the verify status line into a
  code-state oracle and split the generic-rejection taxonomy the story has held
  since 1.1. **Deliberate choice, recorded here:** verify does not distinguish
  superseded from invalid/expired. If a future UX/telemetry need justifies a
  distinct `SUPERSEDED_CODE`, it is a conscious taxonomy change, not a silent one;
  the committed 4.1 acceptance test's exact-body pin on `INVALID_OR_EXPIRED_CODE`
  encodes this decision.

## Scope

Steps for 4.1: `design` (this) → `red-usecase` (FakeClock: cooldown gate rejects an
in-window resend; a past-cooldown resend issues a new code and the old code no
longer verifies — the supersession + cooldown proof the acceptance layer cannot
give) → `green-usecase` (`ResendCode` usecase — new top-level usecase, NOT a call
from `VerifyAccount`; reuses `AccountRepository`/`VerificationCodeRepository`/`Clock`;
generates a code the same CSPRNG way as registration) → `adapters-discovery` (new
`/api/v1/auth/resend-code` route + `resend-code` DI wiring + `RESEND_COOLDOWN_ACTIVE`
→429 map entry; a `find_most_recent_by_account_id`/cooldown read on the code repo if
the port lacks it) → `green-acceptance` (rework the committed HTTP test per decision
1). No migration. The atomic single-writer guard and its db concurrency test are
4.3/4.4's scope, not 4.1's.

New usecase, not a `VerifyAccount` method: resend is a distinct top-level operation
(register-like issuance under a gate), so per the usecase-interaction rule it is its
own entry point, sharing only domain-level code-generation logic with registration.
