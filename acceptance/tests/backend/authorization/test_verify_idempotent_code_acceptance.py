from tests.backend.abstract_backend_test import AbstractBackendTest


class TestVerifyIdempotentCodeAcceptance(AbstractBackendTest):
    """Scenario 3.4: Re-submitting an already-consumed code is idempotent.

    Given a code has already been submitted once and the account is now verified
    When the client submits that same code again
    Then the response is the same success outcome
    """

    async def test_should_return_same_success_on_resubmitted_code(self, verify_statements):
        responses = await verify_statements.given_same_code_submitted_twice_for_pending_account()

        verify_statements.assert_both_verified(responses)
