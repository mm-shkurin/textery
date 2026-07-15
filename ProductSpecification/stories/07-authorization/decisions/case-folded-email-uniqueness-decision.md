# Decision: Case-folded email uniqueness at Scenario 2.3

**Date**: 2026-07-15 **Scenarios**: 2.3

Scenario 2.2 rejects exact-match duplicate emails via a DB-level `UNIQUE` constraint on
`accounts.email` (`uq_accounts_email`, plain column, case-sensitive). Scenario 2.3 requires
`"User@Example.ru"` to be rejected as a duplicate of an existing `"user@example.ru"`
account. Premortem on the 2.3 red-acceptance commit flagged two credible incidents if this
is done naively:

| Rejected | Why |
|----------|-----|
| App-level check-then-insert (`SELECT ... WHERE lower(email) = lower(:email)` before insert) | Reopens the exact TOCTOU race scenario 2.2 deliberately closed by moving uniqueness enforcement into the DB constraint. Two concurrent case-varied registrations for the same email would both pass the app-level check and both insert successfully. |
| A new DB-level functional/expression index (`UNIQUE (lower(email))`) on top of the existing raw-column constraint | Works, but leaves the raw column un-normalized — a future login/lookup usecase (5.x/6.x) doing an exact-match query on `accounts.email` would still miss users who typed a different case at login than at registration ("registered as `User@X.ru`, can't log in as `user@x.ru`" — the second premortem incident). Two constraints (raw + functional) to keep in sync is also more moving parts than one. |

**Chosen**: normalize (lowercase) the email at the domain boundary — `Email.value` returns
the lowercased form — so every usecase that constructs an `Email` (register today; login,
verify, resend in 3.x/4.x/5.x) works with the canonical form uniformly. The existing plain
`uq_accounts_email` constraint from scenario 2.2 is sufficient once storage is canonical:
comparing `"user@example.ru"` and `"USER@Example.ru"` after normalization collides on the
same stored value, so the same `IntegrityError` → `ConflictException` → `EMAIL_ALREADY_REGISTERED`
path from 2.2 handles it with **no new migration**.

## Model

- `backend/domain/src/auth/email.py`: `Email.__init__` normalizes `raw_value` to lowercase
  before storing it (`self._value = raw_value.lower()`), after the existing format/length
  validation runs on the raw input (so validation error messages still reflect what the
  user typed). `Email.value` always returns the canonical lowercased form.
- No change to `backend/usecase/src/auth/register_user.py` — it already does
  `Email(email)` for validation and passes the raw `email` string to `Account.create`;
  this needs to change to pass the *normalized* value (`Email(email).value`) so the
  persisted `Account.email` is canonical, not the raw request casing.
- No change to `backend/adapters/db/migrations/` — the scenario-2.2 `uq_accounts_email`
  constraint already enforces uniqueness on the (now-canonical) stored value.

## Edge Cases

| Case | Behavior |
|------|----------|
| Concurrent case-varied registrations for the same email | Both normalize to the same stored value before insert; the DB `UNIQUE` constraint (not an app-level check) rejects the second commit, preserving the race-safety property from scenario 2.2. |
| Future login (5.x/6.x) | Looks up by `Email(input).value` (canonical/lowercased), so a user who registered as `User@X.ru` can log in as `user@x.ru` — normalization is symmetric across register and login since both go through the same `Email` value object. |
| Display of the registered email back to the user | `RegisterResponseDto` already returns `account.email` (the persisted, now-canonical value) — the user sees their email in lowercase after registration, not the exact casing they typed. Accepted: no scenario in this story requires preserving original casing for display. |
| Non-ASCII case folding (e.g. Turkish dotless-i, locale-dependent `.lower()`) | Out of scope for this scenario — Python's `str.lower()` is used, not locale-aware folding. Named as a known gap by premortem, not fixed here; the story's domain doesn't currently require i18n-aware case folding. |
| Existing scenario 1.1–2.2 fixtures | All use lowercase-only email fixtures (verified: no uppercase local-part/domain fixtures exist in `backend/usecase/tests/` or `backend/adapters/*/tests/`), so normalization is behavior-neutral for every already-committed test. |
