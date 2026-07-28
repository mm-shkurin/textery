from dataclasses import dataclass
from typing import ClassVar, Optional

from clients.application.dto.document.export_response_dto import ExportResponseDto
from statements.document_export_statements import (
    DOCX_CONTENT_TYPE,
    PDF_CONTENT_TYPE,
    DocumentExportStatements,
)

# A freshly created document is born at version 1 (Document.create hardcodes
# version=1), so the first save must present 1 as its optimistic-lock token.
CREATED_DOCUMENT_VERSION = 1
# The editor body saved alongside the title. Kept small and well under the content
# cap; the filename scenario asserts on the header, not on this content.
DOCUMENT_CONTENT = "Тело документа"
# The exact content type each export format must return — pinned so a docx export
# can never ship pdf bytes (or a pdf content type) under a .docx filename.
CONTENT_TYPE_BY_FORMAT = {"pdf": PDF_CONTENT_TYPE, "docx": DOCX_CONTENT_TYPE}
# The leading magic bytes of each format: %PDF- for PDF, the PK zip local-file
# header for DOCX (an OOXML package is a zip).
CONTENT_SIGNATURE_BY_FORMAT = {"pdf": b"%PDF-", "docx": b"PK\x03\x04"}


@dataclass(frozen=True)
class ExpectedExportEnvelope:
    """The deterministic part of a successful export response — everything except the
    generated document bytes. A frozen dataclass compares all fields at once, so one
    equality pins status, content type, filename header and the absence of a JSON body
    together rather than leaving unasserted fields free to regress."""

    status_code: int
    content_type: str
    content_disposition: str
    body: Optional[dict]


def _envelope_of(response: ExportResponseDto) -> ExpectedExportEnvelope:
    return ExpectedExportEnvelope(
        status_code=response.status_code,
        content_type=response.content_type,
        content_disposition=response.content_disposition,
        body=response.body,
    )


