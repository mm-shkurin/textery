from typing import Protocol

from generation.generation import Generation


class GenerationProvider(Protocol):
    async def generate(self, generation: Generation) -> str:
        ...
