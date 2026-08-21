from uuid import UUID

from analytics.analytics_event import AnalyticsEvent
from analytics.analytics_event_repository import AnalyticsEventRepository
from shared.clock import Clock
from shared.unit_of_work import UnitOfWork


class RecordAnalyticsEvent:
    """Record one client-origin analytics event.

    `user_id` is a parameter, never a field of the reported event: the caller
    resolves it from the Authorization header, so a client cannot attribute its
    own events to somebody else's account by putting an id in the body. `None`
    means the header was absent -- scenario 1.1. A header that was sent and did
    not resolve never reaches here at all (§1.3).

    The rate limiter and the failure-log emitter named in
    `decisions/analytics-ingest-shape-decision.md` are NOT constructor slots yet:
    nothing in 1.1 asserts either, and a collaborator pinned by no assertion is a
    shape the tests cannot defend. They arrive with §6.x and Infra 1.1.
    """

    def __init__(
        self,
        analytics_event_repository: AnalyticsEventRepository,
        clock: Clock,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._analytics_event_repository = analytics_event_repository
        self._clock = clock
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        user_id: UUID | None,
        event_name: str,
        visitor_id: str,
        occurrence_key: str,
    ) -> None:
        """`visitor_id` and `occurrence_key` arrive as the raw strings the request
        carried -- the DTO types them permissively so a bad value reaches the
        domain and returns the canonical 400 rather than Pydantic's 422, which
        would echo the rejected input back on the product's only tokenless route.

        The `SaveOutcome` the port answers with is deliberately not read here.
        Only `STORED` is a path at 1.1; the 204-vs-409 branch on
        `ALREADY_RECORDED` / `CONFLICTING_NAME` lands with the scenarios that
        assert it -- `tests/extended/01_API_Tests_Extended.md` §3.1, not §5.x:
        `01_API_Tests.md` §5.1-§5.6 hold no conflicting-name scenario (§5.3 is a
        *malformed* key), so the earlier §5.x pointer named a scenario that does
        not exist.
        """
        event = AnalyticsEvent(
            event_name=event_name,
            # Parsed, not stored as text: the entity types both identifiers as
            # `UUID` so the four spellings of one visitor id (§2.4) resolve to
            # one value before anything downstream sees them.
            visitor_id=UUID(visitor_id),
            occurrence_key=UUID(occurrence_key),
            # Straight through from the caller. The usecase never reads an id
            # out of the reported event, so a client cannot attribute its
            # events to another account.
            user_id=user_id,
            # The injected Clock, never `datetime.now()` -- that is what keeps
            # every later time-dependent scenario controllable.
            event_time=self._clock.now(),
        )
        await self._analytics_event_repository.save_new(event)
        # «The event is recorded» means durable: the acceptance test reads the
        # row back on a separate connection, where an uncommitted insert is
        # invisible.
        await self._unit_of_work.commit()
