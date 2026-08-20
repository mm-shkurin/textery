import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from uuid import UUID

from generation.generation import Generation
from generation.generation_provider import GenerationProvider
from generation.generation_storage import GenerationStorage
from generation.prompt_template import PromptBuildError, PromptRequest, build_prompt

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


def _compose_prompt(generation: Generation) -> str:
    """Composed here, at the call site, and not inside the provider.

    Placement is the guard: a build nested in `GenerationProvider.generate` means
    the provider was called before the request could be refused. The refusal
    happens here, once, before the retry loop — and since scenario 2.1 the result
    is also what the provider is handed, so this is the only composer there is.
    """
    return build_prompt(
        PromptRequest(
            document_type=generation.document_type,
            topic=generation.topic,
            volume_pages=generation.volume_pages,
            requirements=generation.requirements,
            extra_wishes=generation.extra_wishes,
            text_style=generation.text_style,
        )
    )


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

        try:
            prompt = _compose_prompt(generation)
        except PromptBuildError as error:
            # Before the loop, and never inside it. A build failure is deterministic
            # -- attempt 2 phrases the identical request from the identical row --
            # so the catch-all below would spend the whole retry budget and a
            # backoff on a value that cannot change, and bill the provider for a
            # request that cannot be phrased. Terminal on the first failure instead.
            logger.error("generation %s cannot be phrased as a prompt: %s", generation.id, error)
            await self._fail_terminally(generation)
            return

        last_error: Exception | None = None
        for attempt in range(1, MAX_PROVIDER_ATTEMPTS + 1):
            try:
                content = await self._provider.generate(prompt)
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
        await self._fail_terminally(generation)

    async def _fail_terminally(self, generation: Generation) -> None:
        # The row's last write, shared by both terminal paths -- an unphraseable
        # prompt and an exhausted attempt budget. What differs between them is the
        # log line, which each caller keeps; what must not differ is the state the
        # user is left in, so the message and the persist live in one place.
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
