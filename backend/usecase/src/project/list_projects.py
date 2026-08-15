from uuid import UUID

from project.project_feed_repository import ProjectFeedRepository, SearchSlots
from project.project_page import ProjectPage, ProjectPageRequest
from shared.clock import Clock
from shared.exceptions import ValidationException


class ListProjects:
    """The caller's own feed: their documents, plus generations no document links to.

    `clock` is injected though nothing reads it until 1.5, and `search_slots`
    though nothing acquires one until 10.1 -- see the read-model decision for why
    the constructor is frozen with both from the start.
    """

    def __init__(
        self,
        project_feed_repository: ProjectFeedRepository,
        search_slots: SearchSlots,
        clock: Clock,
    ) -> None:
        self._project_feed_repository = project_feed_repository
        self._search_slots = search_slots
        self._clock = clock

    async def execute(self, owner_id: UUID, request: ProjectPageRequest) -> ProjectPage:
        # Fail closed before the port is touched: an unresolved owner must never
        # become an unscoped read served back as a well-formed empty page. The
        # refusal says nothing about *why* the owner could not be resolved.
        if owner_id is None:
            raise ValidationException(
                message="Authentication is required to view your projects.",
                error_code="UNAUTHENTICATED",
            )
        return await self._project_feed_repository.list_feed(owner_id, request)
