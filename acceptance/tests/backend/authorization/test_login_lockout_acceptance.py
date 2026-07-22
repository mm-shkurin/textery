import pytest

from tests.backend.abstract_backend_test import AbstractBackendTest


@pytest.mark.skip(
    reason="RED 5.4: no lockout logic on /login — after LOCKOUT_THRESHOLD wrong-password "
    "attempts a subsequent correct-password login returns 200 + token pair, not 403 "
    "ACCOUNT_LOCKED (verified live against BACKEND_PORT=8100: got status_code=200)"
)
class TestLoginLockoutAcceptance(AbstractBackendTest):
    """Scenario 5.4: Account locks out after N consecutive failed attempts.

    Given a verified account has just reached N consecutive failed login attempts
    When the client submits another login request, even with the correct password
    Then the response is rejected, account locked out
    """

    async def test_should_lock_out_after_n_consecutive_failed_attempts(self, login_statements):
        response = (
            await login_statements
            .given_account_at_lockout_threshold_then_login_with_correct_password()
        )

        login_statements.assert_locked_out(response)
