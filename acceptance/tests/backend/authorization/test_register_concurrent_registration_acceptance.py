from tests.backend.abstract_backend_test import AbstractBackendTest


class TestRegisterConcurrentRegistrationAcceptance(AbstractBackendTest):
    """Scenario 2.4a: Concurrent registration for the same brand-new email creates
    exactly one account.

    Given an email has never been registered before
    When two registration requests for that exact email are submitted at the same instant
    Then exactly one account is created
    And the other request is rejected as a duplicate, not a second row racing the
    uniqueness check
    """

    async def test_should_create_exactly_one_account_under_concurrent_registration(
        self, auth_statements
    ):
        responses = await auth_statements.given_two_concurrent_registrations_for_same_new_email()

        auth_statements.assert_exactly_one_account_created(responses)
