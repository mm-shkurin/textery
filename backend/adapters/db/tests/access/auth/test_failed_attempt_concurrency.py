import pytest

from statements.failed_attempt_concurrency_statements import (
    FailedAttemptConcurrencyStatements,
)


@pytest.mark.skip(
    reason="RED 5.3: increment_failed_attempts + failed_attempt_count column are green work"
)
class TestConcurrentIncrementFailedAttempts:
    """Two racing sessions call increment_failed_attempts on the SAME account
    row, each in its own AsyncSession/transaction. Both increments must land, so
    the final persisted failed_attempt_count is exactly 2.

    The `== 2` assertion is the load-bearing falsification guard: a green using a
    DB-side atomic `UPDATE ... SET failed_attempt_count = failed_attempt_count + 1`
    serializes on the row lock and both increments land (final == 2). An ORM
    load-then-save green (both racers read 0, both write 1) yields 1 and fails --
    this is the lost-update race scenario 5.3 forbids."""

    async def test_should_count_both_increments_under_concurrency(
        self, failed_attempt_concurrency_statements: FailedAttemptConcurrencyStatements
    ):
        await failed_attempt_concurrency_statements.insert_verified_account()
        await failed_attempt_concurrency_statements.race_two_increments()
        await failed_attempt_concurrency_statements.fetch_final_failed_attempt_count()
        failed_attempt_concurrency_statements.assert_final_count_is_two()
