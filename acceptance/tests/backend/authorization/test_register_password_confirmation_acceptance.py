from tests.backend.abstract_backend_test import AbstractBackendTest


class TestRegisterPasswordConfirmationAcceptance(AbstractBackendTest):
    """Scenario 1.4: Reject password/confirm_password mismatch.

    Given a registration request whose password and confirm_password differ
    When the client submits the request
    Then the response is a validation error
    And no account is created
    """

    async def test_should_reject_password_confirmation_mismatch(self, auth_statements):
        response = await auth_statements.given_registration_request_with_mismatched_confirm_password()

        auth_statements.assert_validation_error(response, auth_statements.EXPECTED_PASSWORD_MISMATCH_ERROR)
        auth_statements.assert_no_account_created(response)
