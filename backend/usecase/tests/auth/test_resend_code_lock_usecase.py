from statements.resend_code_lock_statements import ResendCodeLockStatements


class TestResendCodeLockUsecase:
    """Scenario 4.4: ResendCode.execute wires the account row lock into the
    critical section so the db serialization (SELECT ... FOR UPDATE proven by the
    db-adapter race test) is actually exercised in production.

    Two call-site contracts the Fakes CAN pin (single-threaded, no real race):
    the lock precedes the cooldown read, and the POST-lock account is threaded
    forward (premortem CREDIBLE #2 on 7aa72f3) so 4.5's is_verified gate reads the
    fresh row rather than the stale pre-lock one.
    """

    async def test_should_acquire_the_row_lock_once_before_the_cooldown_read(
        self, resend_code_lock_statements: ResendCodeLockStatements
    ):
        await resend_code_lock_statements.given_a_pending_account_eligible_for_resend()
        await resend_code_lock_statements.resend_with_the_call_order_recorded()
        resend_code_lock_statements.assert_lock_acquired_once_before_the_cooldown_read()

    async def test_should_bind_the_issued_code_to_the_post_lock_account(
        self, resend_code_lock_statements: ResendCodeLockStatements
    ):
        await resend_code_lock_statements.given_a_pending_account_eligible_for_resend()
        await resend_code_lock_statements.resend_with_the_lock_returning_a_different_account()
        resend_code_lock_statements.assert_issued_code_is_bound_to_the_locked_account()
