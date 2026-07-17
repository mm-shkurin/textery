from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from access.keyset_pagination import paginate_by_owner
from generation.generation import IN_PROGRESS_STATUS, PENDING_STATUS, Generation
from model.generation.generation_model import GenerationModel
from shared.exceptions import ConflictException, NotFoundException
from shared.keyset_cursor import KeysetCursor


class SqlAlchemyGenerationStorage:
    """Storage adapter for generations.

    There is deliberately no `get(id)`: the only by-id read filters on `owner_id`
    **in SQL**, so a foreign generation falls out as `None` structurally rather
    than relying on every caller remembering an ownership `if`. A `get(id)` sitting
    alongside `get_by_id_and_owner` would be one autocomplete away from undoing
    that -- the same reasoning as `SqlAlchemyDocumentStorage`, see
    decisions/document-ownership-decision.md.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, generation: Generation) -> None:
        self._session.add(GenerationModel.from_domain(generation))
        await self._session.commit()

    async def get_by_id_and_owner(
        self, generation_id: UUID, owner_id: UUID
    ) -> Generation | None:
        result = await self._session.execute(
            select(GenerationModel).where(
                GenerationModel.id == generation_id,
                GenerationModel.owner_id == owner_id,
            )
        )
        model = result.scalar_one_or_none()
        return model.to_domain() if model is not None else None

    async def update(self, generation: Generation) -> None:
        model = await self._session.get(GenerationModel, generation.id)
        if model is None:
            raise NotFoundException(f"generation {generation.id} not found")
        if model.version != generation.version:
            raise ConflictException(f"generation {generation.id} was concurrently modified")
        model.status = generation.status
        model.content = generation.content
        model.error_message = generation.error_message
        model.version += 1
        await self._session.commit()
        generation.version = model.version

    async def list_by_owner(
        self, owner_id: UUID, limit: int, cursor: KeysetCursor | None
    ) -> list[Generation]:
        return [
            model.to_domain()
            for model in await paginate_by_owner(
                self._session, GenerationModel, owner_id, limit, cursor
            )
        ]

    async def list_stale(self, older_than: datetime) -> list[Generation]:
        stmt = select(GenerationModel).where(
            GenerationModel.status.in_((PENDING_STATUS, IN_PROGRESS_STATUS)),
            GenerationModel.created_at < older_than,
        )
        result = await self._session.execute(stmt)
        return [model.to_domain() for model in result.scalars().all()]
