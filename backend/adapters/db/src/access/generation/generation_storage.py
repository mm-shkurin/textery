from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from generation.generation import IN_PROGRESS_STATUS, PENDING_STATUS, Generation
from model.generation.generation_model import GenerationModel
from shared.exceptions import ConflictException, NotFoundException


class SqlAlchemyGenerationStorage:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, generation: Generation) -> None:
        self._session.add(GenerationModel.from_domain(generation))
        await self._session.commit()

    async def get(self, generation_id: UUID) -> Optional[Generation]:
        model = await self._session.get(GenerationModel, generation_id)
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

    async def list_stale(self, older_than: datetime) -> list[Generation]:
        stmt = select(GenerationModel).where(
            GenerationModel.status.in_((PENDING_STATUS, IN_PROGRESS_STATUS)),
            GenerationModel.created_at < older_than,
        )
        result = await self._session.execute(stmt)
        return [model.to_domain() for model in result.scalars().all()]
