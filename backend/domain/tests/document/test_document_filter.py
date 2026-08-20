"""The narrowing a history request may apply: a text query and a creation-date window."""

from datetime import UTC, datetime

import pytest

from document.document_filter import (
    INVALID_DATE_MESSAGE,
    INVERTED_WINDOW_MESSAGE,
    MAX_QUERY_LENGTH,
    QUERY_TOO_LONG_MESSAGE,
    DocumentFilter,
)
from shared.exceptions import ValidationException


class TestQuery:
    def test_should_treat_an_omitted_query_as_no_narrowing(self):
        assert DocumentFilter.parse().query is None
        assert DocumentFilter.parse().is_empty

    def test_should_trim_the_query_before_it_reaches_the_storage(self):
        assert DocumentFilter.parse(q="  отчёт  ").query == "отчёт"

    def test_should_fold_a_whitespace_only_query_down_to_absence(self):
        # A query of spaces is a user who has not typed anything yet. Matching titles against ' '
        # would empty the screen while they think.
        assert DocumentFilter.parse(q="   ").query is None

    def test_should_refuse_a_query_past_the_cap(self):
        with pytest.raises(ValidationException) as caught:
            DocumentFilter.parse(q="я" * (MAX_QUERY_LENGTH + 1))

        assert caught.value.error_code == "INVALID_QUERY"
        assert caught.value.message == QUERY_TOO_LONG_MESSAGE

    def test_should_accept_a_query_exactly_at_the_cap(self):
        # The boundary itself, so the refusal above cannot be satisfied by an off-by-one that
        # rejects the longest legal query.
        assert DocumentFilter.parse(q="я" * MAX_QUERY_LENGTH).query is not None


class TestDateWindow:
    def test_should_read_a_bare_start_date_as_that_days_first_instant(self):
        assert DocumentFilter.parse(created_from="2026-08-20").created_from == datetime(
            2026, 8, 20, 0, 0, 0, tzinfo=UTC
        )

    def test_should_read_a_bare_end_date_as_that_days_last_instant(self):
        # The two ends read a bare date DIFFERENTLY on purpose. Read both as midnight and
        # «с 20 по 20 августа» matches nothing — the single-day filter a user is most likely to ask
        # for would be the one query that always comes back empty.
        assert DocumentFilter.parse(created_to="2026-08-20").created_to == datetime(
            2026, 8, 20, 23, 59, 59, 999999, tzinfo=UTC
        )

    def test_should_read_a_naive_datetime_as_utc(self):
        # `created_at` is stored aware-UTC. Comparing it against a naive bound raises inside the
        # driver — a 500 for what is a client mistake at worst.
        parsed = DocumentFilter.parse(created_from="2026-08-20T10:30:00")

        assert parsed.created_from == datetime(2026, 8, 20, 10, 30, tzinfo=UTC)

    def test_should_keep_an_explicit_offset_rather_than_reinterpret_it(self):
        parsed = DocumentFilter.parse(created_from="2026-08-20T10:30:00+00:00")

        assert parsed.created_from == datetime(2026, 8, 20, 10, 30, tzinfo=UTC)

    def test_should_not_widen_a_full_datetime_to_the_end_of_its_day(self):
        # The end-of-day widening applies to a BARE date only: a caller who named an instant meant
        # that instant, and rounding it up would silently include a day of extra rows.
        parsed = DocumentFilter.parse(created_to="2026-08-20T10:30:00")

        assert parsed.created_to == datetime(2026, 8, 20, 10, 30, tzinfo=UTC)

    def test_should_treat_an_empty_date_as_omitted(self):
        # A cleared `<input type="date">` reports ''. It must mean "not set", not "parse this".
        assert DocumentFilter.parse(created_from="", created_to="").is_empty

    def test_should_refuse_an_unparseable_date(self):
        with pytest.raises(ValidationException) as caught:
            DocumentFilter.parse(created_from="20.08.2026")

        assert caught.value.error_code == "INVALID_CREATED_FROM"
        assert caught.value.message == INVALID_DATE_MESSAGE

    def test_should_refuse_an_inverted_window(self):
        with pytest.raises(ValidationException) as caught:
            DocumentFilter.parse(created_from="2026-08-21", created_to="2026-08-20")

        assert caught.value.error_code == "INVALID_DATE_RANGE"
        assert caught.value.message == INVERTED_WINDOW_MESSAGE

    def test_should_accept_a_single_day_window(self):
        # The inverted-window guard must not reject «с 20 по 20», which is the same date at both
        # ends and the commonest window of all.
        parsed = DocumentFilter.parse(created_from="2026-08-20", created_to="2026-08-20")

        assert parsed.created_from < parsed.created_to
