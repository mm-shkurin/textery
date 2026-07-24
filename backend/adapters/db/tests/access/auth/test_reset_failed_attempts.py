from statements.reset_failed_attempts_statements import (
    ResetFailedAttemptsStatements,
)


class TestResetFailedAttemptsPersistsAtomically:
    """Seed a verified account with failed_attempt_count = 4 and a bystander with
    count = 2, call reset_failed_attempts(account_id) + commit, then re-read on a
    FRESH AsyncSession. The target must read back 0; the bystander must be
    UNCHANGED (== 2), pinning the `WHERE id = :account_id` -- a missing WHERE
    would zero everyone.

    Predicted RED: SqlAlchemyAccountRepository has no reset_failed_attempts method
    yet (only the Protocol + Fake do), so reset_target_failed_attempts raises
    AttributeError."""

    async def test_should_reset_only_target_account_durably(
        self,
        reset_failed_attempts_statements: ResetFailedAttemptsStatements,
    ):
        await reset_failed_attempts_statements.seed_accounts_with_failed_attempts()
        await reset_failed_attempts_statements.reset_target_failed_attempts()
        await reset_failed_attempts_statements.reread_counts_on_new_session()
        reset_failed_attempts_statements.assert_target_reset_to_zero()
        reset_failed_attempts_statements.assert_bystander_unchanged()
