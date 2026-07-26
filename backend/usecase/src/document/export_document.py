from uuid import UUID

from document.document_renderer import DocumentRenderer
from document.document_repository import DocumentRepository
from document.export_format import ExportFormat
from document.rendered_export import RenderedExport

# Media type per target format, keyed by the enum so a new format (docx, Sc 2.2)
# is a one-line addition here rather than a branch. An unmapped format would
# KeyError loudly rather than silently serving the wrong Content-Type.
_MEDIA_TYPE: dict[ExportFormat, str] = {
    ExportFormat.PDF: "application/pdf",
}


class ExportDocument:
    """Render one of the caller's own documents to PDF/DOCX."""

    def __init__(
        self, document_repository: DocumentRepository, document_renderer: DocumentRenderer
    ) -> None:
        self.document_repository = document_repository
        self.document_renderer = document_renderer

    async def execute(
        self, document_id: UUID, owner_id: UUID, format: str | None
    ) -> RenderedExport | None:
        # Validate the format before the owner-scoped fetch so a bad format is
        # refused regardless of whether the target document exists -- it discloses
        # nothing about the document.
        export_format = ExportFormat.parse(format)
        # Absent and foreign collapse to the same None (owner-scoped SQL), mirroring
        # GetDocument. A refused request never reaches the render step.
        document = await self.document_repository.find_by_id_and_owner(document_id, owner_id)
        if document is None:
            return None
        content = self.document_renderer.render(document.content, export_format)
        return RenderedExport(content=content, media_type=_MEDIA_TYPE[export_format])
