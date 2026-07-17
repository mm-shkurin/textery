from typing import Optional
from uuid import UUID

from adapters.generation_storage import GenerationStorage
from shared.page import DEFAULT_LIMIT, Page, PageRequest


class ListGenerations:
    """The caller's own generation history, newest first.

    Pagination lives in PageRequest/Page, shared with ListDocuments: the two
    histories are the same read with a different table, and duplicating the
    limit bounds or the has-next probe would let them drift.
    """

    def __init__(self, storage: GenerationStorage) -> None:
        self._storage = storage

    async def execute(
        self, owner_id: UUID, limit: int = DEFAULT_LIMIT, cursor: Optional[str] = None
    ) -> Page:
        request = PageRequest(limit=limit, cursor=cursor)
        rows = await self._storage.list_by_owner(owner_id, request.fetch_size, request.cursor)
        return Page.of(rows, request.limit)
