from uuid import UUID

from document.idempotency_key import IdempotencyKey
from generation.generation import FAILED_STATUS, Generation
from generation.generation_queue import GenerationQueue
from generation.generation_storage import GenerationStorage
from shared.exceptions import NotFoundException, ValidationException

# Retries of ONE source generation. The fresh-key rule that keeps the button
# alive after a second failure also means idempotency bounds nothing here, and
# this is the one path in the story that spends money on every press.
RETRY_CEILING = 5

NOT_RETRYABLE_MESSAGE = "This generation cannot be retried in its current state."
RETRY_LIMIT_MESSAGE = "This generation has been retried too many times."
INVALID_KEY_MESSAGE = "Idempotency-Key is required and must be at most 128 characters."


class RetryGeneration:
    """Re-run a failed generation from its own stored parameters.

    A top-level operation of its own, and deliberately not a call into
    `RequestGeneration`: chaining usecases would hide the call graph from the
    controller and drag that usecase's client-supplied parameters into a path
    whose whole point is that it reads none.

    The two overrides are the only client-supplied values on this path besides
    the key, and they are passed straight through to `Generation.retry_of`
    rather than merged here: whether an absent override means "keep the source's
    value" is the entity's rule, not this usecase's, and a second copy of it here
    is how the two answers drift.
    """

    def __init__(self, storage: GenerationStorage, queue: GenerationQueue) -> None:
        self._storage = storage
        self._queue = queue

    async def execute(
        self,
        generation_id: UUID,
        owner_id: UUID,
        idempotency_key: str | None,
        text_style: str | None = None,
        volume_pages: int | None = None,
    ) -> tuple[Generation, bool]:
        """Returns the retry and whether THIS call created it.

        The flag is not decoration. The queue port is a no-op today and the real
        trigger is the route's background task, so a replay that returned only
        the row would have the caller start a second run of work the first call
        already started -- the exact duplicate the idempotency key exists to
        prevent.
        """
        key = self._validated_key(idempotency_key)
        replayed = await self._replayed_retry(owner_id, key, generation_id)
        if replayed is not None:
            return replayed, False

        source = await self._retryable_source(generation_id, owner_id)
        retry = Generation.retry_of(
            source,
            idempotency_key=key,
            text_style=text_style,
            volume_pages=volume_pages,
        )
        await self._persist_and_enqueue(retry)
        return retry, True

    async def _persist_and_enqueue(self, retry: Generation) -> None:
        """Saved before enqueued, in that order.

        A crash between the two then leaves a row the sweep can requeue rather
        than a job naming a generation that does not exist.
        """
        await self._storage.save(retry)
        await self._queue.enqueue(retry.id)

    async def _replayed_retry(
        self, owner_id: UUID, key: str, generation_id: UUID
    ) -> Generation | None:
        """The retry this key already created, if it did.

        The key is resolved BEFORE the source is read, and scoped to the owner.
        A replay must answer with the row the first attempt created even if the
        source has since changed state -- otherwise a client whose response was
        lost is told 409 for work it already successfully started.
        """
        replayed = await self._storage.find_by_owner_and_idempotency_key(owner_id, key)
        if replayed is not None and replayed.source_generation_id != generation_id:
            # The same key against a different source is a client bug, not a
            # replay. Answering with the first generation would silently give
            # them a run of something they did not ask for.
            raise ValidationException(
                message="This idempotency key was already used for another generation.",
                error_code="IDEMPOTENCY_KEY_REUSED",
            )
        return replayed

    async def _retryable_source(self, generation_id: UUID, owner_id: UUID) -> Generation:
        """The owner's generation, proven to be one a retry may be built from."""
        source = await self._storage.get_by_id_and_owner(generation_id, owner_id)
        if source is None:
            # Absent and foreign are one answer: the storage filters on owner_id
            # in SQL, so this branch cannot tell them apart, and the client must
            # not be able to either.
            raise NotFoundException(f"generation {generation_id} not found")

        if source.status != FAILED_STATUS:
            # Only `failed`. A pending or in-progress row is still alive -- the
            # stale sweep requeues it -- and retrying there runs one piece of work
            # twice: two documents, two model bills.
            raise ValidationException(message=NOT_RETRYABLE_MESSAGE, error_code="NOT_RETRYABLE")

        if await self._storage.count_retries_of(generation_id) >= RETRY_CEILING:
            raise ValidationException(message=RETRY_LIMIT_MESSAGE, error_code="RETRY_LIMIT_REACHED")
        return source

    @staticmethod
    def _validated_key(raw: str | None) -> str:
        if raw is None:
            raise ValidationException(
                message=INVALID_KEY_MESSAGE, error_code="INVALID_IDEMPOTENCY_KEY"
            )
        try:
            return IdempotencyKey(raw).value
        except ValueError:
            raise ValidationException(
                message=INVALID_KEY_MESSAGE, error_code="INVALID_IDEMPOTENCY_KEY"
            ) from None
