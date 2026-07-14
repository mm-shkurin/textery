import pytest

from statements.register_statements import RegisterStatements


@pytest.mark.skip(reason="RED: verification code generation not implemented")
class TestRegisterUsecaseIssuesVerificationCode:
    """Scenario 2.1: Valid registration creates a pending account and returns a verification code.

    Given a valid registration request
    When the client submits the request
    Then a VerificationCode is generated with a 6-digit zero-padded code
    And expires_at is exactly 10 minutes from the injected Clock's current time
    And the VerificationCode is associated with the persisted Account
    And the VerificationCode is persisted via VerificationCodeRepository
    """

    async def test_should_issue_verification_code_on_valid_registration(
        self, register_statements: RegisterStatements
    ):
        await register_statements.register_and_return_account()
        register_statements.assert_verification_code_issued()
