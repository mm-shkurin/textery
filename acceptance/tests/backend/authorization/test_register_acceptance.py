import pytest

from tests.backend.abstract_backend_test import AbstractBackendTest


@pytest.mark.skip(reason="RED: POST /api/v1/auth/register not implemented (404 Not Found)")
class TestRegisterAcceptance(AbstractBackendTest):
    """Scenario 1.1: Reject malformed email.

    Given a registration request with a malformed email address
    When the client submits the request
    Then the response is a validation error
    And no account is created
    """

    async def test_should_reject_malformed_email(self, auth_statements):
        response = await auth_statements.given_registration_request_with_malformed_email()

        auth_statements.assert_validation_error(response, auth_statements.EXPECTED_MALFORMED_EMAIL_ERROR)
        auth_statements.assert_no_account_created(response)
