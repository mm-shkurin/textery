import logging
from datetime import datetime
from uuid import UUID

from generation.generation_storage import GenerationStorage
from shared.exceptions import ConflictException, NotFoundException

logger = logging.getLogger(__name__)


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
            try:
                await self._storage.update(generation)
            except (ConflictException, NotFoundException):
                # Losing a row is the normal outcome, not an error. The sweep runs
                # in every replica's lifespan, so two instances routinely list the
                # same stale row and race to claim it; the CAS in the storage is
                # what makes exactly one win, and this is the loser being told so.
                # A row deleted between the list and the update reads the same way.
                #
                # Caught per row rather than around the loop, because the loop is a
                # batch of independent claims. Letting it propagate aborted the
                # whole sweep at the first contested row and left every later one
                # stranded for another interval -- and with several replicas, an
                # early conflict is likely, so the sweep would rarely finish. It
                # surfaced only as "stale generation sweep failed" in the lifespan
                # logger, which reads like a malfunction rather than two instances
                # doing exactly what they should.
                logger.debug(
                    "generation %s already claimed by another sweep or gone; skipping",
                    generation.id,
                )
                continue
            requeued.append((generation.id, generation.owner_id))
        return requeued
