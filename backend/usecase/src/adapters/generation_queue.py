from typing import Protocol
from uuid import UUID


class GenerationQueue(Protocol):
    async def enqueue(self, generation_id: UUID) -> None:
        ...
