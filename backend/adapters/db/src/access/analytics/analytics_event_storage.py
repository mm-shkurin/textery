from sqlalchemy.ext.asyncio import AsyncSession

from analytics.analytics_event import AnalyticsEvent
from analytics.analytics_event_repository import SaveOutcome


class SqlAlchemyAnalyticsEventRepository:
    """Postgres implementation of the write-only `AnalyticsEventRepository` port.

    RED-phase stub: `save_new` raises so the scenario-1.1 storage test fails on a
    named, deliberate absence rather than on a table that happens not to exist yet.
    The model and the migration land in `green-adapter db`, not here.

    What green owes this class, from
    `ProductSpecification/stories/14-analytics-event-tracking/decisions/analytics-ingest-shape-decision.md`:

    - `INSERT ... ON CONFLICT (visitor_id, occurrence_key) DO NOTHING RETURNING id`,
      never a prior read. React StrictMode double-invokes effects and genuinely sends
      the second request, so two inserts of one occurrence arriving on two connections
      at the same instant is the ordinary case here, not the rare one -- and
      read-then-insert writes two rows for it.
    - The zero-row case must stay ONE explicit, named decision point. `DO NOTHING`
      returns no row for `ALREADY_RECORDED` *and* for `CONFLICTING_NAME`, and telling
      them apart needs a follow-up read of the stored row's `event_name`. Scenario 1.1
      exercises only `STORED`, so deferring that branch is legitimate -- hardcoding
      `no row -> ALREADY_RECORDED` is not, because it strands the third enum member
      permanently (`progress-backend.md`, adapters-discovery).
    - No commit here. The caller owns the transaction boundary, as every sibling
      storage adapter in this package does.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_new(self, event: AnalyticsEvent) -> SaveOutcome:
        raise NotImplementedError()
