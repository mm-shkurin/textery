"""`GenerationVisitorLog` over Postgres. Never raises, on its own session.

`ON CONFLICT DO NOTHING` on the write: a requeue re-requests a generation that
already has a row, and the FIRST visitor is the one the funnel means -- the
browser that asked. Overwriting it on a retry would move the generation into
whichever visitor happened to trigger the requeue, which for the stale sweep is
no visitor at all (§9.10).
"""

import logging
from collections.abc import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from model.analytics.generation_visitor_model import GenerationVisitorModel

logger = logging.getLogger(__name__)


class SqlAlchemyGenerationVisitorLog:
    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory

    async def remember(self, generation_id: UUID, visitor_id: UUID | None) -> None:
        if visitor_id is None:
            return
        session = self._session_factory()
        try:
            await session.execute(
                pg_insert(GenerationVisitorModel)
                .values(generation_id=generation_id, visitor_id=visitor_id)
                .on_conflict_do_nothing(index_elements=["generation_id"])
            )
            await session.commit()
        except Exception as error:
            logger.warning("generation visitor was not remembered: %s", type(error).__name__)
        finally:
            await session.close()

    async def visitor_of(self, generation_id: UUID) -> UUID | None:
        session = self._session_factory()
        try:
            result = await session.execute(
                select(GenerationVisitorModel.visitor_id).where(
                    GenerationVisitorModel.generation_id == generation_id
                )
            )
            return result.scalar_one_or_none()
        except Exception as error:
            logger.warning("generation visitor was not read: %s", type(error).__name__)
            return None
        finally:
            await session.close()
