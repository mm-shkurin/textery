from tests.backend.abstract_backend_test import AbstractBackendTest


class TestVerifyConcurrentAcceptance(AbstractBackendTest):
    """Scenario 3.6: Concurrent verify requests for the same account produce
    exactly one transition (HTTP-observable part).

    Given a pending account with an active, correct verification code
    When two verify requests with that code are submitted at the same instant
    Then exactly one request transitions the account to verified
    And the other observes the resulting verified state, not a duplicate
    transition or an error
    """

    async def test_should_return_verified_for_both_concurrent_verifies(
        self, verify_statements
    ):
        responses = await verify_statements.given_two_concurrent_verifies_with_the_same_code()

        verify_statements.assert_both_verified(responses)
