import pytest

from statements.register_statements import RegisterStatements


@pytest.mark.skip(reason="RED: RegisterUser does not validate password policy yet")
class TestRegisterUsecaseWeakPassword:
    """Scenario 1.3: Reject password failing the policy.

    Given a registration request whose password fails the password policy
    When the client submits the request
    Then the response is a validation error
    And no account is created
    """

    @pytest.mark.parametrize(
        "password",
        [
            "Sh0rt!!",
            "nodigit!Aa",
            "n0uppercase!",
            "N0LOWERCASE!",
            "NoSpecial1Char",
            "A1!" + "a" * 126,
        ],
        ids=[
            "too_short",
            "missing_digit",
            "missing_uppercase",
            "missing_lowercase",
            "missing_special_char",
            "too_long",
        ],
    )
    async def test_should_reject_weak_password(self, register_statements: RegisterStatements, password):
        await register_statements.attempt_registering_with_password(password)
        register_statements.assert_invalid_password_error_raised()
