from datetime import timedelta
from uuid import UUID

from sqlalchemy import Row, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from access.project.project_feed_query import feed_subquery, order_by
from project.project_item import ProjectItem
from project.project_page import ProjectPage, ProjectPageRequest
from project.project_preview import derive_preview
from project.project_status import (
    DOCUMENT_KIND,
    generation_feed_status,
    generation_is_retryable,
)
from shared.clock import Clock, SystemClock

# A document is never retryable; only a failed generation is. Named rather than
# inlined so the literal `False` in the row factory is not read as an oversight.
_DOCUMENTS_ARE_NEVER_RETRYABLE = False

MISSING_OWNER_REFUSAL = (
    "list_feed requires a resolved owner_id: None would drop the owner predicate "
    "and read every account's rows"
)


class SqlAlchemyProjectFeedRepository:
    """The `ProjectFeedRepository` port, backed by one merged SQL projection.

    See stories/12-my-projects/decisions/project-feed-read-model-decision.md.

    The clock is the adapter's because the stale label is a property of the row
    as *read*: `items` and `total` come from one snapshot, and the recovering
    boundary must be evaluated against that same instant.
    """

    def __init__(
        self,
        session: AsyncSession,
        stale_after: timedelta = timedelta(minutes=10),
        clock: Clock | None = None,
    ) -> None:
        self._session = session
        self._stale_after = stale_after
        self._clock = clock or SystemClock()

    async def list_feed(self, owner_id: UUID, request: ProjectPageRequest) -> ProjectPage:
        """The caller's feed, owner-scoped **in SQL**.

        The refusal comes first and is not a type-checker formality: SQLAlchemy
        compiles `where(col == None)` to `IS NULL`, so forwarding an unresolved
        owner would serve a well-formed, empty 200 rather than failing.

        `total` is counted over the same subquery as the page and inside the same
        transaction, so the two describe one snapshot. It is not `len(items)`,
        which under offset paging is the size of the window rather than of the set.
        """
        if owner_id is None:
            raise ValueError(MISSING_OWNER_REFUSAL)

        feed = feed_subquery(owner_id, request.query)
        total = await self._session.scalar(select(func.count()).select_from(feed))
        rows = await self._session.execute(
            select(feed)
            .order_by(*order_by(feed, request.sort))
            .limit(request.limit)
            .offset(request.offset)
        )
        now = self._clock.now()
        return ProjectPage(
            items=tuple(self._item_of(row, now) for row in rows),
            page=request.page,
            limit=request.limit,
            total=total or 0,
        )

    def _item_of(self, row: Row, now) -> ProjectItem:
        """One feed row, projected from whichever arm produced it.

        `status` and `retryable` are derived here rather than in the query
        because the recovering rule is a comparison against an injected clock,
        and pushing it into SQL would make the boundary depend on the database's
        idea of `now()` instead of the application's.
        """
        is_document = row.kind == DOCUMENT_KIND
        status = (
            row.status
            if is_document
            else generation_feed_status(row.status, row.updated_at, now, self._stale_after)
        )
        return ProjectItem(
            kind=row.kind,
            id=row.id,
            title=row.title,
            preview=derive_preview(row.preview_source),
            document_type=row.document_type,
            status=status,
            retryable=(
                _DOCUMENTS_ARE_NEVER_RETRYABLE if is_document else generation_is_retryable(status)
            ),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
