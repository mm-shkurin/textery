import pytest

from statements.account_concurrency_statements import AccountConcurrencyStatements


class TestConcurrentTransitionToVerified:
    """Two racing sessions call transition_to_verified on the SAME pending
    account row. Exactly one returns True (it flipped is_verified false->true,
    rowcount==1); the other returns False (rowcount==0, already verified) and
    raises no exception. The final persisted row is is_verified=true, so the
    loser resolves to the verified state -- the idempotent-observation outcome
    scenario 3.6 requires."""

    @pytest.mark.skip(
        reason="RED 2026-07-20: transition_to_verified not implemented; green-adapter db 3.6 adds the conditional UPDATE"
    )
    async def test_should_transition_exactly_once_under_concurrent_verify(
        self, account_concurrency_statements: AccountConcurrencyStatements
    ):
        await account_concurrency_statements.insert_pending_account()
        await account_concurrency_statements.race_two_transitions()
        await account_concurrency_statements.fetch_final_verified_state()
        account_concurrency_statements.assert_exactly_one_transition()
        account_concurrency_statements.assert_final_row_verified()
