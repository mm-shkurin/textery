## red-adapter db (2026-07-14)

**Quirk:** `VerificationCode` (domain entity) has no `created_at` field — only `id`, `account_id`, `code`, `expires_at`, `consumed_at`. The `verification_codes` table/model needs a `created_at` column (for consistency with every other table in this story), so `VerificationCodeModel.from_domain` takes an explicit `created_at` parameter that isn't sourced from the domain entity itself.
**Where:** `backend/domain/src/auth/verification_code.py`, `backend/adapters/db/src/model/auth/verification_code_model.py`.
**Implication:** Compare against `Account`, which *does* carry `created_at` on the domain entity. Whoever picks up `green-adapter db` for this scenario should decide whether to add `created_at` to the domain entity (consistent with `Account`) or keep it as an adapter-only concern — currently inconsistent between the two entities in the same story.

## Interrupted work unit (2026-07-14)

**Note:** Commit `9cc689b` ("test: red-adapter db scenario 2.1 verification code storage") landed as a behavior commit, but the `/test-review`, `/refactor`, `agent-review`, and `premortem` passes for it were interrupted mid-dispatch (session paused for `/clear`) and never completed. A quick manual read of the Statements assertions (`verification_code_storage_statements.py`) showed exact-tuple-equality checks already in place (code `"007123"` with leading zero, tz-aware `expires_at`, `consumed_at is None`) — no obviously loose assertions — but the formal review/refactor batch for this specific commit is still owed before the next work unit (`green-adapter db`) proceeds, per this project's "one commit, one refactor+review batch" convention.
