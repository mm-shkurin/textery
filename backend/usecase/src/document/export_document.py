from uuid import UUID

from document.document import Document
from document.document_renderer import DocumentRenderer
from document.document_repository import DocumentRepository
from document.export_format import ExportFormat
from document.rendered_export import RenderedExport


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
        return RenderedExport(
            content=content,
            export_format=export_format,
            filename=self._derive_filename(document, export_format),
        )

    @staticmethod
    def _derive_filename(document: Document, export_format: ExportFormat) -> str:
        """The plain filename: title stem when present, else the default "document".

        The extension IS the ExportFormat value (pdf/docx), so it cannot drift from
        the format that drove the render. RFC 5987 encoding is the rest adapter's
        concern -- this stays plain unicode.

        The strip is DEFENSE IN DEPTH and belongs to the FILENAME ONLY: the save
        boundary only governs writes made through it, so a row written by a
        migration, an import, an admin tool, or before the blank-title green can
        still carry "   " or " Отчёт ". Derivation is where "never empty" is
        enforceable for every input. The stored entity is NOT rewritten -- see
        decisions/blank-title-semantics-decision.md.
        """
        stem = (document.title or "").strip() or "document"
        return f"{stem}.{export_format.value}"
