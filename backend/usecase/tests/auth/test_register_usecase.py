import pytest

from statements.register_statements import RegisterStatements


class TestRegisterUsecaseMalformedEmail:
    """Scenario 1.1: Reject malformed email.

    Given a registration request with a malformed email address
    When the client submits the request
    Then the response is a validation error
    And no account is created
    """

    @pytest.mark.parametrize(
        "email",
        ["not-an-email", "missing-at-sign.ru", "user@", "@example.ru", "user@@example.ru", "user@ example.ru"],
        ids=["no_at_sign", "no_at_sign_dotted", "missing_domain", "missing_local_part", "double_at", "embedded_space"],
    )
    async def test_should_reject_malformed_email(self, register_statements: RegisterStatements, email):
        await register_statements.attempt_registering_with_email(email)
        register_statements.assert_invalid_email_error_raised()

    @pytest.mark.parametrize(
        "email",
        [None, 12345],
        ids=["none_value", "int_value"],
    )
    async def test_should_reject_non_string_email(self, register_statements: RegisterStatements, email):
        await register_statements.attempt_registering_with_email(email)
        register_statements.assert_invalid_email_error_raised()
