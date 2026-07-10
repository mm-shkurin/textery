from datetime import datetime
from uuid import UUID

from adapters.generation_storage import GenerationStorage


class RequeueStaleGenerations:
    """Sweep usecase: resets generations stuck in pending/in_progress past a
    staleness threshold back to pending. Recovers stuck generations after a
    worker crash/restart, since BackgroundTasks is not durable across process
    boundaries. The application layer re-triggers execution for the returned
    ids; this usecase only owns the storage-state transition.
    """

    def __init__(self, storage: GenerationStorage) -> None:
        self._storage = storage

    async def execute(self, older_than: datetime) -> list[UUID]:
        stale = await self._storage.list_stale(older_than)
        requeued_ids: list[UUID] = []
        for generation in stale:
            generation.requeue()
            await self._storage.update(generation)
            requeued_ids.append(generation.id)
        return requeued_ids
