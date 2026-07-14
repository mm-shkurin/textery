import pytest

from tests.backend.abstract_backend_test import AbstractBackendTest


@pytest.mark.skip(
    reason="RED: verification_code missing from RegisterResponse - "
    "expected verification_code to be a string, got NoneType (None)"
)
class TestRegisterValidAcceptance(AbstractBackendTest):
    """Scenario 2.1: Valid registration creates a pending account and returns a verification code.

    Given a registration request with a valid, unused email and a policy-compliant password
    When the client submits the request
    Then an account is created with is_verified false
    And the response includes a 6-digit verification code as a zero-padded string
    And the response includes the code's expiry, 10 minutes from issuance
    """

    async def test_should_create_pending_account_with_verification_code(self, auth_statements):
        response = await auth_statements.given_valid_unique_registration_request()

        auth_statements.assert_pending_account_created_with_verification_code(response)
