import uuid

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from analytics.analytics_event import AnalyticsEvent
from analytics.analytics_event_repository import SaveOutcome
from model.analytics.analytics_event_model import CLIENT_ORIGIN_ROWS, AnalyticsEventModel


class SqlAlchemyAnalyticsEventRepository:
    """Postgres implementation of the write-only `AnalyticsEventRepository` port.

    No commit here: the caller owns the transaction boundary, as every sibling
    storage adapter in this package does.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_new(self, event: AnalyticsEvent) -> SaveOutcome:
        """Insert one event, letting the INSERT itself decide the collapse.

        `ON CONFLICT ... DO NOTHING RETURNING id`, never a prior read. React
        StrictMode double-invokes effects and genuinely sends the second request,
        so two inserts of one occurrence arriving on two connections at the same
        instant is the ordinary case here rather than the rare one -- and
        read-then-insert writes two rows for it
        (`decisions/analytics-ingest-shape-decision.md`).
        """
        statement = (
            pg_insert(AnalyticsEventModel)
            .values(
                # Minted here because the entity carries no id -- the store owns
                # it. Discarded by Postgres when the row conflicts, which is fine:
                # nothing outside this method has seen it.
                id=uuid.uuid4(),
                event_name=event.event_name,
                visitor_id=event.visitor_id,
                occurrence_key=event.occurrence_key,
                user_id=event.user_id,
                event_time=event.event_time,
                # `payload` and `degraded` are deliberately not sent: the entity
                # does not carry them yet, and the column defaults (`{}` / false)
                # are the values their scenarios say an event without them has.
            )
            # `index_where` is not decoration: the unique index is PARTIAL, and
            # Postgres refuses to infer a partial index unless the statement
            # repeats its predicate ("no unique or exclusion constraint matching
            # the ON CONFLICT specification"). Repeated by importing the index's
            # own predicate rather than by spelling it out a second time.
            .on_conflict_do_nothing(
                index_elements=["visitor_id", "occurrence_key"],
                index_where=text(CLIENT_ORIGIN_ROWS),
            )
            .returning(AnalyticsEventModel.id)
        )
        inserted_id = (await self._session.execute(statement)).scalar_one_or_none()
        if inserted_id is None:
            return self._what_the_conflicting_row_means()
        return SaveOutcome.STORED

    def _what_the_conflicting_row_means(self) -> SaveOutcome:
        """The single decision point for "the insert wrote no row".

        `DO NOTHING` returns nothing for BOTH remaining outcomes and does not say
        which: `ALREADY_RECORDED` (the same occurrence replayed under the same
        name) and `CONFLICTING_NAME` (the same key reused under a DIFFERENT name,
        which `endpoints.md` §2 answers `409 OCCURRENCE_KEY_CONFLICT`) are
        indistinguishable from the statement alone. Telling them apart requires a
        follow-up read of the stored row's `event_name` -- which is not written
        here because no scenario yet drives it.

        That branch is OWNED BY `tests/extended/01_API_Tests_Extended.md` §3.1,
        which is folded in when §5 goes green. It is deferred, not foreclosed:
        this method is the one place the follow-up read lands, and it is code
        rather than schema, so adding it later costs no migration on a hot table.
        Until then every no-row result is reported as the replay, which is the
        commoner of the two and the one scenario 1.1's neighbours assume.
        """
        return SaveOutcome.ALREADY_RECORDED
