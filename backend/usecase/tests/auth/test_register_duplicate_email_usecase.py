import pytest

from statements.register_statements import RegisterStatements


class TestRegisterUsecaseDuplicateEmail:
    """Scenario 2.2: Duplicate email is rejected, verified or pending.

    Given a registration request whose email is already registered
    When the AccountRepository rejects the save due to the unique email constraint
    Then RegisterUser.execute raises a validation error with error_code
    EMAIL_ALREADY_REGISTERED
    And no verification code is issued
    """

    async def test_should_reject_registration_when_email_already_registered(
        self, register_statements: RegisterStatements
    ):
        await register_statements.attempt_registering_when_email_already_registered()
        register_statements.assert_email_already_registered_error_raised()
