import logging
from uuid import UUID

from adapters.generation_provider import GenerationProvider
from adapters.generation_storage import GenerationStorage

MAX_PROVIDER_ATTEMPTS = 2

logger = logging.getLogger(__name__)


class GenerateDocument:
    def __init__(self, storage: GenerationStorage, provider: GenerationProvider) -> None:
        self._storage = storage
        self._provider = provider

    async def execute(self, generation_id: UUID) -> None:
        generation = await self._storage.get(generation_id)
        generation.mark_in_progress()
        await self._storage.update(generation)

        last_error: Exception | None = None
        for attempt in range(1, MAX_PROVIDER_ATTEMPTS + 1):
            try:
                content = await self._provider.generate(generation)
            except Exception as error:
                last_error = error
                logger.warning(
                    "generation %s provider attempt %d/%d failed: %s",
                    generation.id, attempt, MAX_PROVIDER_ATTEMPTS, error,
                )
                continue
            generation.complete(content)
            await self._storage.update(generation)
            return

        logger.error("generation %s failed after %d attempts: %s", generation.id, MAX_PROVIDER_ATTEMPTS, last_error)
        generation.fail(str(last_error))
        await self._storage.update(generation)
