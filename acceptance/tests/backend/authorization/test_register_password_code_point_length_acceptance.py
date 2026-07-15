from tests.backend.abstract_backend_test import AbstractBackendTest


class TestRegisterPasswordCodePointLengthAcceptance(AbstractBackendTest):
    """Scenario 2.4d: Password length limit is measured in code points, not bytes.

    Given a registration password built from multibyte Unicode characters
    totalling exactly 128 code points
    When the client submits the request
    Then the request is accepted

    Given the same password extended to 129 code points
    When the client submits the request
    Then the response is a validation error
    """

    async def test_should_accept_multibyte_password_at_128_code_points(self, auth_statements):
        response = (
            await auth_statements.given_registration_request_with_multibyte_password_at_length_limit()
        )

        auth_statements.assert_created_pending_account(response)

    async def test_should_reject_multibyte_password_at_129_code_points(self, auth_statements):
        response = (
            await auth_statements.given_registration_request_with_multibyte_password_over_length_limit()
        )

        auth_statements.assert_validation_error(response, auth_statements.EXPECTED_WEAK_PASSWORD_ERROR)
        auth_statements.assert_no_account_created(response)
