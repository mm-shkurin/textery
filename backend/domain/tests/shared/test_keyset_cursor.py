import base64
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from shared.keyset_cursor import KeysetCursor


class TestRoundTrip:
    """A cursor survives encode/decode with both halves of the key intact."""

    def test_should_restore_created_at_and_id(self):
        created_at = datetime(2026, 7, 17, 12, 30, 45, 123456, tzinfo=UTC)
        id = uuid4()

        restored = KeysetCursor.decode(KeysetCursor(created_at, id).encode())

        assert (restored.created_at, restored.id) == (created_at, id), (
            f"expected ({created_at}, {id}), got ({restored.created_at}, {restored.id})"
        )

    def test_should_preserve_microseconds(self):
        # Not a redundant round-trip test: the whole point of pairing created_at
        # with id is sub-second collisions, so a cursor that silently truncated
        # microseconds would seek to the wrong row and skip or repeat one.
        created_at = datetime(2026, 7, 17, 12, 30, 45, 999999, tzinfo=UTC)

        restored = KeysetCursor.decode(KeysetCursor(created_at, uuid4()).encode())

        assert restored.created_at.microsecond == 999999, (
            f"expected microsecond 999999, got {restored.created_at.microsecond}"
        )

    def test_should_preserve_timezone(self):
        created_at = datetime(2026, 7, 17, 12, 30, 45, tzinfo=UTC)

        restored = KeysetCursor.decode(KeysetCursor(created_at, uuid4()).encode())

        assert restored.created_at.tzinfo is not None, (
            "a naive cursor would compare wrongly against a timestamptz column"
        )
        assert restored.created_at == created_at, (
            f"expected {created_at}, got {restored.created_at}"
        )


class TestOf:
    """`of` anchors on anything carrying created_at and id."""

    def test_should_anchor_on_an_entity(self):
        class _Row:
            id = uuid4()
            created_at = datetime(2026, 7, 17, tzinfo=UTC)

        cursor = KeysetCursor.of(_Row())

        assert (cursor.created_at, cursor.id) == (_Row.created_at, _Row.id), (
            f"expected the row's own key, got ({cursor.created_at}, {cursor.id})"
        )


class TestDecodeRejectsGarbage:
    """Every unusable shape collapses to one ValueError -- naming which half was
    wrong would describe our storage layout to someone probing it."""

    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "!!!not base64!!!",
            base64.urlsafe_b64encode(b"no-separator-here").decode(),
            base64.urlsafe_b64encode(b"not-a-date|" + str(uuid4()).encode()).decode(),
            base64.urlsafe_b64encode(b"2026-07-17T12:00:00+00:00|not-a-uuid").decode(),
            base64.urlsafe_b64encode(b"|").decode(),
            base64.urlsafe_b64encode(b"\xff\xfe").decode(),
        ],
        ids=["empty", "not-base64", "no-separator", "bad-date", "bad-uuid", "both-empty", "bad-utf8"],
    )
    def test_should_raise_value_error(self, raw):
        with pytest.raises(ValueError):
            KeysetCursor.decode(raw)

    @pytest.mark.parametrize("raw", [None, 42, b"bytes"], ids=["none", "int", "bytes"])
    def test_should_raise_value_error_for_a_non_string(self, raw):
        with pytest.raises(ValueError):
            KeysetCursor.decode(raw)
