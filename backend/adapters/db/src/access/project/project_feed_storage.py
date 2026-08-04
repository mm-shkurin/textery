from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from project.project_page import ProjectPage, ProjectPageRequest


class SqlAlchemyProjectFeedRepository:
    """The `ProjectFeedRepository` port, backed by one SQLAlchemy statement.

    See stories/12-my-projects/decisions/project-feed-read-model-decision.md.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_feed(self, owner_id: UUID, request: ProjectPageRequest) -> ProjectPage:
        raise NotImplementedError()
