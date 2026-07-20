from tests.backend.abstract_backend_test import AbstractBackendTest


class TestVerifyAlreadyVerifiedAcceptance(AbstractBackendTest):
    """Scenario 3.5: verify against an already-verified account is rejected.

    Given an account already verified with its issued code
    When the client submits a verify request with a different code for that email
    Then the response is 409 ALREADY_VERIFIED (not the 400 generic rejection)
    """

    async def test_should_reject_with_409_when_account_already_verified(
        self, verify_statements
    ):
        response = await verify_statements.given_verified_account_then_verify_with_a_different_code()

        verify_statements.assert_already_verified_rejected(response)
