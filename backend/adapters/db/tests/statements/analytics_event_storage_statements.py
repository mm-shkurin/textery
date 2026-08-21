"""Test DSL for scenario 1.1 at the storage layer -- what Postgres actually holds.

Given a visitor with no session
When it reports a site visit
Then the event is recorded
And the stored event has no account attached.

The usecase test for this scenario proves the usecase builds the right
`AnalyticsEvent` and hands it to the port; a Fake answered it, so nothing there
touches a column. This layer's claim is the other half: the adapter turns that
entity into a row, the row survives a commit, and every field arrives where the
next reader looks for it.

**Read back in raw SQL, not through the port.** `endpoints.md` ships no read
surface at all ("reading is Story 15"), so `AnalyticsEventRepository` deliberately
grows no finder -- there is no second port to assert through, and inventing one
here would hand Story 15 a contract it has not designed. The acceptance probe
(`acceptance/clients/database/analytics_event_probe.py`) reads the same columns
the same way for the same reason; the adapters-discovery record approves this
shape explicitly rather than treating it as a way around write-here-read-there.

**On a session of its own.** `create_session_factory` sets `expire_on_commit=False`,
so a re-read inside the writing session is served from SQLAlchemy's identity map
and would pass on a row Postgres never received.

Columns are named, never `SELECT *`: `occurrence_key`, `event_name` and `user_id`
are the three the acceptance probe reads by name, so a green that spells one of
them differently must fail here -- at the adapter, where the column is chosen --
rather than two layers away in the acceptance suite.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from access.analytics.analytics_event_storage import SqlAlchemyAnalyticsEventRepository
from analytics.analytics_event import AnalyticsEvent
from analytics.analytics_event_repository import SaveOutcome
from statements.arranged import arranged

# The browser-origin name for a page view (`api-specs/analytics_events_create.yaml`).
SITE_VISITED = "SITE_VISITED"

# A fixed instant, deliberately not "around now". `event_time` is stamped by the
# usecase from an injected Clock, so the adapter's only job is to carry the value it
# was handed -- and an adapter that let Postgres fill the column with `now()` instead
# can only be caught by an expected value the database cannot produce.
#
# The seconds and microseconds are non-zero ON PURPOSE, and are the one thing this
# constant does not share with the usecase test's `_SERVER_NOW`. A whole-second instant
# is carried unchanged by a `TIMESTAMP(0)` column that truncates every real event to the
# second, so 09:30:00.000000 cannot tell a full-precision column from a truncating one --
# and this is the only layer where the column type is exercised at all. The
# AcceptanceCriteria ask for exactly that guard ("a timestamp with non-zero microseconds
# survives store -> read unchanged; the column does not truncate to seconds"); before
# this value carried sub-second digits, no scenario in the story owned it.
REPORTED_AT = datetime(2026, 8, 20, 9, 30, 12, 345678, tzinfo=UTC)

# Scoped to ONE visitor and to nothing narrower, exactly as the acceptance probe is.
# The visitor is minted fresh per run, so every row this returns was written by the
# call under test -- which makes the row COUNT an assertable claim ("exactly one event
# exists for this visitor") instead of a claim about the subset that already matched
# what was expected. `occurrence_key` is therefore selected back rather than pinned in
# the WHERE: a lookup keyed on it can only return rows that already carry the right
# value, so a rewritten or NULL key would read as "nothing was written at all".
_SELECT_EVENTS_FOR_VISITOR = text(
    "SELECT occurrence_key, event_name, user_id, event_time "
    "FROM analytics_events "
    "WHERE visitor_id = :visitor_id"
)


@dataclass(frozen=True)
class StoredEventRow:
    """One `analytics_events` row as Postgres holds it, coercing nothing.

    Every column is typed for the NULL the database may hold, so a NULL that should
    have been a value reaches the comparison as `None` and fails there rather than
    being filled in with a default on the way past.
    """

    occurrence_key: UUID | None
    event_name: str | None
    # NULL is the whole point of scenario 1.1: an anonymous event carries no account.
    user_id: UUID | None
    event_time: datetime | None


class AnalyticsEventStorageStatements:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._visitor_id = uuid4()
        self._occurrence_key = uuid4()
        self._outcome: SaveOutcome | None = None
        self._stored_rows: tuple[StoredEventRow, ...] | None = None

    async def when_a_visitor_with_no_session_reports_a_site_visit(self) -> None:
        # `user_id=None` IS the scenario: the caller sent no Authorization header. It
        # never means "a token was sent and could not be resolved" -- 1.3 refuses that
        # before anything reaches the store, so an anonymous row here can never be a
        # downgraded bad token.
        event = AnalyticsEvent(
            event_name=SITE_VISITED,
            visitor_id=self._visitor_id,
            occurrence_key=self._occurrence_key,
            user_id=None,
            event_time=REPORTED_AT,
        )
        async with self._session_factory() as session:
            self._outcome = await SqlAlchemyAnalyticsEventRepository(session).save_new(event)
            # The adapter does not commit -- the caller owns the boundary, and "the
            # event is recorded" means durable: the fresh read below runs on another
            # connection, where an uncommitted insert is invisible.
            await session.commit()

    def assert_the_store_reported_a_new_row(self) -> None:
        # A first-time occurrence is STORED and nothing else. Asserted rather than
        # ignored because the port answers three outcomes and the other two both mean
        # "no row was written by this call" -- an adapter that answered
        # ALREADY_RECORDED for a successful insert would still leave a readable row
        # behind and pass every assertion below it.
        outcome = arranged(self._outcome, "the outcome save_new answered")
        assert outcome is SaveOutcome.STORED, (
            f"expected a first-time occurrence to be reported as {SaveOutcome.STORED}, "
            f"got {outcome}"
        )

    async def read_back_the_stored_events_on_a_fresh_connection(self) -> None:
        async with self._session_factory() as session:
            result = await session.execute(
                _SELECT_EVENTS_FOR_VISITOR, {"visitor_id": self._visitor_id}
            )
            self._stored_rows = tuple(
                StoredEventRow(
                    occurrence_key=row.occurrence_key,
                    event_name=row.event_name,
                    user_id=row.user_id,
                    event_time=row.event_time,
                )
                for row in result
            )

    def assert_the_event_is_recorded(self) -> None:
        # One structural comparison against the whole expected row rather than a field
        # at a time: StoredEventRow is a frozen dataclass, so this pins every column
        # the read names at once and reports a pinpoint diff when one of them is wrong.
        stored = self._the_one_stored_row()
        expected = self._the_visit_as_reported()
        assert stored == expected, (
            f"expected the stored row to be the visit exactly as it was reported "
            f"({expected!r}), got {stored!r}"
        )

    def _the_visit_as_reported(self) -> StoredEventRow:
        # `occurrence_key` is pinned to the value the client minted because it is what
        # makes the StrictMode double-fire collapse into one row later -- a key the
        # server replaced on the way in would collapse nothing.
        return StoredEventRow(
            occurrence_key=self._occurrence_key,
            event_name=SITE_VISITED,
            user_id=None,
            event_time=REPORTED_AT,
        )

    def assert_no_account_is_attached(self) -> None:
        # `user_id` is NULL exactly, not merely "different from a signed-in caller's":
        # a sentinel account, or the visitor id copied across, would satisfy a looser
        # check and hand Story 15 a phantom account in its cohort figures.
        stored = self._the_one_stored_row()
        assert stored.user_id is None, (
            f"expected an anonymous event to carry no account, got user_id={stored.user_id!r}"
        )

    def _the_one_stored_row(self) -> StoredEventRow:
        # One reported visit is one stored row. Counted rather than indexed, so a
        # second row written under values the visitor never reported fails here
        # instead of sitting unseen behind `rows[0]`.
        rows = arranged(self._stored_rows, "the rows read back for this visitor")
        assert len(rows) == 1, (
            f"expected exactly one stored event for visitor_id={self._visitor_id}, "
            f"got {len(rows)}: {rows!r}"
        )
        return rows[0]
