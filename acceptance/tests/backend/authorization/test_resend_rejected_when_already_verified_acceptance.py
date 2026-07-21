import pytest

from tests.backend.abstract_backend_test import AbstractBackendTest


@pytest.mark.skip(
    reason="RED: 4.5 needs an is_verified gate in ResendCode.execute BEFORE the "
    "cooldown check. Today a verified account's immediate resend falls through to "
    "the cooldown and answers 429 RESEND_COOLDOWN_ACTIVE, not 409 ALREADY_VERIFIED."
)
class TestResendRejectedWhenAlreadyVerifiedAcceptance(AbstractBackendTest):
    """Scenario 4.5: a resend requested against an already-verified account is
    rejected, already verified.

    Given an account is already verified
    When the client requests a resend for that account
    Then the response is 409 ALREADY_VERIFIED (not the 429 RESEND_COOLDOWN_ACTIVE
    the request currently falls through to, because the is_verified gate must be
    checked before the cooldown).
    """

    async def test_should_reject_resend_with_409_when_account_already_verified(
        self, resend_statements
    ):
        resend_response = await resend_statements.given_resend_for_a_verified_account()

        resend_statements.assert_resend_rejected_as_already_verified(resend_response)
