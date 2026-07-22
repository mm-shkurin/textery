from statements.login_lockout_statements import LoginLockoutStatements


class TestLoginLockout:
    """Scenario 5.4: an account locks out after N consecutive failed attempts.

    Given a verified account whose failed-attempt counter is at the lockout
    threshold, When a login is attempted -- even with the CORRECT password --
    Then it is rejected with a distinct 403 ACCOUNT_LOCKED, no token is issued,
    and the password is never verified (the gate precedes credential checking).
    And a successful login one below the threshold authenticates, resets the
    counter to zero, and commits that reset.
    """

    async def test_should_reject_even_a_correct_password_when_the_account_is_locked(
        self, login_lockout_statements: LoginLockoutStatements
    ):
        await login_lockout_statements.given_verified_account_at_the_lockout_threshold()
        await login_lockout_statements.login_with_the_correct_password()
        login_lockout_statements.assert_rejected_as_locked_without_verifying_or_issuing()

    async def test_should_authenticate_and_reset_the_counter_below_the_threshold(
        self, login_lockout_statements: LoginLockoutStatements
    ):
        await login_lockout_statements.given_verified_account_one_below_the_lockout_threshold()
        await login_lockout_statements.login_with_the_correct_password()
        login_lockout_statements.assert_authenticated_and_reset_the_counter()

    async def test_should_commit_the_reset_on_a_successful_login(
        self, login_lockout_statements: LoginLockoutStatements
    ):
        await login_lockout_statements.given_verified_account_one_below_the_lockout_threshold()
        await login_lockout_statements.login_with_the_correct_password()
        login_lockout_statements.assert_committed_the_reset()
