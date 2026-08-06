from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from access.project.project_feed_storage import SqlAlchemyProjectFeedRepository
from container.runtime import request_scoped, stale_after_minutes
from project.list_projects import ListProjects
from shared.clock import SystemClock


class UnlimitedSearchSlots:
    """The `SearchSlots` port, granting every request a permit.

    A permit is required by `ListProjects`' frozen constructor but acquired by
    nobody until scenario 10.1 adds the unindexed content scan that needs
    throttling. Granting unconditionally is what the code does today anyway --
    shipping a real per-account limiter now would put an unasserted concurrency
    bound in production. The backend runs as multiple instances, so the eventual
    limiter cannot be an in-memory counter here; it will be database-backed.
    """

    async def acquire(self, owner_id: UUID) -> bool:  # noqa: ARG002
        return True

    async def release(self, owner_id: UUID) -> None:  # noqa: ARG002
        return None


@request_scoped
def create_list_projects(session: AsyncSession) -> ListProjects:
    # The same threshold the stale sweep runs on, read from the same place: the
    # feed's `recovering` label and the sweep's requeue must agree about which
    # rows are stale, or the feed offers a retry on work the sweep is re-running.
    stale_after = timedelta(minutes=stale_after_minutes())
    return ListProjects(
        project_feed_repository=SqlAlchemyProjectFeedRepository(
            session, stale_after=stale_after, clock=SystemClock()
        ),
        search_slots=UnlimitedSearchSlots(),
        clock=SystemClock(),
    )
