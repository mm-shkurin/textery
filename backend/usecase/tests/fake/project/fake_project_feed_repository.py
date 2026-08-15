from uuid import UUID

from project.project_item import ProjectItem
from project.project_page import ProjectPage, ProjectPageRequest


class FakeProjectFeedRepository:
    """In-memory feed projection, owner-scoped like the real statement.

    The owner predicate is mirrored rather than simplified away, for the reason
    FakeDocumentRepository records: a fake that returned everything it holds would
    let every ownership test pass against a projection that leaks.

    Calls are recorded so a test can assert the port was *not* reached -- an
    unresolved owner must never reach the statement at all.
    """

    def __init__(self) -> None:
        self.items_by_owner: dict[UUID, list[ProjectItem]] = {}
        self.calls: list[tuple[UUID, ProjectPageRequest]] = []

    def seed(self, owner_id: UUID, *items: ProjectItem) -> None:
        self.items_by_owner.setdefault(owner_id, []).extend(items)

    async def list_feed(self, owner_id: UUID, request: ProjectPageRequest) -> ProjectPage:
        # The port's contract, enforced rather than documented: a missing owner is
        # never an unscoped read here, so a usecase that forwards None fails loudly
        # instead of being handed somebody else's rows -- or an empty 200.
        if owner_id is None:
            raise AssertionError("list_feed was called without a resolved owner_id")
        self.calls.append((owner_id, request))
        return ProjectPage(items=tuple(self.items_by_owner.get(owner_id, [])))


class FakeSearchSlots:
    """Always grants the permit.

    Scenario 1.1 asserts nothing about slots, so nothing is recorded here yet:
    unread bookkeeping in a fake reads as coverage that does not exist. The
    acquire/release bracket is asserted from 10.1, and that work unit adds the
    recording alongside the assertion that reads it.
    """

    async def acquire(self, owner_id: UUID) -> bool:  # noqa: ARG002 -- ProjectFeedRepository port shape
        return True

    async def release(self, owner_id: UUID) -> None:  # noqa: ARG002 -- ProjectFeedRepository port shape
        return None
