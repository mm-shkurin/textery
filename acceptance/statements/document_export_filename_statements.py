from typing import ClassVar

from clients.application.dto.document.export_response_dto import ExportResponseDto
from statements.document_export_statements import DocumentExportStatements

# A freshly created document is born at version 1 (Document.create hardcodes
# version=1), so the first save must present 1 as its optimistic-lock token.
CREATED_DOCUMENT_VERSION = 1
# The editor body saved alongside the title. Kept small and well under the content
# cap; the filename scenario asserts on the header, not on this content.
DOCUMENT_CONTENT = "Тело документа"


class DocumentExportFilenameStatements(DocumentExportStatements):
    """Scenario 3.1 statements — the attachment filename is derived from a Cyrillic
    title and RFC 5987-encoded.

    Subclasses DocumentExportStatements to reuse `_authenticated_access_token` and
    `_create_document_owned_by`, and lives in its own module so the base export
    statements file stays under the 200-line cap.
    """

    # A title with Cyrillic letters and a space — the space is not an RFC 5987
    # attr-char, so it must be percent-encoded (%20), not passed through or turned
    # into '+'.
    CYRILLIC_TITLE: ClassVar[str] = "Привет Мир"
    # The exact Content-Disposition the export must return for CYRILLIC_TITLE on the
    # pdf path: filename*=UTF-8'' followed by the percent-encoded UTF-8 bytes of
    # "Привет Мир" and the .pdf extension. Pinned as a literal (no runtime encoding
    # in the test) — %D0%9F… are the UTF-8 bytes of the Cyrillic letters, %20 the
    # space.
    EXPECTED_CONTENT_DISPOSITION: ClassVar[str] = (
        "attachment; "
        "filename*=UTF-8''%D0%9F%D1%80%D0%B8%D0%B2%D0%B5%D1%82%20%D0%9C%D0%B8%D1%80.pdf"
    )

    async def given_owner_exports_document_with_cyrillic_title_as_pdf(
        self,
    ) -> ExportResponseDto:
        access_token = await self._authenticated_access_token()
        document_id = await self._create_document_owned_by(access_token)
        save = await self._client.save_document(
            document_id=document_id,
            content=DOCUMENT_CONTENT,
            version=CREATED_DOCUMENT_VERSION,
            access_token=access_token,
            title=self.CYRILLIC_TITLE,
        )
        assert save.status_code == 200, (
            f"setup: expected the title-bearing save to succeed with 200, got "
            f"status_code={save.status_code}, body={save.body}"
        )
        return await self._client.export_document(
            document_id=document_id,
            export_format="pdf",
            access_token=access_token,
        )

    def assert_filename_rfc5987_encoded_from_title(
        self, response: ExportResponseDto
    ) -> None:
        # The whole Content-Disposition header is pinned to the exact RFC 5987 form.
        # A substring check would pass for a raw or mojibake filename; exact equality
        # is what proves the title was UTF-8 percent-encoded and reflected verbatim.
        assert response.status_code == 200, (
            f"expected 200 exporting a titled document as pdf, got "
            f"status_code={response.status_code}, body={response.body}"
        )
        assert response.content_disposition == self.EXPECTED_CONTENT_DISPOSITION, (
            f"expected the attachment filename to be the RFC 5987-encoded title "
            f"{self.EXPECTED_CONTENT_DISPOSITION!r}, got "
            f"content_disposition={response.content_disposition!r}"
        )
