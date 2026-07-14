from tests.backend.abstract_backend_test import AbstractBackendTest


class TestRegisterLengthAcceptance(AbstractBackendTest):
    """Scenario 1.2: Reject email exceeding the length limit.

    Given a registration request whose email is 256 characters
    When the client submits the request
    Then the response is a validation error
    And no account is created
    """

    async def test_should_reject_email_exceeding_length_limit(self, auth_statements):
        response = await auth_statements.given_registration_request_with_overlong_email()

        auth_statements.assert_validation_error(response, auth_statements.EXPECTED_OVERLONG_EMAIL_ERROR)
        auth_statements.assert_no_account_created(response)
