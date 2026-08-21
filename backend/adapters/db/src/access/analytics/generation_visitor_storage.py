"""`GenerationVisitorLog` over Postgres. Never raises, on its own session.

`ON CONFLICT DO NOTHING` on the write: a requeue re-requests a generation that
already has a row, and the FIRST visitor is the one the funnel means -- the
browser that asked. Overwriting it on a retry would move the generation into
whichever visitor happened to trigger the requeue, which for the stale sweep is
no visitor at all (§9.10).
"""

from collections.abc import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from access.analytics.fail_open import in_own_session
from model.analytics.generation_visitor_model import GenerationVisitorModel


class SqlAlchemyGenerationVisitorLog:
    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory

    async def remember(self, generation_id: UUID, visitor_id: UUID | None) -> None:
        if visitor_id is None:
            return

        async def write(session: AsyncSession) -> None:
            await session.execute(
                pg_insert(GenerationVisitorModel)
                .values(generation_id=generation_id, visitor_id=visitor_id)
                .on_conflict_do_nothing(index_elements=["generation_id"])
            )
            await session.commit()

        await in_own_session(
            self._session_factory, "generation visitor was not remembered", write, None
        )

    async def visitor_of(self, generation_id: UUID) -> UUID | None:
        async def read(session: AsyncSession) -> UUID | None:
            result = await session.execute(
                select(GenerationVisitorModel.visitor_id).where(
                    GenerationVisitorModel.generation_id == generation_id
                )
            )
            return result.scalar_one_or_none()

        return await in_own_session(
            self._session_factory, "generation visitor was not read", read, None
        )
