from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from model.document.document_model import DocumentModel
from project.project_item import ProjectItem
from project.project_page import ProjectPage, ProjectPageRequest

MISSING_OWNER_REFUSAL = (
    "list_feed requires a resolved owner_id: None would drop the owner predicate "
    "and read every account's rows"
)


class SqlAlchemyProjectFeedRepository:
    """The `ProjectFeedRepository` port, backed by one SQLAlchemy statement.

    See stories/12-my-projects/decisions/project-feed-read-model-decision.md.

    Documents arm only. The ADR's `UNION ALL` with the generations arm arrives
    with the scenario that first seeds a generation row (1.2/1.3); adding it now
    would ship an owner predicate no test exercises on a second table.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_feed(
        self,
        owner_id: UUID,
        # ARG002 noqa'd on the parameter, not on the file: `request` is the port's
        # pinned signature and is read from 1.2 onward (page, limit, sort, q).
        # Dropping it would break the port; a file-wide ignore would also silence a
        # genuinely dead parameter added later.
        request: ProjectPageRequest,  # noqa: ARG002
    ) -> ProjectPage:
        """The caller's feed, owner-scoped **in SQL**.

        The refusal comes first and is not a type-checker formality: SQLAlchemy
        compiles `where(col == None)` to `IS NULL`, so forwarding an unresolved
        owner would serve a well-formed, empty 200 rather than failing. The
        predicate is a WHERE clause, never an in-Python filter over an unfiltered
        select -- the latter passes every single-owner test while reading every
        account's rows on every request.
        """
        if owner_id is None:
            raise ValueError(MISSING_OWNER_REFUSAL)

        result = await self._session.execute(
            select(DocumentModel.id).where(DocumentModel.owner_id == owner_id)
        )
        # Built from the whole result set, not from a first row: an owner who owns
        # nothing is the path every new account hits first, and `scalar_one()` or
        # `rows[0]` would raise there instead of yielding an empty page.
        return ProjectPage(items=tuple(ProjectItem(id=row_id) for row_id in result.scalars()))
