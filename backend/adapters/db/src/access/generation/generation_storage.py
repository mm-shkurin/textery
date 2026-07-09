from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from generation.generation import Generation
from model.generation.generation_model import GenerationModel


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
        model.status = generation.status
        model.content = generation.content
        await self._session.commit()
