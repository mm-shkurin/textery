from statements.resend_concurrency_statements import ResendConcurrencyStatements


class TestConcurrentResendSingleWriter:
    """Two racing sessions run the FULL resend critical section (lock_for_update ->
    find_active -> cooldown gate -> insert-if-eligible -> commit) on the SAME
    eligible account. The account-row FOR UPDATE lock serializes them: the winner
    reads the 90s-old seeded code (eligible) and inserts; the loser blocks until the
    winner commits, then reads the winner's fresh code (inside the 60s cooldown) and
    skips. Net: seed + exactly one new code. This pins the ADR's exactly-one-writer
    guarantee -- a no-op lock would let both racers insert (three rows) and fail."""

    async def test_should_issue_exactly_one_code_under_concurrent_resend(
        self, resend_concurrency_statements: ResendConcurrencyStatements
    ):
        await resend_concurrency_statements.insert_eligible_account()
        await resend_concurrency_statements.race_two_resends()
        resend_concurrency_statements.assert_exactly_one_new_code_issued()
