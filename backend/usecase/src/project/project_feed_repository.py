from typing import Protocol
from uuid import UUID

from project.project_page import ProjectPage, ProjectPageRequest


class ProjectFeedRepository(Protocol):
    """Port for the feed read model.

    One call, one snapshot -- `items` and (later) `total` must be read together, so
    this is a dedicated projection rather than a composition of DocumentRepository
    and GenerationStorage. See
    stories/12-my-projects/decisions/project-feed-read-model-decision.md.
    """

    async def list_feed(self, owner_id: UUID, request: ProjectPageRequest) -> ProjectPage:
        """The rows this owner owns, and no others.

        `owner_id` is REQUIRED and non-optional. An implementor must never turn a
        missing owner into an `owner_id IS NULL` predicate: that serves a
        well-formed, empty 200 to a caller whose identity could not be resolved,
        which the contract answers 401.
        """
        ...


class SearchSlots(Protocol):
    """Per-account concurrency permits for the feed's unindexed content scan.

    Injected now though nothing acquires one until 10.1: the acquire/release
    bracket must wrap every exit path of `execute`, and retrofitting it through a
    frozen constructor is exactly what the read-model decision set out to avoid.
    """

    async def acquire(self, owner_id: UUID) -> bool: ...

    async def release(self, owner_id: UUID) -> None: ...
