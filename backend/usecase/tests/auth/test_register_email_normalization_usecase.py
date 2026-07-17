
from statements.register_statements import RegisterStatements


class TestRegisterUsecaseEmailNormalization:
    """Scenario 2.3: Case-folded email uniqueness.

    Given a registration request with a mixed-case email
    When RegisterUser.execute persists the Account
    Then the persisted Account.email is the lowercased/normalized form,
    not the raw request casing
    """

    async def test_should_persist_account_with_normalized_email(
        self, register_statements: RegisterStatements
    ):
        await register_statements.register_with_mixed_case_email_and_return_account()
        register_statements.assert_account_persisted_with_normalized_email()
