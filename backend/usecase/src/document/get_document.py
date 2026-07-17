from typing import Optional
from uuid import UUID

from document.document import Document
from document.document_repository import DocumentRepository


class GetDocument:
    """Fetch one of the caller's own documents (reopen for editing)."""

    def __init__(self, document_repository: DocumentRepository) -> None:
        self.document_repository = document_repository

    async def execute(self, document_id: UUID, owner_id: UUID) -> Optional[Document]:
        # Returns None rather than raising, matching GetGeneration: the router turns
        # it into a 404. Absent and foreign collapse into the same None here because
        # the repository filters on owner_id in SQL -- there is no branch that could
        # tell them apart, which is the point.
        return await self.document_repository.find_by_id_and_owner(document_id, owner_id)
