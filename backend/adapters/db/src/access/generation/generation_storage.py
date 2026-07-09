from sqlalchemy.ext.asyncio import AsyncSession

from generation.generation import Generation


class SqlAlchemyGenerationStorage:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, generation: Generation) -> None:
        raise NotImplementedError()
