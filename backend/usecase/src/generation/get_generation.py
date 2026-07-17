from uuid import UUID

from generation.generation import Generation
from generation.generation_storage import GenerationStorage


class GetGeneration:
    def __init__(self, storage: GenerationStorage) -> None:
        self._storage = storage

    async def execute(self, generation_id: UUID, owner_id: UUID) -> Generation | None:
        # Absent and foreign collapse to the same None: the ownership predicate is in
        # SQL, so there is no branch here that could tell them apart even by accident.
        # A 403 would confirm the id exists, turning the endpoint into an existence
        # oracle over the id space.
        return await self._storage.get_by_id_and_owner(generation_id, owner_id)