class DocumentExportFilenameStatements(DocumentExportStatements):
    """Scenario 3.1/3.2 statements — the attachment filename is derived from the title
    (RFC 5987-encoded), and falls back to a defined default when there is no title.

    Subclasses DocumentExportStatements to reuse `_authenticated_access_token` and
    `_create_document_owned_by`, and lives in its own module so the base export
    statements file stays under the 200-line cap.
    """

    # A title with Cyrillic letters and a space — the space is not an RFC 5987
    # attr-char, so it must be percent-encoded (%20), not passed through or turned
    # into '+'.
    CYRILLIC_TITLE: ClassVar[str] = "Привет Мир"
    # The exact Content-Disposition the export must return for CYRILLIC_TITLE on the
    # pdf path. Pinned as a literal (no runtime encoding in the test) — %D0%9F… are
    # the UTF-8 bytes of the Cyrillic letters, %20 the space.
    EXPECTED_CONTENT_DISPOSITION: ClassVar[str] = (
        "attachment; "
        "filename*=UTF-8''%D0%9F%D1%80%D0%B8%D0%B2%D0%B5%D1%82%20%D0%9C%D0%B8%D1%80.pdf"
    )
    # The defined default attachment filename for a document that carries no title,
    # per export format: the stem is the constant "document" and the extension follows
    # the requested format. RFC 5987 form even for the pure-ASCII default, because the
    # route always emits filename*=UTF-8''.
    EXPECTED_DEFAULT_CONTENT_DISPOSITION: ClassVar[dict[str, str]] = {
        "pdf": "attachment; filename*=UTF-8''document.pdf",
        "docx": "attachment; filename*=UTF-8''document.docx",
    }
    # The version a document carries after exactly one successful save (created at
    # version 1, each save bumps it), so a second save presents 2 as its lock token.
    ONCE_SAVED_DOCUMENT_VERSION: ClassVar[int] = 2

    async def _document_carrying_the_cyrillic_title(self) -> tuple[str, str]:
        # Arrange shared by the titled-export and blank-title-overwrite cases: an
        # authenticated owner with a document whose stored title is CYRILLIC_TITLE.
        access_token = await self._authenticated_access_token()
        document_id = await self._create_document_owned_by(access_token)
        save = await self._client.save_document(
            document_id=document_id,
            content=DOCUMENT_CONTENT,
            version=CREATED_DOCUMENT_VERSION,
            access_token=access_token,
            title=self.CYRILLIC_TITLE,
        )
        self._assert_setup_save_succeeded(save, "title-bearing")
        return access_token, document_id

    @staticmethod
    def _assert_setup_save_succeeded(save, described_as: str) -> None:
        assert save.status_code == 200, (
            f"setup: expected the {described_as} save to succeed with 200, got "
            f"status_code={save.status_code}, body={save.body}"
        )

    async def given_owner_exports_document_with_cyrillic_title_as_pdf(
        self,
    ) -> ExportResponseDto:
        access_token, document_id = await self._document_carrying_the_cyrillic_title()
        return await self._client.export_document(
            document_id=document_id,
            export_format="pdf",
            access_token=access_token,
        )

    async def given_owner_exports_untitled_document(
        self, export_format: str
    ) -> ExportResponseDto:
        # A freshly created document is born with no title at all (Document.create
        # takes no title and the create API accepts only document_type), so this is
        # the persisted-null path end to end -- nothing ever writes documents.title.
        access_token = await self._authenticated_access_token()
        document_id = await self._create_document_owned_by(access_token)
        return await self._client.export_document(
            document_id=document_id,
            export_format=export_format,
            access_token=access_token,
        )

    async def given_owner_saves_a_blank_title_over_a_stored_title_and_exports(
        self, blank_title: str
    ) -> ExportResponseDto:
        # A client autosave that submits a blank title (empty or whitespace-only)
        # carries no title intent -- exactly like omitting the field. It must
        # therefore leave the previously stored title untouched, so the export
        # filename still reflects it.
        access_token, document_id = await self._document_carrying_the_cyrillic_title()
        blank_save = await self._client.save_document(
            document_id=document_id,
            content=DOCUMENT_CONTENT,
            version=self.ONCE_SAVED_DOCUMENT_VERSION,
            access_token=access_token,
            title=blank_title,
        )
        self._assert_setup_save_succeeded(blank_save, "blank-title")
        return await self._client.export_document(
            document_id=document_id,
            export_format="pdf",
            access_token=access_token,
        )

    def assert_default_filename(
        self, response: ExportResponseDto, export_format: str
    ) -> None:
        # Exact equality on the whole deterministic envelope is what proves the
        # filename is a defined default rather than empty, null, or mismatched with
        # the requested format.
        self._assert_export(
            response,
            export_format,
            self.EXPECTED_DEFAULT_CONTENT_DISPOSITION[export_format],
            f"the untitled {export_format} export to carry the defined default filename",
        )

    def assert_filename_rfc5987_encoded_from_title(
        self, response: ExportResponseDto
    ) -> None:
        # A substring check would pass for a raw or mojibake filename; exact equality
        # is what proves the title was UTF-8 percent-encoded and reflected verbatim.
        self._assert_export(
            response,
            "pdf",
            self.EXPECTED_CONTENT_DISPOSITION,
            "the attachment filename to be the RFC 5987-encoded title",
        )

    def _assert_export(
        self,
        response: ExportResponseDto,
        export_format: str,
        expected_content_disposition: str,
        described_as: str,
    ) -> None:
        expected = ExpectedExportEnvelope(
            status_code=200,
            content_type=CONTENT_TYPE_BY_FORMAT[export_format],
            content_disposition=expected_content_disposition,
            body=None,
        )
        assert _envelope_of(response) == expected, (
            f"expected {described_as} — i.e. the export response envelope {expected!r} "
            f"— got {_envelope_of(response)!r}"
        )
        signature = CONTENT_SIGNATURE_BY_FORMAT[export_format]
        assert response.content.startswith(signature), (
            f"expected a real {export_format} payload starting with the {signature!r} "
            f"signature, got first bytes={response.content[:8]!r}"
        )
