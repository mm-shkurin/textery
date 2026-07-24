from statements.verify_account_base import VerifyAccountStatementsBase


class VerifyAccountAtomicTransitionStatements(VerifyAccountStatementsBase):
    """Scenario 3.6: the verify path drives the atomic single-row transitions.

    The exactly-one-winner property is a commit-scoped concurrency guarantee and
    is pinned at the db adapter (`test_account_concurrency.py` /
    `test_verification_code_concurrency.py`), NOT here -- the Fakes model no
    rollback race. What this layer must pin is the load-bearing wiring
    (premortem gap 1): the production `_apply_verification` must actually CALL
    `account_repository.transition_to_verified` and
    `verification_code_repository.transition_to_consumed`. Without this pin, the
    db-adapter atomic methods stay dead code and a "green suite" would not mean a
    race-safe production path -- a regression back to the lock-free
    `verify()`+`save()` / `consume()`+`save()` pair would go unnoticed.

    The atomic call is reached only AFTER `find_active_by_account_id` has returned
    a real code (premortem gap 3): the pending tail runs strictly after the
    None-checks in `execute`, so a False-for-nonexistent transition can never be
    mistaken for idempotent success without a prior row-exists confirmation. The
    happy-path arrangement here inherently satisfies that ordering.

    Identity-map note (agent-review b): the real adapter's bulk UPDATE bypasses the
    ORM identity map, but `execute` does no later same-txn read of
    `is_verified`/`consumed_at` after `_apply_verification` (it returns None), so
    there is no stale-read hazard to model at the Fake layer.
    """

    async def verify_with_the_issued_code(self) -> None:
        await self._execute_verify(self.account_email, self.account_code)

    def assert_verify_drove_the_atomic_transitions(self) -> None:
        assert self.thrown_exception is None, (
            f"expected the happy-path verify to succeed, got "
            f"{type(self.thrown_exception).__name__}: {self.thrown_exception}"
        )
        account_id = self.account_repository.saved_accounts[0].id
        assert self.account_repository.transition_to_verified_calls == [account_id], (
            f"expected the verify path to call transition_to_verified exactly once "
            f"with the account's id {account_id}, got "
            f"{self.account_repository.transition_to_verified_calls}"
        )
        code_id = self.verification_code_repository.saved_codes[0].id
        assert self.verification_code_repository.transition_to_consumed_calls == [
            (code_id, self.FIXED_CLOCK_NOW)
        ], (
            f"expected the verify path to call transition_to_consumed exactly once "
            f"with (code id {code_id}, clock now {self.FIXED_CLOCK_NOW}), got "
            f"{self.verification_code_repository.transition_to_consumed_calls}"
        )
