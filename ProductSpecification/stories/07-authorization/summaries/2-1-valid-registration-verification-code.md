## red-adapter db (2026-07-14)

**Quirk:** `VerificationCode` (domain entity) has no `created_at` field — only `id`, `account_id`, `code`, `expires_at`, `consumed_at`. The `verification_codes` table/model needs a `created_at` column (for consistency with every other table in this story), so `VerificationCodeModel.from_domain` takes an explicit `created_at` parameter that isn't sourced from the domain entity itself.
**Where:** `backend/domain/src/auth/verification_code.py`, `backend/adapters/db/src/model/auth/verification_code_model.py`.
**Implication:** Compare against `Account`, which *does* carry `created_at` on the domain entity. Whoever picks up `green-adapter db` for this scenario should decide whether to add `created_at` to the domain entity (consistent with `Account`) or keep it as an adapter-only concern — currently inconsistent between the two entities in the same story.

## Interrupted work unit (2026-07-14)

**Note:** Commit `9cc689b` ("test: red-adapter db scenario 2.1 verification code storage") landed as a behavior commit, but the `/test-review`, `/refactor`, `agent-review`, and `premortem` passes for it were interrupted mid-dispatch (session paused for `/clear`) and never completed. A quick manual read of the Statements assertions (`verification_code_storage_statements.py`) showed exact-tuple-equality checks already in place (code `"007123"` with leading zero, tz-aware `expires_at`, `consumed_at is None`) — no obviously loose assertions — but the formal review/refactor batch for this specific commit is still owed before the next work unit (`green-adapter db`) proceeds, per this project's "one commit, one refactor+review batch" convention.

## Owed review batch completed (2026-07-14)

**Ran the missing `/test-review` + `/refactor` + `agent-review` + `premortem` passes over `9cc689b` before starting `green-adapter db`.**
- `/test-review`: no changes needed — assertions already strict (confirms the earlier manual read).
- `/refactor`: no changes needed — red-phase scaffold, all files under the 200-line cap, mapping already lives on `VerificationCodeModel` not scattered in the repository.
- `agent-review` verdict: **CONCERNS**.
- `premortem` verdict: **CONCERNS**.

**Quirk: `VerificationCodeModel.to_domain()` drops `consumed_at`, and `VerificationCode.__init__` hardcodes `consumed_at=None` with no way to reconstruct a consumed code.**
**Where:** `backend/adapters/db/src/model/auth/verification_code_model.py` (`to_domain()`, ~line 34), `backend/domain/src/auth/verification_code.py` (`__init__`).
**Implication:** Both independent review passes flagged the same gap — a code fetched back from storage after being consumed will report `consumed_at is None` regardless of the actual DB value, since `to_domain()` never reads the column and the domain constructor has no parameter/setter for it. No test in `9cc689b` catches this (the round-trip test only exercises a never-consumed code and asserts against the raw model, not `to_domain()`). This must be closed before scenario 3.x (email verification, which needs to detect an already-consumed code) — needs either a domain `reconstitute()` factory taking `consumed_at`, or a constructor parameter, plus a repository test that saves → marks consumed → refetches → asserts `to_domain().consumed_at` is preserved. `green-adapter db` for scenario 2.1 itself only needs `save()`, so this can be scoped into `green-adapter db`'s test coverage now or explicitly deferred to a later scenario — decide before green-adapter db locks in `to_domain()`'s signature.
**From:** scenario 2.1 (valid-registration-verification-code), owed review batch.

Minor/non-blocking (premortem, REMOTE — no reachable code path yet): no `ondelete` on the `verification_codes.account_id` FK (no account-deletion feature exists to trigger it); no index/unique constraint on `account_id` (no lookup-by-account method exists yet to need it). Not follow-up-worthy until those features exist.

## test-coverage for green-adapter rest (2026-07-15)

**Ran the owed `/test-coverage --focus` pass over commit `9b1fdf3`** (RegisterResponseDto.from_domain built from full RegistrationResult; auth_router.register() passes full result; container.py wires real SqlAlchemyVerificationCodeRepository).

- `rest` module: `pytest --cov=adapters/rest/src adapters/rest/tests/` → 14 passed, 0 failed.
- Focused classes: `register_response_dto.py` and `auth_router.py` — both 100% line and branch coverage. No gaps, no dead code.
- `container.py` (application module DI wiring, also touched by the commit) has no unit-test target under this architecture (straight-line wiring, no branches) — exercised only via acceptance tests. Not a coverage gap.
- No red/green follow-up steps needed. Scenario 2.1 backend work is clean through `green-adapter rest`; `green-acceptance` remains the next step.
