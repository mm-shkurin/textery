import pytest

from statements.register_statements import RegisterStatements


@pytest.mark.skip(reason="RED: RegisterUser.execute does not compare password to confirm_password")
class TestRegisterUsecasePasswordConfirmationMismatch:
    """Scenario 1.4: Reject password/confirm_password mismatch.

    Given a registration request whose confirm_password differs from password
    When the client submits the request
    Then the response is a validation error
    And no account is created
    """

    async def test_should_reject_mismatched_confirm_password(
        self, register_statements: RegisterStatements
    ):
        await register_statements.attempt_registering_with_mismatched_confirmation(
            "Different1!Pass"
        )
        register_statements.assert_password_mismatch_error_raised()
