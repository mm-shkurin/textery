import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from uuid import UUID

from generation.generation_provider import GenerationProvider
from generation.generation_storage import GenerationStorage

MAX_PROVIDER_ATTEMPTS = 2
GENERIC_FAILURE_MESSAGE = "Не удалось сгенерировать документ. Попробуйте позже."

# Waited between provider attempts, doubling per retry. Without it the retry
# fires microseconds after the failure and, against a rate-limited or briefly-down
# provider, fails for the identical reason -- two attempts spending one attempt's
# worth of luck. The jitter keeps a batch of generations that all failed at once
# (a provider blip, or the sweep re-triggering a backlog) from retrying in a
# synchronised wave.
_RETRY_BASE_DELAY_SECONDS = 1.0
_RETRY_JITTER_SECONDS = 0.5

logger = logging.getLogger(__name__)


class GenerateDocument:
    def __init__(
        self,
        storage: GenerationStorage,
        provider: GenerationProvider,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self._storage = storage
        self._provider = provider
        # Injectable so the retry tests do not spend real seconds asleep.
        self._sleep = sleep or asyncio.sleep

    async def execute(self, generation_id: UUID, owner_id: UUID) -> None:
        # The owner is threaded through rather than looked up, so that the storage
        # can expose exactly one by-id read and it is the owner-filtered one. This is
        # not an authorization check -- this path is internal and already trusted; the
        # pair is simply the locator. Callers pass the generation's own owner.
        generation = await self._storage.get_by_id_and_owner(generation_id, owner_id)
        if generation is None:
            # The port returns Optional and this runs in a BackgroundTask, where an
            # AttributeError on None is raised into the task's context: nothing
            # answers for it, so it would surface only as a row stuck pending until
            # the sweep. Reachable without a bug -- the row can be gone by the time
            # the task runs, and the sweep re-triggers from a list read earlier.
            logger.warning(
                "generation %s not found for owner %s; nothing to do", generation_id, owner_id
            )
            return

        generation.mark_in_progress()
        await self._storage.update(generation)

        last_error: Exception | None = None
        for attempt in range(1, MAX_PROVIDER_ATTEMPTS + 1):
            try:
                content = await self._provider.generate(generation)
            except Exception as error:
                # Every exception, not just ProviderError. The row is already
                # persisted as in_progress by this point, so anything that escapes
                # here strands it in that state until the stale sweep notices --
                # and a provider raising TimeoutError or httpx.ConnectError rather
                # than wrapping it in ProviderError is exactly the kind of thing
                # that is true of an adapter without this layer knowing.
                last_error = error
                logger.warning(
                    "generation %s provider attempt %d/%d failed: %s",
                    generation.id,
                    attempt,
                    MAX_PROVIDER_ATTEMPTS,
                    error,
                )
                if attempt < MAX_PROVIDER_ATTEMPTS:
                    await self._sleep(self._backoff_for(attempt))
                continue
            generation.complete(content)
            await self._storage.update(generation)
            return

        logger.error(
            "generation %s failed after %d attempts: %s",
            generation.id,
            MAX_PROVIDER_ATTEMPTS,
            last_error,
        )
        generation.fail(GENERIC_FAILURE_MESSAGE)
        await self._storage.update(generation)

    @staticmethod
    def _backoff_for(attempt: int) -> float:
        # Exponential in the attempt, plus jitter. Never waited after the last
        # attempt -- there is nothing left to wait for, and the caller is a
        # BackgroundTask whose time is the user's.
        return _RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)) + random.uniform(
            0, _RETRY_JITTER_SECONDS
        )
