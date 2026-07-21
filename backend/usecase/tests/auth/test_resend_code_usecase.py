from statements.resend_code_statements import ResendCodeStatements


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

    async def test_should_measure_the_cooldown_from_the_newest_code_not_the_oldest(
        self, resend_code_statements: ResendCodeStatements
    ):
        """Abuse vector (premortem Incident 1): a green measuring the cooldown against
        the OLDEST/registration code would allow unlimited resends after the first.

        A first legal resend past the cooldown issues code #2; a second resend 30s
        later is inside code #2's window but ~91s past registration. It must be
        rejected — forcing the cooldown to be measured from max(created_at)."""
        await resend_code_statements.given_pending_account_with_a_code_issued_at_t0()
        await resend_code_statements.resend_past_cooldown_then_again_shortly_after_the_second_code()
        resend_code_statements.assert_rejected_as_cooldown_active_with_no_new_code()

    async def test_should_reissue_a_code_with_a_strictly_greater_timestamp_than_the_superseded_one(
        self, resend_code_statements: ResendCodeStatements
    ):
        """Monotonicity (premortem Incident 2 / agent-review): the Fake's insertion-order
        find_active masks a green that persists an equal/earlier timestamp, which the
        real ORDER BY created_at DESC would return the OLD code for. Pins the reissued
        code's timestamp strictly greater than the superseded one's."""
        await resend_code_statements.given_pending_account_with_a_code_issued_at_t0()
        await resend_code_statements.resend_after_the_cooldown_window()
        resend_code_statements.assert_reissued_code_timestamp_is_strictly_greater()
