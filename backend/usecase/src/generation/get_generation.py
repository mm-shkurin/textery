from typing import Optional
from uuid import UUID

from adapters.generation_storage import GenerationStorage
from generation.generation import Generation


class GetGeneration:
    def __init__(self, storage: GenerationStorage) -> None:
        self._storage = storage

    async def execute(self, generation_id: UUID, owner_id: UUID) -> Optional[Generation]:
        # Absent and foreign collapse to the same None: the ownership predicate is in
        # SQL, so there is no branch here that could tell them apart even by accident.
        # A 403 would confirm the id exists, turning the endpoint into an existence
        # oracle over the id space.
        return await self._storage.get_by_id_and_owner(generation_id, owner_id)
