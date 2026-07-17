from typing import Optional
from uuid import UUID

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
        self, owner_id: UUID, limit: int = DEFAULT_LIMIT, cursor: Optional[str] = None
    ) -> Page:
        request = PageRequest(limit=limit, cursor=cursor)
        rows = await self._document_repository.list_by_owner(
            owner_id, request.fetch_size, request.cursor
        )
        return Page.of(rows, request.limit)
