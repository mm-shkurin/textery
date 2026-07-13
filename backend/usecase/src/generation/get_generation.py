from typing import Optional
from uuid import UUID

from adapters.generation_storage import GenerationStorage
from generation.generation import Generation


class GetGeneration:
    def __init__(self, storage: GenerationStorage) -> None:
        self._storage = storage

    async def execute(self, generation_id: UUID) -> Optional[Generation]:
        return await self._storage.get(generation_id)
