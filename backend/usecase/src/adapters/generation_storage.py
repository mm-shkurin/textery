from datetime import datetime
from typing import Protocol
from uuid import UUID

from generation.generation import Generation
from shared.keyset_cursor import KeysetCursor


class GenerationStorage(Protocol):
    async def save(self, generation: Generation) -> None:
        ...

    async def get_by_id_and_owner(
        self, generation_id: UUID, owner_id: UUID
    ) -> Generation | None:
        ...

    async def update(self, generation: Generation) -> None:
        ...

    async def list_stale(self, older_than: datetime) -> list[Generation]:
        ...

    async def list_by_owner(
        self, owner_id: UUID, limit: int, cursor: KeysetCursor | None
    ) -> list[Generation]:
        """The owner's generations, newest first, starting after `cursor`.

        Unlike `list_stale` -- the cross-owner sweep -- this is a caller-facing
        read, so `owner_id` is a predicate, not a hint.
        """
        ...
