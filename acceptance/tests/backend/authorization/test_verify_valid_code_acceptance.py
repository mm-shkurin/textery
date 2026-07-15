import pytest

from tests.backend.abstract_backend_test import AbstractBackendTest


@pytest.mark.skip(reason="RED: POST /api/v1/auth/verify does not exist, returns 404 Not Found")
class TestVerifyValidCodeAcceptance(AbstractBackendTest):
    """Scenario 3.1: Correct code activates the account.

    Given a pending account with an active, unexpired verification code
    When the client submits that code for that email
    Then the account becomes verified
    """

    async def test_should_activate_account_with_correct_code(self, verify_statements):
        response = await verify_statements.given_correct_code_submitted_for_pending_account()

        verify_statements.assert_account_verified(response)
