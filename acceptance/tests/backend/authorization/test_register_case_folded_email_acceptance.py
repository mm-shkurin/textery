from tests.backend.abstract_backend_test import AbstractBackendTest


class TestRegisterCaseFoldedEmailAcceptance(AbstractBackendTest):
    """Scenario 2.3: Case-folded email uniqueness.

    Given an account already exists for "user@example.ru"
    When a registration request is submitted for "User@Example.ru"
    Then the response is rejected as a duplicate, the same account
    """

    async def test_should_reject_registration_with_different_case_of_existing_email(
        self, auth_statements
    ):
        response = await auth_statements.given_duplicate_registration_with_different_case()

        auth_statements.assert_rejected_as_duplicate(response)
