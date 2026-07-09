from typing import Optional

from adapters.generation_queue import GenerationQueue
from adapters.generation_storage import GenerationStorage
from generation.generation import Generation


class RequestGeneration:
    """Orchestrates submission of a new generation request.

    Scenario 1.1 scope: delegate field validation to the domain factory,
    letting ValidationException propagate uncaught.

    Scenario 2.1 scope: constructor now takes the storage and queue ports
    per the persist-and-enqueue architecture decision. execute() still only
    delegates to Generation.create() -- persisting and enqueueing are wired
    in green-usecase, once Generation.create() itself generates id/status/
    created_at (it currently still raises NotImplementedError for a valid
    topic).
    """

    def __init__(self, storage: GenerationStorage, queue: GenerationQueue) -> None:
        self._storage = storage
        self._queue = queue

    async def execute(
        self,
        topic: Optional[str],
        volume_pages: Optional[int],
        requirements: Optional[str],
        extra_wishes: Optional[str],
        document_type: str,
    ) -> Generation:
        return Generation.create(
            topic=topic,
            volume_pages=volume_pages,
            requirements=requirements,
            extra_wishes=extra_wishes,
            document_type=document_type,
        )
