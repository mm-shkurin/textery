"""Test DSL for scenario 1.1 -- an event with no token is recorded as anonymous.

Given a visitor with no session
When it reports a site visit
Then the event is recorded
And the stored event has no account attached.

The acceptance test for this scenario proves the row reaches Postgres and comes back
on another connection. What it cannot see is *where the values came from*, and that is
this layer's claim: the account is the one the caller resolved (here: none), the
identifiers are the ones the visitor reported, and the timestamp is the server's --
never a value the request could have chosen.

`visitor_id` and `occurrence_key` are minted as UUIDs and handed to the usecase as
strings, which is exactly what the router does with a permissively-typed DTO. The
minted UUID is therefore the expected value and the string is merely the wire form --
no assertion below converts one into the other, so a usecase that stored the raw text
fails on a `'…'`-against-`UUID('…')` mismatch rather than passing an equal-looking
comparison.

Every assertion routes through `_the_one_recorded_event`, so no claim about a field
can be reached unless exactly one event was recorded: a run that recorded nothing
fails on the cardinality instead of on an `is None` that would have read as success.

«The event is recorded» is asserted as one structural comparison against the whole
expected `AnalyticsEvent` rather than field by field. AnalyticsEvent is a frozen
dataclass, so that compares every field it has -- including the ones a future scenario
adds, which is what stops a new column from arriving without 1.1 stating its value for
an anonymous visit. The two `And` clauses below keep their own named single assertions
because the scenario names them, not because the comparison misses them.
"""

from datetime import UTC, datetime
from uuid import uuid4

from analytics.analytics_event import AnalyticsEvent
from analytics.record_analytics_event import RecordAnalyticsEvent
from fake.analytics.fake_analytics_event_repository import FakeAnalyticsEventRepository
from fake.auth.fake_clock import FakeClock
from fake.auth.fake_unit_of_work import FakeUnitOfWork

# Deliberately not "around now": a usecase that reached for the wall clock instead of
# the injected one has to fail this, and it only does if the fixed instant is one the
# wall clock cannot produce.
_SERVER_NOW = datetime(2026, 8, 20, 9, 30, tzinfo=UTC)


class AnalyticsIngestStatements:
    # The browser-origin name for a page view (analytics_events_create.yaml).
    SITE_VISITED = "SITE_VISITED"

    def __init__(self) -> None:
        self._repository = FakeAnalyticsEventRepository()
        self._unit_of_work = FakeUnitOfWork()
        self._usecase = RecordAnalyticsEvent(
            analytics_event_repository=self._repository,
            clock=FakeClock(_SERVER_NOW),
            unit_of_work=self._unit_of_work,
        )
        self._visitor_id = uuid4()
        self._occurrence_key = uuid4()

    async def when_a_visitor_with_no_session_reports_a_site_visit(self) -> None:
        # `user_id=None` IS the scenario. It is the caller saying "no Authorization
        # header was sent", not "I could not work out who this is": §1.3 refuses the
        # second case before it ever reaches this call, so an anonymous event here is
        # never a downgraded bad token.
        await self._usecase.execute(
            user_id=None,
            event_name=self.SITE_VISITED,
            visitor_id=str(self._visitor_id),
            occurrence_key=str(self._occurrence_key),
        )

    def assert_the_event_is_recorded(self) -> None:
        recorded = self._the_one_recorded_event()
        expected = self._the_visit_as_reported()
        assert recorded == expected, (
            f"expected the recorded event to be the visit exactly as it was reported "
            f"({expected!r}), got {recorded!r}"
        )

    def _the_visit_as_reported(self) -> AnalyticsEvent:
        # The whole event, not three of its fields: every value the usecase is allowed
        # to put on the entity is stated here, so nothing can be recorded that no
        # assertion looked at. That is also what keeps the domain field gate honest --
        # when §3.x puts `payload` on AnalyticsEvent, this comparison goes red until
        # 1.1 says what an anonymous visit stores in it, instead of letting the new
        # field ride along unasserted.
        #
        # `occurrence_key` is pinned to the value the client minted because it is what
        # makes the StrictMode double-fire collapse into one row at §5.x -- a key the
        # server replaced would collapse nothing.
        return AnalyticsEvent(
            event_name=self.SITE_VISITED,
            visitor_id=self._visitor_id,
            occurrence_key=self._occurrence_key,
            user_id=None,
            event_time=_SERVER_NOW,
        )

    def assert_no_account_is_attached(self) -> None:
        recorded = self._the_one_recorded_event()
        # `user_id` is None exactly, not merely "different from a signed-in caller's":
        # a placeholder account, an anonymous sentinel or the visitor id copied across
        # would each satisfy a looser check and each would hand Story 15 a phantom
        # account in its cohort figures.
        assert recorded.user_id is None, (
            f"expected an anonymous event to carry no account, got user_id={recorded.user_id!r}"
        )

    def assert_the_event_time_came_from_the_server_clock(self) -> None:
        recorded = self._the_one_recorded_event()
        # The request schema carries no client timestamp, so this is not about
        # preferring the server's value over the caller's -- it is about the usecase
        # taking the injected Clock rather than reading the wall clock itself, which
        # is what makes every time-dependent scenario after this one controllable.
        assert recorded.event_time == _SERVER_NOW, (
            f"expected the event to be stamped from the injected clock "
            f"({_SERVER_NOW!r}), got event_time={recorded.event_time!r}"
        )

    def assert_the_recording_was_committed_once(self) -> None:
        # «An event is recorded» means the row is durable and readable elsewhere, not
        # that a write was issued: the acceptance test reads it back on a separate
        # connection, and an uncommitted insert is invisible there. Exactly once, so a
        # commit per retry cannot hide inside a "at least one" check.
        assert self._unit_of_work.commit_call_count == 1, (
            f"expected exactly one commit, got {self._unit_of_work.commit_call_count}"
        )
        assert self._unit_of_work.rollback_call_count == 0, (
            f"expected no rollback on the stored path, got {self._unit_of_work.rollback_call_count}"
        )

    def _the_one_recorded_event(self) -> AnalyticsEvent:
        # One reported visit is one recorded event. Counted rather than indexed, so a
        # second event written under values the visitor never reported fails here
        # instead of sitting unseen behind `recorded[0]`.
        assert len(self._repository.recorded) == 1, (
            f"expected exactly one recorded event for visitor_id={self._visitor_id} "
            f"occurrence_key={self._occurrence_key}, got "
            f"{len(self._repository.recorded)}: {self._repository.recorded!r}"
        )
        return self._repository.recorded[0]
