import uuid

from sqlalchemy import select, text
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
                # Sent explicitly, NOT left to the column defaults. The defaults
                # (`{}` / false) happen to be right for an event that carries
                # neither, which is exactly what made their absence here
                # invisible: every row stored `{}` and `false` and looked correct
                # until a request actually carried a payload and the row still
                # read empty. `validate_payload` has already reduced absent,
                # explicit null and `{}` to one value, so there is nothing left
                # for a default to decide.
                payload=event.payload,
                degraded=event.degraded,
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
            return await self._what_the_conflicting_row_means(event)
        return SaveOutcome.STORED

    async def _what_the_conflicting_row_means(self, event: AnalyticsEvent) -> SaveOutcome:
        """The single decision point for "the insert wrote no row".

        `DO NOTHING` returns nothing for BOTH remaining outcomes and does not say
        which: `ALREADY_RECORDED` (the same occurrence replayed under the same
        name) and `CONFLICTING_NAME` (the same key reused under a DIFFERENT name,
        which `endpoints.md` §2 answers `409 OCCURRENCE_KEY_CONFLICT`) are
        indistinguishable from the statement alone. Telling them apart takes one
        follow-up read of the stored row's `event_name`.

        The read is SAFE TO DO SECOND, which is why the insert still decides the
        collapse on its own. It runs only on the conflict path -- never on the
        common one -- and it cannot resurrect the read-then-insert race it
        replaced: by the time it runs, the row it reads is already committed by
        whoever won, so the answer it gives is stable.

        A row that has vanished between the conflict and this read (an erasure
        running concurrently) reads as the replay. That is the conservative
        answer: reporting a conflict for a key nothing holds would refuse an
        event on the strength of a row that no longer exists.
        """
        stored_name = (
            await self._session.execute(
                select(AnalyticsEventModel.event_name).where(
                    AnalyticsEventModel.visitor_id == event.visitor_id,
                    AnalyticsEventModel.occurrence_key == event.occurrence_key,
                )
            )
        ).scalar_one_or_none()
        if stored_name is not None and stored_name != event.event_name:
            return SaveOutcome.CONFLICTING_NAME
        return SaveOutcome.ALREADY_RECORDED
