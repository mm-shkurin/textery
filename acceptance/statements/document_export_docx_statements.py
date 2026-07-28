import io
import zipfile

from clients.application.dto.document.export_response_dto import ExportResponseDto
from statements.document_export_statements import DocumentExportStatements
from statements.export_envelope import assert_export_attachment


class DocumentExportDocxStatements(DocumentExportStatements):
    """DOCX happy-path statements for Scenario 2.2 (a document exports as a valid DOCX).

    Subclasses DocumentExportStatements to reuse `_authenticated_access_token` and
    `_create_document_owned_by`. Kept in its own module so the base export statements
    file stays under the 200-line cap.
    """

    async def given_owner_exports_their_own_document_as_docx(self) -> ExportResponseDto:
        # The DOCX twin of given_owner_exports_their_own_document_as_pdf: the SAME
        # creation path, exported by the owner with export_format="docx".
        return await self._owner_exports_fresh_document("docx")

    def assert_valid_docx_attachment(self, response: ExportResponseDto) -> None:
        # A successful owner DOCX export delivers a real .docx, not the JSON
        # placeholder: 200, exact wordprocessingml content type, a ZIP local-file-header
        # signature (a DOCX is a ZIP), an attachment disposition, and no parsed JSON body.
        assert_export_attachment(response, "docx")
        # PK magic alone passes for ANY zip (empty archive, renamed file, a docx
        # missing its OOXML parts). Open the bytes and require the two mandatory
        # OOXML parts so a bare/corrupt zip that Word reports as damaged cannot
        # ship green (red-acceptance premortem carry-forward).
        try:
            with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                names = archive.namelist()
        except zipfile.BadZipFile as error:  # pragma: no cover - defensive
            raise AssertionError(
                f"the DOCX body is not a readable ZIP archive: {error}"
            ) from error
        assert "[Content_Types].xml" in names and "word/document.xml" in names, (
            f"expected the mandatory OOXML parts [Content_Types].xml and "
            f"word/document.xml in the docx, got members={names!r}"
        )
