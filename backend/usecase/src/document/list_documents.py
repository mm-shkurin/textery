from uuid import UUID

from document.document_filter import EMPTY, DocumentFilter
from document.document_repository import DocumentRepository
from shared.page import DEFAULT_LIMIT, Page, PageRequest


class ListDocuments:
    """The caller's own document history, newest first.

    Newest *created*, not newest *edited*: the keyset anchor must be immutable, or
    a row can move across the cursor mid-paging and be served twice or skipped.
    See KeysetCursor.
    """

    def __init__(self, document_repository: DocumentRepository) -> None:
        self._document_repository = document_repository

    async def execute(
        self,
        owner_id: UUID,
        limit: int = DEFAULT_LIMIT,
        cursor: str | None = None,
        document_filter: DocumentFilter = EMPTY,
    ) -> Page:
        """One page of history, optionally narrowed by search text and a date window.

        The filter travels WITH the cursor rather than being applied after the
        page is read: filtering a fetched page would return fewer than `limit`
        rows while still reporting a next cursor, so «поиск по истории» would
        show two matches on a screen that had ten pages of them.

        It is a `DocumentFilter`, already parsed and validated, not three raw
        strings — the rules (blank query is absent, an inverted window is a
        refusal) are asked once at the edge, so this usecase and the storage
        below it cannot disagree about them.
        """
        request = PageRequest(limit=limit, cursor=cursor)
        rows = await self._document_repository.list_by_owner(
            owner_id, request.fetch_size, request.cursor, document_filter
        )
        return Page.of(rows, request.limit)
