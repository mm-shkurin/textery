from uuid import UUID

from adapters.generation_provider import GenerationProvider
from adapters.generation_storage import GenerationStorage


class GenerateDocument:
    def __init__(self, storage: GenerationStorage, provider: GenerationProvider) -> None:
        self._storage = storage
        self._provider = provider

    async def execute(self, generation_id: UUID) -> None:
        generation = await self._storage.get(generation_id)
        generation.mark_in_progress()
        await self._storage.update(generation)
        try:
            content = await self._provider.generate(generation)
        except Exception as error:
            generation.fail(str(error))
            await self._storage.update(generation)
            return
        generation.complete(content)
        await self._storage.update(generation)
