import pytest

from tests.backend.abstract_backend_test import AbstractBackendTest


@pytest.mark.skip(
    reason="RED: POST /api/v1/auth/verify is routed but not wired to a usecase, returns "
    "500 (get_verify_account_usecase raises NotImplementedError; the composition-root "
    "override in main.py is deliberately withheld until scenario 3.2 lands the "
    "wrong-code rejection branch -- see progress-backend.md scenario 3.1 green-acceptance)"
)
class TestVerifyValidCodeAcceptance(AbstractBackendTest):
    """Scenario 3.1: Correct code activates the account.

    Given a pending account with an active, unexpired verification code
    When the client submits that code for that email
    Then the account becomes verified
    """

    async def test_should_activate_account_with_correct_code(self, verify_statements):
        response = await verify_statements.given_correct_code_submitted_for_pending_account()

        verify_statements.assert_account_verified(response)
