"""The analytics events table: one write, and the read that interprets its refusal.

**The insert decides the collapse — never a prior read.** `ON CONFLICT ... DO
NOTHING RETURNING id`. React StrictMode double-invokes effects and genuinely
sends the second request, so two inserts of one occurrence arriving on two
connections at the same instant is the ORDINARY case here rather than the rare
one, and read-then-insert writes two rows for it
(`decisions/analytics-ingest-shape-decision.md`).

**`index_where` is not decoration.** The unique index is PARTIAL, and Postgres
refuses to infer a partial index unless the statement repeats its predicate
("no unique or exclusion constraint matching the ON CONFLICT specification").
Repeated by importing the index's own predicate rather than by spelling it out
a second time.

**Every column is sent explicitly, not left to its default.** The defaults
(`{}` / false) happen to be right for an event carrying neither, which is
exactly what made their absence invisible: every row stored `{}` and `false`
and looked correct until a request actually carried a payload and the row still
read empty. `validate_payload` has already reduced absent, explicit null and
`{}` to one value, so there is nothing left for a default to decide.

**`DO NOTHING` returns nothing for two DIFFERENT outcomes** and does not say
which. `ALREADY_RECORDED` (the same occurrence replayed under the same name) and
`CONFLICTING_NAME` (the same key reused under a DIFFERENT name, which
`endpoints.md` §2 answers `409 OCCURRENCE_KEY_CONFLICT`) are indistinguishable
from the statement alone, so `_what_the_conflicting_row_means` reads the stored
row's `event_name`. That read is safe to do SECOND, which is why the insert still
decides the collapse on its own: it runs only on the conflict path, and by the
time it runs the row it reads is already committed by whoever won, so its answer
is stable. A row that has vanished between the conflict and the read (a
concurrent erasure) reads as the replay — the conservative answer, since
reporting a conflict for a key nothing holds would refuse an event on the
strength of a row that is gone.
"""

import uuid

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.dml import ReturningInsert

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
        """Insert one event, letting the INSERT itself decide the collapse."""
        statement = insert_of(event)
        inserted_id = (await self._session.execute(statement)).scalar_one_or_none()
        if inserted_id is None:
            return await self._what_the_conflicting_row_means(event)
        return SaveOutcome.STORED

    async def _what_the_conflicting_row_means(self, event: AnalyticsEvent) -> SaveOutcome:
        """Tell a replay apart from a reused key. Rationale: the module docstring."""
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


def insert_of(event: AnalyticsEvent) -> ReturningInsert[tuple[uuid.UUID]]:
    """The one statement this store issues, spelled out once.

    Public because the fail-open `SqlAlchemyServerEventRecorder` executes the same
    statement. It takes the STATEMENT rather than calling this repository: one
    third-layer adapter must not call another (`.claude/rules/coding-rules.md`),
    and a module-level statement builder is shared code, not a peer.
    """
    return (
        pg_insert(AnalyticsEventModel)
        .values(
            # Minted here: the entity carries no id, so the store owns it.
            id=uuid.uuid4(),
            event_name=event.event_name,
            visitor_id=event.visitor_id,
            occurrence_key=event.occurrence_key,
            user_id=event.user_id,
            event_time=event.event_time,
            payload=event.payload,
            degraded=event.degraded,
        )
        .on_conflict_do_nothing(
            index_elements=["visitor_id", "occurrence_key"],
            index_where=text(CLIENT_ORIGIN_ROWS),
        )
        .returning(AnalyticsEventModel.id)
    )
