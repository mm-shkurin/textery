from tests.backend.abstract_backend_test import AbstractBackendTest


class TestRegisterServerOwnedFieldsAcceptance(AbstractBackendTest):
    """Scenario 1.5: Ignore server-owned fields in the request body.

    Given a registration request whose body also sets is_verified to true and an id
    When the client submits the request
    Then the created account's is_verified is false, not the attacker-supplied value
    And the created account's id is server-generated, not the attacker-supplied value
    """

    async def test_should_ignore_server_owned_fields_in_request_body(self, auth_statements):
        response = await auth_statements.given_registration_request_with_server_owned_fields()

        auth_statements.assert_server_owned_fields_ignored(response)
