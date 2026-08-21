"""Test DSL for §3.6 -- a payload survives store and read with its values unchanged.

Its own file rather than another method on `AnalyticsEventStorageStatements`,
which is at the file-size cap, and its own scenario rather than a widening of 1.1:
1.1 is the anonymous visit that carries NO payload, and the two claims fail for
different reasons.

This scenario exists because of a defect it would have caught. The adapter's
INSERT deliberately omitted `payload` and `degraded` while the entity did not yet
carry them, and the column defaults (`{}` / false) are exactly the values an event
without them has -- so every row read back correct, and kept reading correct after
the entity grew both fields, until a request actually carried a payload and the
stored row was still empty. A default that agrees with the absent case hides the
difference between "carried nothing" and "carried something that was dropped".
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from access.analytics.analytics_event_storage import SqlAlchemyAnalyticsEventRepository
from analytics.analytics_event import AnalyticsEvent
from statements.arranged import arranged

SITE_VISITED = "SITE_VISITED"
REPORTED_AT = datetime(2026, 8, 20, 9, 30, 12, 345678, tzinfo=UTC)

# Nested, multibyte, and holding every JSON scalar type. Not decoration: JSONB
# normalises what it stores, so a payload of one flat ASCII string would pass
# against a column that mangles Cyrillic, reorders nothing and collapses nothing.
# `false` and `0` are in here because both are falsy in Python and an adapter that
# guarded its write with `if payload:` would drop a payload that is entirely made
# of them.
REPORTED_PAYLOAD: dict[str, Any] = {
    "path": "/редактор",
    "depth": {"nested": ["a", 1, True]},
    "zero": 0,
    "flag": False,
}

_SELECT_PAYLOAD_FOR_VISITOR = text(
    "SELECT payload, degraded FROM analytics_events WHERE visitor_id = :visitor_id"
)


@dataclass(frozen=True)
class StoredPayloadRow:
    payload: dict[str, Any] | None
    degraded: bool | None


class AnalyticsPayloadStorageStatements:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._visitor_id = uuid4()
        self._stored_rows: tuple[StoredPayloadRow, ...] | None = None

    async def when_a_visitor_reports_a_visit_carrying_a_payload(self) -> None:
        event = AnalyticsEvent(
            event_name=SITE_VISITED,
            visitor_id=self._visitor_id,
            occurrence_key=uuid4(),
            user_id=None,
            event_time=REPORTED_AT,
            payload=REPORTED_PAYLOAD,
            # Reported TRUE, and asserted, for the same reason the payload is: the
            # column defaults to false, so a `degraded` the adapter never writes is
            # indistinguishable from one it wrote correctly on every row that was
            # not degraded -- which is almost all of them.
            degraded=True,
        )
        async with self._session_factory() as session:
            await SqlAlchemyAnalyticsEventRepository(session).save_new(event)
            await session.commit()

    async def read_back_the_stored_events_on_a_fresh_connection(self) -> None:
        async with self._session_factory() as session:
            result = await session.execute(
                _SELECT_PAYLOAD_FOR_VISITOR, {"visitor_id": self._visitor_id}
            )
            self._stored_rows = tuple(
                StoredPayloadRow(payload=row.payload, degraded=row.degraded) for row in result
            )

    def assert_the_payload_is_stored_exactly_as_reported(self) -> None:
        stored = self._the_one_stored_row()
        expected = StoredPayloadRow(payload=REPORTED_PAYLOAD, degraded=True)
        assert stored == expected, (
            f"expected the stored row to carry the payload exactly as reported "
            f"({expected!r}), got {stored!r}"
        )

    def _the_one_stored_row(self) -> StoredPayloadRow:
        rows = arranged(self._stored_rows, "the rows read back for this visitor")
        assert len(rows) == 1, (
            f"expected exactly one stored event for visitor_id={self._visitor_id}, "
            f"got {len(rows)}: {rows!r}"
        )
        return rows[0]
