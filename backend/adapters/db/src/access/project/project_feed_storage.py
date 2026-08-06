from uuid import UUID

from sqlalchemy import Row, select
from sqlalchemy.ext.asyncio import AsyncSession

from model.document.document_model import DocumentModel
from project.project_item import ProjectItem
from project.project_page import ProjectPage, ProjectPageRequest

# The `kind` discriminator of the documents arm. A literal, and correctly so:
# there is no `documents.kind` column to read -- the value says which arm of the
# ADR's UNION ALL the row came from, and the generations arm will name its own.
_DOCUMENT_KIND = "document"

# A document is never retryable; only a failed generation is, and that column
# arrives with the generations arm (1.2/1.3). Named rather than inlined so the
# literal `False` in the row factory is not read as an oversight.
_DOCUMENTS_ARE_NEVER_RETRYABLE = False

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
            select(
                DocumentModel.id,
                DocumentModel.title,
                DocumentModel.content,
                DocumentModel.document_type,
                DocumentModel.status,
                DocumentModel.created_at,
                DocumentModel.updated_at,
            ).where(DocumentModel.owner_id == owner_id)
        )
        # Built from the whole result set, not from a first row: an owner who owns
        # nothing is the path every new account hits first, and `scalar_one()` or
        # `rows[0]` would raise there instead of yielding an empty page.
        return ProjectPage(items=tuple(_row_of(row) for row in result))


def _row_of(row: Row) -> ProjectItem:
    """One feed row, every field but the two arm discriminators read from SQL.

    `status` is the stored column rather than the domain's `DRAFT_STATUS`: the
    check constraint admits only `draft` today, so no test can yet tell a read
    from a hardcode -- but a projection that reads the column keeps telling the
    truth on the day the contract's `ready` arrives.

    `preview` is the content verbatim, and `''` rather than NULL for a document
    with none, because `documents.content` is NOT NULL and defaults to `''`. The
    200-code-point trim (6.2) and the markup strip (6.3) are not 1.1's to derive.
    """
    return ProjectItem(
        kind=_DOCUMENT_KIND,
        id=row.id,
        title=row.title,
        preview=row.content,
        document_type=row.document_type,
        status=row.status,
        retryable=_DOCUMENTS_ARE_NEVER_RETRYABLE,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
