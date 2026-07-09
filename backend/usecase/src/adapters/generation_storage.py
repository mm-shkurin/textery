from typing import Protocol

from generation.generation import Generation


class GenerationStorage(Protocol):
    async def save(self, generation: Generation) -> None:
        ...
