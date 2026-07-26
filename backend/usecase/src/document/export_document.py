from uuid import UUID

from document.document import Document
from document.document_repository import DocumentRepository
from document.export_format import ExportFormat


class ExportDocument:
    """Fetch one of the caller's own documents for export to PDF/DOCX."""

    def __init__(self, document_repository: DocumentRepository) -> None:
        self.document_repository = document_repository

    async def execute(
        self, document_id: UUID, owner_id: UUID, format: str | None
    ) -> Document | None:
        # Validate the format before the owner-scoped fetch so a bad format is
        # refused regardless of whether the target document exists -- it discloses
        # nothing about the document.
        ExportFormat.parse(format)
        # Returns None rather than raising, mirroring GetDocument: absent and foreign
        # collapse to the same None because the repository filters on owner_id in SQL.
        return await self.document_repository.find_by_id_and_owner(document_id, owner_id)
