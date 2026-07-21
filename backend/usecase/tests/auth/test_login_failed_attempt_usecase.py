import pytest

from statements.login_failed_attempt_statements import LoginFailedAttemptStatements


class TestLoginFailedAttemptCounter:
    """Scenario 5.3: a wrong-password login on a found account is counted.

    Given a registered account
    When a login is attempted with the wrong password
    Then the failed-attempt counter is incremented and committed before the
         generic INVALID_CREDENTIALS is raised -- and unknown-email or
         correct-but-unverified attempts are NOT counted.
    """

    async def test_should_increment_then_commit_then_reject_on_a_wrong_password(
        self, login_failed_attempt_statements: LoginFailedAttemptStatements
    ):
        await login_failed_attempt_statements.given_verified_account()
        await login_failed_attempt_statements.login_with_a_wrong_password()
        login_failed_attempt_statements.assert_counted_the_failed_attempt_then_rejected()

    async def test_should_reject_generically_and_rollback_when_the_commit_fails(
        self, login_failed_attempt_statements: LoginFailedAttemptStatements
    ):
        await login_failed_attempt_statements.given_verified_account()
        await login_failed_attempt_statements.login_with_a_wrong_password_while_the_commit_fails()
        login_failed_attempt_statements.assert_rejected_as_invalid_credentials_and_rolled_back()

    async def test_should_not_count_an_unknown_email(
        self, login_failed_attempt_statements: LoginFailedAttemptStatements
    ):
        await login_failed_attempt_statements.given_verified_account()
        await login_failed_attempt_statements.login_with_an_unknown_email()
        login_failed_attempt_statements.assert_did_not_count_any_attempt()
        login_failed_attempt_statements.assert_rejected_as_invalid_credentials()

    async def test_should_not_count_a_correct_password_on_an_unverified_account(
        self, login_failed_attempt_statements: LoginFailedAttemptStatements
    ):
        await login_failed_attempt_statements.given_pending_account()
        await login_failed_attempt_statements.login_with_the_correct_password()
        login_failed_attempt_statements.assert_did_not_count_any_attempt()
        login_failed_attempt_statements.assert_rejected_as_unverified()
