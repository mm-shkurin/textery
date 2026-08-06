from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

_ID_ONE = UUID("11111111-1111-4111-8111-111111111111")
_ID_TWO = UUID("22222222-2222-4222-8222-222222222222")

# 16:26:53 at +07:00 is 09:26:53Z. Both existing seeds in
# test_project_list_row_serialization.py are already `tzinfo=UTC`, which is the
# identity case for `astimezone` -- they pass whether the serializer normalizes to
# UTC or merely echoes whatever offset it was handed. This one does not.
_SEVEN_HOURS_EAST = timezone(timedelta(hours=7))
# The second timestamp is seeded at a *different* offset, and one west of UTC. A
# serializer caught echoing on `created_at` alone would leave `updated_at`
# unobserved -- the guarantee is "timestamps", not "the first timestamp" -- and a
# single eastern offset cannot tell a real conversion from a fixed -7h shift.
_FIVE_HOURS_WEST = timezone(timedelta(hours=-5))


class TestListProjectsWireContract:
    """Story 12 Scenario 1.1: four wire guarantees the whole-body equality is blind to.

    The sibling row-serialization test compares the entire response body against a
    hand-written literal. That comparison cannot see: an offset echoed instead of
    converted (both its seeds are already UTC); a naive timestamp silently shifted
    by the deploy host's offset; a JSON `0` where the contract says `false`
    (`json.loads('{"r": 0}') == {"r": False}` is `True` in Python, in both
    directions); or an unknown `status` forwarded verbatim.
    """

    async def test_should_convert_a_non_utc_timestamp_to_utc(
        self, feed_serving, feed_client, contract_row, expected_row
    ):
        """projects_list.yaml: timestamps are UTC ISO-8601. Converted, not echoed."""
        usecase = feed_serving(
            contract_row(
                _ID_ONE,
                created_at=datetime(2026, 3, 14, 16, 26, 53, tzinfo=_SEVEN_HOURS_EAST),
                updated_at=datetime(2026, 3, 15, 13, 4, 7, tzinfo=_FIVE_HOURS_WEST),
            ),
        )

        async with feed_client(usecase) as client:
            response = await client.get("/api/v1/projects")

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        # Whole-row, not the two timestamps alone: converting the offsets while
        # dropping or corrupting one of the other seven fields is not a pass.
        assert response.json()["items"] == [expected_row(_ID_ONE)], (
            f"a +07:00 and a -05:00 instant must both reach the wire as UTC, "
            f"got {response.json()['items']!r}"
        )

    async def test_should_refuse_a_naive_timestamp_rather_than_shift_it(
        self, feed_serving, feed_client, contract_row
    ):
        """A naive value has no instant, and guessing one is worse than failing.

        `astimezone(UTC)` does NOT raise on a naive datetime: Python reads it as
        system local time. So a serializer that only converts turns a *visible*
        violation (an offset-less string, which the acceptance parser rejects)
        into an invisible one -- a well-formed `Z` string naming the wrong
        instant, shifted by whatever offset the deploy host happens to run, green
        in a UTC container and silently wrong on a developer machine. The refusal
        is the guarantee; which exception type carries it is the green's choice,
        so this pins the `ValueError` that `pydantic.ValidationError` also is.

        The *message* is not left to the green, though. It names the offending
        field and the reason -- "created_at must be timezone-aware" -- so a
        refusal that fired for some unrelated reason, or named the wrong field,
        cannot satisfy this test. The match is unanchored on purpose: pydantic
        wraps a field validator's message in its own "Value error, ..." envelope,
        and the substring survives either implementation.
        """
        usecase = feed_serving(
            contract_row(_ID_ONE, created_at=datetime(2026, 3, 14, 16, 26, 53)),
        )

        with pytest.raises(ValueError, match=r"created_at must be timezone-aware"):
            async with feed_client(usecase) as client:
                await client.get("/api/v1/projects")

    async def test_should_emit_retryable_as_a_json_boolean(
        self, feed_serving, feed_client, contract_row, expected_row
    ):
        """`False == 0` in Python, so the sibling dict equality cannot see an int.

        Both polarities are seeded: a field typed `int` emits `0` and `1`, and
        each compares equal to the boolean the literal expects. Asserted with
        `is`, not `==` and not `isinstance`: `0 is False` and `1 is True` are both
        `False` for JSON-decoded ints, so identity pins the type *and* the
        polarity in one assertion, where `isinstance` pins only the type and would
        pass a row whose value was inverted.
        """
        usecase = feed_serving(
            contract_row(_ID_ONE, retryable=False),
            contract_row(_ID_TWO, status="failed", retryable=True),
        )

        async with feed_client(usecase) as client:
            response = await client.get("/api/v1/projects")

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        items = response.json()["items"]
        # Equality first -- it carries the row count and the other eight fields of
        # both rows. It cannot carry the *type* of `retryable`, which is the whole
        # point of this test, so the identity reads follow it rather than replace it.
        assert items == [
            expected_row(_ID_ONE, retryable=False),
            expected_row(_ID_TWO, status="failed", retryable=True),
        ], f"unexpected rows {items!r}"
        assert items[0]["retryable"] is False, (
            f"retryable reached the wire as "
            f"{type(items[0]['retryable']).__name__} {items[0]['retryable']!r}"
        )
        assert items[1]["retryable"] is True, (
            f"retryable reached the wire as "
            f"{type(items[1]['retryable']).__name__} {items[1]['retryable']!r}"
        )

    async def test_should_fail_an_unknown_status_closed_without_blanking_the_page(
        self, feed_serving, feed_client, contract_row, expected_row
    ):
        """projects_list.yaml: an unrecognised status becomes `unknown`, always present.

        Fail-closed here means a 200 carrying `unknown`, never a non-200 and never
        a dropped row. The page is seeded with two rows on purpose: `ProjectItemDto`
        is built per row with no isolation, so a DTO that *rejected* the unknown
        value would raise into the catch-all handler and blank the whole feed -- one
        bad row costing one caller their entire page. A per-row problem must never
        become a per-page failure, so the expectation is a two-element list
        compared whole -- the row count is asserted, not implied.
        """
        usecase = feed_serving(
            contract_row(_ID_ONE, status="teapot"),
            contract_row(_ID_TWO, status="ready"),
        )

        async with feed_client(usecase) as client:
            response = await client.get("/api/v1/projects")

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        items = response.json()["items"]
        # A two-element equality, so the row count is asserted rather than implied:
        # a DTO that rejected the unknown value would blank the page and fail here.
        assert items == [
            expected_row(_ID_ONE, status="unknown"),
            expected_row(_ID_TWO),
        ], f"unexpected rows {items!r}"
