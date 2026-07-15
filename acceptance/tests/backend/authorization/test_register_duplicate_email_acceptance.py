import pytest

from tests.backend.abstract_backend_test import AbstractBackendTest


@pytest.mark.skip(
    reason="RED: RegisterUser.execute performs no duplicate-email check -- a second "
    "registration for the same email currently returns 201 with a new account "
    "instead of 409 EMAIL_ALREADY_REGISTERED"
)
class TestRegisterDuplicateEmailAcceptance(AbstractBackendTest):
    """Scenario 2.2: Duplicate email is rejected, verified or pending.

    Given an account already exists for an email, verified
    When a registration request is submitted for that same email
    Then the response is rejected as a duplicate
    And no second account is created

    Given an account already exists for an email, still pending verification
    When a registration request is submitted for that same email
    Then the response is rejected as a duplicate
    And no second account is created
    """

    async def test_should_reject_duplicate_against_verified_account(self, auth_statements):
        response = await auth_statements.given_duplicate_registration_against_verified_account()

        auth_statements.assert_rejected_as_duplicate(response)

    async def test_should_reject_duplicate_against_pending_account(self, auth_statements):
        response = await auth_statements.given_duplicate_registration_against_pending_account()

        auth_statements.assert_rejected_as_duplicate(response)
