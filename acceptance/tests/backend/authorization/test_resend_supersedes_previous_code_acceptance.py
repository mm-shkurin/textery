import pytest

from tests.backend.abstract_backend_test import AbstractBackendTest


@pytest.mark.skip(reason="RED: POST /api/v1/auth/resend-code not implemented (404)")
class TestResendSupersedesPreviousCodeAcceptance(AbstractBackendTest):
    """Scenario 4.1: Resend issues a new code and invalidates the previous one.

    Given a pending account with an active verification code
    When the client requests a resend, more than 60 seconds after the previous issuance
    Then a new 6-digit code is returned
    And the previous code no longer verifies the account

    HTTP-observable scope: this acceptance test pins the two effects that ARE
    observable over HTTP without a server-clock lever — (a) a resend returns a
    fresh 6-digit code that differs from the previous one, and (b) after the
    resend the OLD code no longer verifies while the NEW code does.

    Design-step preconditions (NOT resolved here, flagged for `design`):
      1. Cooldown-timing observability. The scenario's ">60 seconds after the
         previous issuance" precondition only clears the resend COOLDOWN (whose
         within-window rejection is scenario 4.2). The acceptance layer has no
         server-clock lever, so — mirroring scenarios 3.6 / 2.4b / 3.4, where
         non-HTTP-observable time invariants were pushed to the usecase layer
         with a FakeClock — proving the cooldown boundary itself belongs to
         design / red-usecase, not here. No real 60s wall-clock wait is used.
      2. First-resend-inside-cooldown. A just-registered account's first resend
         may fall inside the cooldown window (cooldown measured from last
         issuance). If so, this test's single immediate resend would be gated.
         The design step must decide how a fresh registration's first resend is
         treated (e.g. registration issuance does not start the cooldown, or the
         window is otherwise clear). This test expresses the intended end-state
         (new code supersedes old) and currently fails RED on the absent
         /api/v1/auth/resend-code endpoint (404), independent of that decision.
    """

    async def test_should_issue_new_code_and_invalidate_previous(self, resend_statements):
        resend_response, context = await resend_statements.given_resend_for_pending_account()

        resend_statements.assert_new_code_issued(resend_response, context)

        old_verify, new_verify = await resend_statements.when_old_and_new_codes_submitted(
            resend_response, context
        )
        resend_statements.assert_old_code_no_longer_verifies(old_verify)
        resend_statements.assert_new_code_verifies(new_verify)
