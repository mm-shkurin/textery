from uuid import UUID

from adapters.generation_queue import GenerationQueue
from adapters.generation_storage import GenerationStorage

from generation.generation import Generation


class RequestGeneration:
    """Orchestrates submission of a new generation request.

    Scenario 1.1 scope: delegate field validation to the domain factory,
    letting ValidationException propagate uncaught.

    Scenario 2.1 scope: per the persist-and-enqueue architecture decision,
    a valid request is persisted via GenerationStorage.save() and then
    handed off to GenerationQueue.enqueue() before returning.
    """

    def __init__(self, storage: GenerationStorage, queue: GenerationQueue) -> None:
        self._storage = storage
        self._queue = queue

    async def execute(
        self,
        owner_id: UUID,
        topic: str | None,
        volume_pages: int | None,
        requirements: str | None,
        extra_wishes: str | None,
        document_type: str,
    ) -> Generation:
        generation = Generation.create(
            owner_id=owner_id,
            topic=topic,
            volume_pages=volume_pages,
            requirements=requirements,
            extra_wishes=extra_wishes,
            document_type=document_type,
        )
        await self._storage.save(generation)
        await self._queue.enqueue(generation.id)
        return generation
