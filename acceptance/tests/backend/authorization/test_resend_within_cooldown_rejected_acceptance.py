from tests.backend.abstract_backend_test import AbstractBackendTest


class TestResendWithinCooldownRejectedAcceptance(AbstractBackendTest):
    """Scenario 4.2 (black-box regression pin): a resend requested while the
    previous verification code is still inside its cooldown window is rejected
    with 429 RESEND_COOLDOWN_ACTIVE, and the pending account keeps its existing
    code.

    This is a NAMED regression pin for 4.2's distinct spec requirement — a resend
    *within* the cooldown is rejected — kept alongside 4.1's
    `TestResendCooldownActiveAcceptance` in the same way 2.4a/2.4b/2.4d stand as
    separate named pins for distinct requirements that share an already-green
    HTTP slice. It records NO independent RED phase: the resend endpoint already
    enforces the cooldown, so this test PASSES on first run.

    The 4.2-specific precision that this black-box test cannot express is proven
    at the usecase layer with a FakeClock
    (`backend/usecase/tests/auth/test_resend_code_usecase.py::
    test_should_reject_a_resend_requested_within_the_cooldown_window`):
    - the code was issued specifically ~30s ago (T0 + WITHIN_COOLDOWN = 30s), a
      mid-window instant distinct from 4.1's ~0s immediate resend; and
    - "no new code is issued" — the assertion pins that the saved-codes count is
      unchanged after the rejected resend.
    The acceptance layer has NO server-clock lever, so "issued 30 seconds ago"
    cannot be pinned precisely over HTTP; a just-registered account's code is
    <60s old, which is the only within-cooldown instant HTTP can reach. What this
    test DOES pin end-to-end over real HTTP: the live endpoint rejects a
    within-cooldown resend with the exact 429 RESEND_COOLDOWN_ACTIVE contract.
    """

    async def test_should_reject_a_resend_within_the_cooldown_window(self, resend_statements):
        resend_response, _context = await resend_statements.given_resend_for_pending_account()

        resend_statements.assert_resend_rejected_as_cooldown_active(resend_response)
