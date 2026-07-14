import pytest

from tests.backend.abstract_backend_test import AbstractBackendTest


@pytest.mark.skip(reason="TDD Red Phase - Not yet implemented")
class TestRegisterPasswordPolicyAcceptance(AbstractBackendTest):
    """Scenario 1.3: Reject password failing the policy.

    Given a registration request whose password is only 7 characters
    When the client submits the request
    Then the response is a validation error

    Given a registration request whose password has no digit
    When the client submits the request
    Then the response is a validation error

    Given a registration request whose password has no uppercase letter
    When the client submits the request
    Then the response is a validation error

    Given a registration request whose password has no special character
    When the client submits the request
    Then the response is a validation error

    Given a registration request whose password has no lowercase letter
    When the client submits the request
    Then the response is a validation error

    Given a registration request whose password exceeds 128 characters
    When the client submits the request
    Then the response is a validation error
    """

    async def test_should_reject_password_too_short(self, auth_statements):
        response = await auth_statements.given_registration_request_with_short_password()

        auth_statements.assert_validation_error(response, auth_statements.EXPECTED_WEAK_PASSWORD_ERROR)

    async def test_should_reject_password_missing_digit(self, auth_statements):
        response = await auth_statements.given_registration_request_with_password_missing_digit()

        auth_statements.assert_validation_error(response, auth_statements.EXPECTED_WEAK_PASSWORD_ERROR)

    async def test_should_reject_password_missing_uppercase(self, auth_statements):
        response = await auth_statements.given_registration_request_with_password_missing_uppercase()

        auth_statements.assert_validation_error(response, auth_statements.EXPECTED_WEAK_PASSWORD_ERROR)

    async def test_should_reject_password_missing_special_character(self, auth_statements):
        response = (
            await auth_statements.given_registration_request_with_password_missing_special_character()
        )

        auth_statements.assert_validation_error(response, auth_statements.EXPECTED_WEAK_PASSWORD_ERROR)

    async def test_should_reject_password_missing_lowercase(self, auth_statements):
        response = await auth_statements.given_registration_request_with_password_missing_lowercase()

        auth_statements.assert_validation_error(response, auth_statements.EXPECTED_WEAK_PASSWORD_ERROR)

    async def test_should_reject_password_exceeding_length_limit(self, auth_statements):
        response = await auth_statements.given_registration_request_with_overlong_password()

        auth_statements.assert_validation_error(response, auth_statements.EXPECTED_WEAK_PASSWORD_ERROR)
