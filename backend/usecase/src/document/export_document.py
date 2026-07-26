from uuid import UUID

from document.document import Document
from document.document_repository import DocumentRepository


class ExportDocument:
    """Fetch one of the caller's own documents for export to PDF/DOCX."""

    def __init__(self, document_repository: DocumentRepository) -> None:
        self.document_repository = document_repository

    async def execute(self, document_id: UUID, owner_id: UUID) -> Document | None:
        raise NotImplementedError
