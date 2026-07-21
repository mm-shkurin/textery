import pytest

from statements.resend_code_statements import ResendCodeStatements


@pytest.mark.skip(reason="RED: ResendCode usecase not implemented (cooldown gate + supersession)")
class TestResendCodeUsecase:
    """Scenario 4.1: Resend issues a new code and invalidates the previous one.

    Given a pending account with an active verification code
    When the client requests a resend, more than 60 seconds after the previous issuance
    Then a new 6-digit code is returned
    And the previous code no longer verifies the account

    Both behaviours are FakeClock-driven because the acceptance layer has no
    server-clock lever: the 60s cooldown gate, and the insert-only supersession
    that makes the reissued code the only one that verifies.
    """

    async def test_should_reject_a_resend_requested_within_the_cooldown_window(
        self, resend_code_statements: ResendCodeStatements
    ):
        await resend_code_statements.given_pending_account_with_a_code_issued_at_t0()
        await resend_code_statements.resend_within_the_cooldown_window()
        resend_code_statements.assert_rejected_as_cooldown_active_with_no_new_code()

    async def test_should_issue_a_new_code_that_supersedes_the_old_one_after_the_cooldown(
        self, resend_code_statements: ResendCodeStatements
    ):
        await resend_code_statements.given_pending_account_with_a_code_issued_at_t0()
        await resend_code_statements.resend_after_the_cooldown_window()
        await resend_code_statements.verify_with_the_old_code_then_the_new_code()
        resend_code_statements.assert_new_code_issued_and_supersedes_the_old_one()

    async def test_should_allow_a_resend_at_exactly_the_60s_cooldown_boundary(
        self, resend_code_statements: ResendCodeStatements
    ):
        """Pins the ADR's `now - max(created_at) >= 60s` — allowed AT 60s, not just past it.

        Without this, WITHIN=30s/PAST=61s leave (30,61] passing, so an off-by-one
        green (`> 60`) would wrongly reject a legit resend at exactly 60s yet still
        pass both other tests.
        """
        await resend_code_statements.given_pending_account_with_a_code_issued_at_t0()
        await resend_code_statements.resend_at_the_exact_cooldown_boundary()
        resend_code_statements.assert_a_new_code_was_issued_at_the_boundary()
