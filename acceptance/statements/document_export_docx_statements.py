import io
import zipfile

from clients.application.dto.document.export_response_dto import ExportResponseDto
from statements.document_export_statements import (
    DOCX_CONTENT_TYPE,
    DocumentExportStatements,
)


class DocumentExportDocxStatements(DocumentExportStatements):
    """DOCX happy-path statements for Scenario 2.2 (a document exports as a valid DOCX).

    Subclasses DocumentExportStatements to reuse `_authenticated_access_token` and
    `_create_document_owned_by`. Kept in its own module so the base export statements
    file stays under the 200-line cap.
    """

    async def given_owner_exports_their_own_document_as_docx(self) -> ExportResponseDto:
        # The DOCX twin of given_owner_exports_their_own_document_as_pdf: the SAME
        # creation path, exported by the owner with export_format="docx".
        owner_access_token = await self._authenticated_access_token()
        own_document_id = await self._create_document_owned_by(owner_access_token)
        return await self._client.export_document(
            document_id=own_document_id,
            export_format="docx",
            access_token=owner_access_token,
        )

    def assert_valid_docx_attachment(self, response: ExportResponseDto) -> None:
        # A successful owner DOCX export delivers a real .docx, not the JSON
        # placeholder: 200, exact wordprocessingml content type, a ZIP local-file-header
        # signature (a DOCX is a ZIP), an attachment disposition, and no parsed JSON body.
        assert response.status_code == 200, (
            f"expected 200 exporting the owner's own document as docx, got "
            f"status_code={response.status_code}, body={response.body}"
        )
        assert response.content_type == DOCX_CONTENT_TYPE, (
            f"expected the exact docx content type {DOCX_CONTENT_TYPE!r}, got "
            f"content_type={response.content_type!r}"
        )
        assert response.content.startswith(b"PK\x03\x04"), (
            f"expected the body to start with the PK\\x03\\x04 ZIP signature of a valid "
            f"DOCX, got first bytes={response.content[:8]!r}"
        )
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
        assert response.content_disposition is not None and (
            response.content_disposition.strip().lower().startswith("attachment")
        ), (
            f"expected a Content-Disposition delivering the export as an attachment, got "
            f"content_disposition={response.content_disposition!r}"
        )
        assert response.body is None, (
            f"a DOCX export carries binary bytes, not a parsed JSON body — got {response.body!r}"
        )
