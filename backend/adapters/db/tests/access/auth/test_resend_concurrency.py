import pytest

from statements.resend_concurrency_statements import ResendConcurrencyStatements


class TestConcurrentResendSerialization:
    """Two racing sessions run the resend critical section (lock_for_update ->
    find_active -> insert -> commit) on the SAME eligible account. The account-row
    FOR UPDATE lock serializes them: the loser blocks until the winner commits,
    then its post-lock read reflects the winner's committed insert -- it does NOT
    read the stale pre-race state concurrently. This pins the serialization that
    scenario 4.4's exactly-one-resend guarantee is built on."""

    @pytest.mark.skip(
        reason="RED: SqlAlchemyAccountRepository.lock_for_update does not exist yet; "
        "green-adapter db adds SELECT ... FOR UPDATE to serialize concurrent resends."
    )
    async def test_should_serialize_resend_reads_under_concurrent_lock(
        self, resend_concurrency_statements: ResendConcurrencyStatements
    ):
        await resend_concurrency_statements.insert_eligible_account()
        await resend_concurrency_statements.race_two_resends()
        resend_concurrency_statements.assert_reads_were_serialized()
