from statements.resend_verified_statements import ResendVerifiedStatements


class TestResendVerifiedUsecase:
    """Scenario 4.5: a resend against an already-verified account is rejected with
    ALREADY_VERIFIED (409 taxonomy from 3.5), and no new code is issued.

    The gate reads the POST-lock account (lock_for_update's return) and sits BEFORE
    the cooldown check, so a verified account never leaks a cooldown answer and a
    verify that commits inside the lock window is still caught.
    """

    async def test_should_reject_a_verified_account_before_the_cooldown_check(
        self, resend_verified_statements: ResendVerifiedStatements
    ):
        await resend_verified_statements.given_a_verified_account_with_a_code_still_inside_cooldown()
        await resend_verified_statements.resend()
        resend_verified_statements.assert_rejected_as_already_verified_with_no_new_code()

    async def test_should_gate_on_the_post_lock_verified_account(
        self, resend_verified_statements: ResendVerifiedStatements
    ):
        await resend_verified_statements.given_an_unverified_account_eligible_for_resend()
        await resend_verified_statements.resend_with_the_lock_returning_a_verified_account()
        resend_verified_statements.assert_rejected_as_already_verified_with_no_new_code()
