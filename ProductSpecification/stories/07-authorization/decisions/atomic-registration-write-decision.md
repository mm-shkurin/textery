# Decision: UnitOfWork port for atomic Account+VerificationCode write

**Date**: 2026-07-15 **Scenarios**: 2.5

`AccountRepository.save()` and `VerificationCodeRepository.save()` each call `session.commit()` independently — a crash/error between the two calls leaves an orphan pending account with no verification code (accepted-tracked gap since scenario 2.1, per `verification-code-design-decision.md`). Scenario 2.5 requires both writes succeed or fail together.

| Rejected | Why |
|----------|-----|
| Retrofit commit/rollback logic directly into `RegisterUser.execute` against the raw `AsyncSession` | Usecase layer must not depend on framework code (`AsyncSession` is SQLAlchemy) — violates Clean Architecture's inward dependency rule. |
| Let each repository keep committing, catch failures and manually delete the orphan row | Not atomic — a crash between insert and delete still leaves the orphan; doesn't close the actual race. |

**Chosen**: new `UnitOfWork` port (usecase layer) with async `commit()`/`rollback()`, backed by `SqlAlchemyUnitOfWork` wrapping the shared `AsyncSession`. Both repositories stop committing themselves; `RegisterUser.execute` calls `UnitOfWork.commit()` once after both saves succeed, and is the sole caller of `rollback()` on any failure (repositories never rollback themselves, closing a double-rollback risk raised by hazard scan group 4).

## Model

- `backend/usecase/src/shared/unit_of_work.py`: `UnitOfWork` port — `commit() -> None`, `rollback() -> None`.
- `backend/adapters/db/src/session/sql_alchemy_unit_of_work.py`: `SqlAlchemyUnitOfWork(session)` adapter.
- `SqlAlchemyAccountRepository.save()`: `session.add()` + `await session.flush()` only (still surfaces `IntegrityError`→`ConflictException` early, before verification-code generation, preserving scenario 2.2's ordering) — no commit, no rollback.
- `SqlAlchemyVerificationCodeRepository.save()`: `session.add()` only — no flush, no commit.
- `RegisterUser.execute`: gains a `UnitOfWork` port dependency; calls `unit_of_work.commit()` once after both saves succeed; on any exception from either save or from `commit()`, calls `unit_of_work.rollback()` then re-raises (generic mapped exception for final-commit failure, message excludes raw driver/SQL detail).
- `container.py` `create_register_user()`: builds one `SqlAlchemyUnitOfWork(session)` shared with both repositories.

## Edge Cases

| Case | Behavior |
|------|----------|
| Account flush succeeds, verification-code write/final commit fails | `UnitOfWork.rollback()` discards both — zero rows in either table, no orphan account. |
| Duplicate email (flush-time `IntegrityError`) | Unchanged from scenario 2.2 — `ConflictException`→`EMAIL_ALREADY_REGISTERED`, no verification code generated. |
| Two concurrent first-registrations, same brand-new email | Unique-constraint check still fires at `flush()` (DB enforces on INSERT, not only COMMIT) — scenario 2.4a's race guard re-verified against this code path, not just assumed. |
| Failure exception message | Never includes raw `IntegrityError`/SQL text — sentinel-value test asserts absence from the raised exception's message. |
