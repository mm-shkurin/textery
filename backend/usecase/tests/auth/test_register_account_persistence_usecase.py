
from statements.register_statements import RegisterStatements


class TestRegisterUsecasePersistsAccount:
    """Scenario 1.5: Ignore server-owned fields in the request body.

    Given a valid registration request
    When the client submits the request
    Then a real Account is persisted with a server-generated id and is_verified=false
    And created_at comes from the injected Clock, never from caller input
    """

    async def test_should_persist_account_with_server_owned_fields(
        self, register_statements: RegisterStatements
    ):
        await register_statements.register_and_return_account()
        register_statements.assert_account_persisted_with_server_owned_fields()
