import pytest

from tests.backend.abstract_backend_test import AbstractBackendTest


@pytest.mark.skip(
    reason="RED: the accounts.email uniqueness check is a case-sensitive DB UNIQUE "
    "constraint with no normalization -- registering 'User@Example.ru' after "
    "'user@example.ru' currently returns 201 with a new account instead of 409 "
    "EMAIL_ALREADY_REGISTERED"
)
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
