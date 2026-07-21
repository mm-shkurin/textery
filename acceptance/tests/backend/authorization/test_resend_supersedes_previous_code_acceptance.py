from tests.backend.abstract_backend_test import AbstractBackendTest


class TestResendCooldownActiveAcceptance(AbstractBackendTest):
    """Scenario 4.1 (HTTP-observable slice): the resend endpoint is live and the
    cooldown is enforced, so an immediate resend is rejected 429
    RESEND_COOLDOWN_ACTIVE.

    This test does NOT assert the scenario's success path — "a resend more than 60
    seconds after the previous issuance returns a new 6-digit code and the old one
    no longer verifies". That success path is NOT observable at the acceptance
    layer: the resend cooldown is
    measured from the last issuance (registration counts, per
    decisions/resend-code-cooldown-and-supersession-decision.md), and there is no
    server-clock lever over HTTP to advance past the 60s window without a real
    wall-clock wait. That success + supersession is therefore proven at the
    usecase layer with a FakeClock (test_resend_code_usecase.py), mirroring how
    3.6 / 2.4b / 3.4 pushed non-HTTP-observable time invariants down a layer.

    What IS observable, and what this test pins end-to-end over real HTTP: the
    resend endpoint is live and the cooldown is enforced. A just-registered
    account's code is <60s old, so an immediate resend falls inside the cooldown
    and is rejected 429 RESEND_COOLDOWN_ACTIVE. This closes the endpoint-liveness
    question (route mounted + DI wired + the 429 mapping) that the unit tests
    cannot cross.
    """

    async def test_should_reject_an_immediate_resend_as_cooldown_active(self, resend_statements):
        resend_response, _context = await resend_statements.given_resend_for_pending_account()

        resend_statements.assert_resend_rejected_as_cooldown_active(resend_response)
