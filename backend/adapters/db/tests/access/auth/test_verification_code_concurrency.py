import pytest

from statements.verification_code_concurrency_statements import (
    VerificationCodeConcurrencyStatements,
)


@pytest.mark.skip(
    reason="RED: SqlAlchemyVerificationCodeRepository.transition_to_consumed not yet implemented"
)
class TestConcurrentTransitionToConsumed:
    """Two racing sessions call transition_to_consumed on the SAME unconsumed
    verification code row. Exactly one returns True (it stamped consumed_at,
    rowcount==1); the other returns False (rowcount==0, already consumed) and
    raises no exception. The final persisted row has consumed_at set, so the
    loser resolves to the consumed state -- the idempotent-observation outcome
    scenario 3.6's second (code-consume) guard requires."""

    async def test_should_consume_exactly_once_under_concurrent_verify(
        self, verification_code_concurrency_statements: VerificationCodeConcurrencyStatements
    ):
        await verification_code_concurrency_statements.insert_pending_account_with_unconsumed_code()
        await verification_code_concurrency_statements.race_two_consumes()
        await verification_code_concurrency_statements.fetch_final_consumed_state()
        verification_code_concurrency_statements.assert_exactly_one_consume()
        verification_code_concurrency_statements.assert_final_row_consumed()
