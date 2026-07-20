import pytest

from statements.verify_account_idempotency_statements import (
    VerifyAccountIdempotencyStatements,
)


class TestVerifyAccountIdempotentReplay:
    """Scenario 3.4: re-submitting an already-consumed code causes NO duplicate
    state transition.

    Given an account already verified once with its issued code
    When the same email+code is submitted again (clock advanced)
    Then the replay succeeds silently AND neither repository is written a second
    time, no second commit fires, and the code's first consume time is preserved.
    """

    @pytest.mark.skip(
        reason="RED 2026-07-20: VerifyAccount.execute re-runs the consume/save/commit "
        "tail on replay (no is_verified early-return yet); green-usecase 3.4 lands the guard"
    )
    async def test_should_not_re_transition_on_replay_of_consumed_code(
        self, verify_account_idempotency_statements: VerifyAccountIdempotencyStatements
    ):
        statements = verify_account_idempotency_statements
        await statements.given_account_already_verified_once_with_its_code()
        await statements.resubmit_the_same_already_consumed_code()
        statements.assert_replay_was_a_no_op()

    @pytest.mark.skip(
        reason="RED 2026-07-20: expiry check currently precedes the is_verified/matches "
        "idempotent-return; green-usecase 3.4/3.5 reorders per ADR"
    )
    async def test_should_stay_idempotent_when_matching_code_replayed_after_expiry(
        self, verify_account_idempotency_statements: VerifyAccountIdempotencyStatements
    ):
        statements = verify_account_idempotency_statements
        await statements.given_account_already_verified_once_with_its_code()
        await statements.resubmit_the_same_code_after_it_expired()
        statements.assert_replay_was_a_no_op()
