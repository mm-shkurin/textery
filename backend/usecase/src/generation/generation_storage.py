from datetime import datetime
from typing import Protocol
from uuid import UUID

from generation.generation import Generation
from shared.keyset_cursor import KeysetCursor


class GenerationStorage(Protocol):
    async def save(self, generation: Generation) -> None: ...

    async def get_by_id_and_owner(
        self, generation_id: UUID, owner_id: UUID
    ) -> Generation | None: ...

    async def update(self, generation: Generation) -> None: ...

    async def list_stale(self, older_than: datetime) -> list[Generation]: ...

    async def find_by_owner_and_idempotency_key(
        self, owner_id: UUID, idempotency_key: str
    ) -> "Generation | None":
        """The generation this owner already created under `idempotency_key`.

        Scoped to the owner and not to the key alone: keying on the header by
        itself lets one account's replay return another account's row, and the
        replay path short-circuits before any ownership check would run.
        """
        ...

    async def count_retries_of(self, source_generation_id: UUID) -> int:
        """How many generations name this one as their source.

        Counted in the database rather than tracked on the row: the backend runs
        as multiple instances, so a counter held anywhere but in shared storage
        bounds nothing.
        """
        ...

    async def list_by_owner(
        self, owner_id: UUID, limit: int, cursor: KeysetCursor | None
    ) -> list[Generation]:
        """The owner's generations, newest first, starting after `cursor`.

        Unlike `list_stale` -- the cross-owner sweep -- this is a caller-facing
        read, so `owner_id` is a predicate, not a hint.
        """
        ...
