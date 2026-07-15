from tests.backend.abstract_backend_test import AbstractBackendTest


class TestRegisterRetryIdempotentAcceptance(AbstractBackendTest):
    """Scenario 2.4: A retried identical registration request produces exactly one account.

    Given a registration request has already succeeded, creating a pending account and a code
    When the client retries the identical registration request against the same email
    Then exactly one account exists for that email
    And exactly one verification code is active for that account
    """

    async def test_should_reject_identical_retry_as_duplicate(self, auth_statements):
        response = await auth_statements.given_identical_registration_request_retried()

        auth_statements.assert_rejected_as_duplicate(response)
