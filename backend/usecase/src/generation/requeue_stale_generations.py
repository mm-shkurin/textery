from datetime import datetime
from uuid import UUID

from adapters.generation_storage import GenerationStorage


class RequeueStaleGenerations:
    """Sweep usecase: resets generations stuck in pending/in_progress past a
    staleness threshold back to pending. Recovers stuck generations after a
    worker crash/restart, since BackgroundTasks is not durable across process
    boundaries. The application layer re-triggers execution for the returned
    ids; this usecase only owns the storage-state transition.

    The sweep is cross-owner by nature -- it recovers every stuck row regardless of
    who requested it -- so it reads through `list_stale`, not the owner-filtered
    by-id read. It returns `(id, owner_id)` pairs because the re-trigger it feeds
    does need the owner to locate the row again.
    """

    def __init__(self, storage: GenerationStorage) -> None:
        self._storage = storage

    async def execute(self, older_than: datetime) -> list[tuple[UUID, UUID]]:
        stale = await self._storage.list_stale(older_than)
        requeued: list[tuple[UUID, UUID]] = []
        for generation in stale:
            generation.requeue()
            await self._storage.update(generation)
            requeued.append((generation.id, generation.owner_id))
        return requeued
