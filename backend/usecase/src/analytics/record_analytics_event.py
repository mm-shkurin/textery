from uuid import UUID

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
        """
        raise NotImplementedError()
