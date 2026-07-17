from datetime import datetime
from typing import Optional, Protocol
from uuid import UUID

from generation.generation import Generation


class GenerationStorage(Protocol):
    async def save(self, generation: Generation) -> None:
        ...

    async def get_by_id_and_owner(
        self, generation_id: UUID, owner_id: UUID
    ) -> Optional[Generation]:
        ...

    async def update(self, generation: Generation) -> None:
        ...

    async def list_stale(self, older_than: datetime) -> list[Generation]:
        ...
