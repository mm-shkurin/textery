from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from shared.exceptions import ValidationException
from shared.keyset_cursor import KeysetCursor
from shared.page import DEFAULT_LIMIT, MAX_LIMIT, MIN_LIMIT, Page, PageRequest

_BASE_TIME = datetime(2026, 7, 17, 12, 0, 0, tzinfo=UTC)


class _Row:
    def __init__(self, offset_seconds: int) -> None:
        self.id = uuid4()
        self.created_at = _BASE_TIME - timedelta(seconds=offset_seconds)


def _rows(count: int) -> list:
    return [_Row(offset_seconds=index) for index in range(count)]


class TestLimitBounds:
    """limit is validated in the domain, so a violation carries this project's
    error_code rather than Pydantic's envelope."""

    @pytest.mark.parametrize(
        "limit", [MIN_LIMIT, DEFAULT_LIMIT, MAX_LIMIT], ids=["min", "default", "max"]
    )
    def test_should_accept_a_limit_in_range(self, limit):
        assert PageRequest(limit=limit).limit == limit, f"limit {limit} must be accepted"

    @pytest.mark.parametrize(
        "limit", [0, -1, MAX_LIMIT + 1, 1000], ids=["zero", "negative", "over-max", "far-over"]
    )
    def test_should_reject_a_limit_out_of_range(self, limit):
        with pytest.raises(ValidationException) as error:
            PageRequest(limit=limit)
        assert error.value.error_code == "INVALID_LIMIT", (
            f"expected INVALID_LIMIT, got {error.value.error_code}"
        )

    @pytest.mark.parametrize("limit", [True, False], ids=["true", "false"])
    def test_should_reject_a_bool_limit(self, limit):
        # bool subclasses int, so `limit=true` would otherwise sail through as 1
        # (or fail the range check as 0) instead of being rejected as a bad type.
        with pytest.raises(ValidationException) as error:
            PageRequest(limit=limit)
        assert error.value.error_code == "INVALID_LIMIT", (
            f"expected INVALID_LIMIT for {limit!r}, got {error.value.error_code}"
        )

    @pytest.mark.parametrize("limit", ["20", 1.5, None], ids=["string", "float", "none"])
    def test_should_reject_a_non_integer_limit(self, limit):
        with pytest.raises(ValidationException) as error:
            PageRequest(limit=limit)
        assert error.value.error_code == "INVALID_LIMIT", (
            f"expected INVALID_LIMIT for {limit!r}, got {error.value.error_code}"
        )


class TestCursorDecoding:
    def test_should_leave_cursor_none_when_absent(self):
        assert PageRequest(limit=10, cursor=None).cursor is None, "the first page has no anchor"

    def test_should_decode_a_valid_cursor(self):
        row = _Row(offset_seconds=0)

        decoded = PageRequest(limit=10, cursor=KeysetCursor.of(row).encode()).cursor

        assert (decoded.created_at, decoded.id) == (row.created_at, row.id), (
            f"expected ({row.created_at}, {row.id}), got ({decoded.created_at}, {decoded.id})"
        )

    def test_should_reject_a_malformed_cursor(self):
        with pytest.raises(ValidationException) as error:
            PageRequest(limit=10, cursor="not-a-cursor")
        assert error.value.error_code == "INVALID_CURSOR", (
            f"expected INVALID_CURSOR, got {error.value.error_code}"
        )


class TestFetchSize:
    def test_should_request_one_extra_row_as_the_has_next_probe(self):
        assert PageRequest(limit=20).fetch_size == 21, (
            "fetch_size must be limit+1 -- the extra row is what answers 'is there "
            "another page' without a COUNT"
        )


class TestPageOf:
    def test_should_trim_the_probe_row_and_emit_a_cursor_when_more_remain(self):
        rows = _rows(21)

        page = Page.of(rows, limit=20)

        assert len(page.items) == 20, f"expected 20 items, got {len(page.items)}"
        assert page.items == rows[:20], "the probe row must not be served to the client"
        assert page.next_cursor is not None, "a full page with more behind it needs an anchor"

    def test_should_anchor_the_cursor_on_the_last_served_row(self):
        rows = _rows(21)

        decoded = KeysetCursor.decode(Page.of(rows, limit=20).next_cursor)

        # The 20th row, not the 21st probe: anchoring on the probe would skip it.
        assert (decoded.created_at, decoded.id) == (rows[19].created_at, rows[19].id), (
            f"expected the anchor on row 19, got ({decoded.created_at}, {decoded.id})"
        )

    def test_should_emit_no_cursor_on_a_partial_last_page(self):
        page = Page.of(_rows(5), limit=20)

        assert len(page.items) == 5, f"expected 5 items, got {len(page.items)}"
        assert page.next_cursor is None, "a null cursor is the client's stop condition"

    def test_should_emit_no_cursor_on_an_exactly_full_final_page(self):
        # Exactly `limit` rows means the probe found nothing behind them. Emitting a
        # cursor here would hand the client one more round trip for an empty page.
        page = Page.of(_rows(20), limit=20)

        assert len(page.items) == 20, f"expected 20 items, got {len(page.items)}"
        assert page.next_cursor is None, "no probe row means no next page"

    def test_should_handle_an_empty_result(self):
        page = Page.of([], limit=20)

        assert page.items == [], f"expected no items, got {page.items}"
        assert page.next_cursor is None, f"expected no cursor, got {page.next_cursor}"
