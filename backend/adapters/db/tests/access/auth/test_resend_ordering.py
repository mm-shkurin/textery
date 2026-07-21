import pytest

from statements.resend_ordering_statements import ResendOrderingStatements


class TestTiedCreatedAtDeterminism:
    """Two active codes with EQUAL created_at but different ids: find_active must
    deterministically return the greater-id row. Today find_active orders by
    created_at DESC only, so on a tie postgres row order is UNDEFINED -- asserting
    the max-id row would be flaky, not a clean RED. Skip-marked until green adds the
    ', id DESC' secondary sort, at which point this becomes a deterministic GREEN
    pin (max-id row always returned)."""

    @pytest.mark.skip(
        reason="RED: ', id DESC' tiebreak not implemented; on equal created_at "
        "postgres row order is undefined (would be flaky). Becomes a clean GREEN "
        "pin once find_active_by_account_id adds the secondary id DESC sort."
    )
    async def test_should_return_greater_id_code_on_equal_created_at(
        self, resend_ordering_statements: ResendOrderingStatements
    ):
        await resend_ordering_statements.save_two_codes_with_equal_created_at()
        resend_ordering_statements.assert_returns_greater_id_code()


class TestNeverZeroOnRolledBackInsert:
    """Insert code A + commit, then drive a second insert (code B) and roll it back
    without committing. find_active_by_account_id must still return code A -- never
    None. Insert-only supersession never mutates or deletes the prior row, so an
    aborted resend leaves the committed code active. Regression pin (already-green),
    left unmarked."""

    async def test_should_keep_committed_code_active_after_rolled_back_insert(
        self, resend_ordering_statements: ResendOrderingStatements
    ):
        await resend_ordering_statements.save_committed_code_then_rollback_second_insert()
        resend_ordering_statements.assert_active_is_committed_code_never_none()
