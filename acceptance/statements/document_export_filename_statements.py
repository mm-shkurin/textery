from typing import ClassVar

from clients.application.dto.document.export_response_dto import ExportResponseDto
from statements.document_export_statements import DocumentExportStatements
from statements.export_envelope import assert_export_envelope
from statements.setup_assertions import assert_setup_ok

# A freshly created document is born at version 1 (Document.create hardcodes
# version=1), so the first save must present 1 as its optimistic-lock token.
CREATED_DOCUMENT_VERSION = 1
# Each successful save is a CAS that increments: the title-bearing setup save takes
# the document from 1 to 2. Pinned as an exact literal rather than read back from the
# response -- an `isinstance(version, int)` check passes for a version the CAS never
# incremented, and threading the observed value forward would let a silently-added
# setup save go unnoticed.
VERSION_AFTER_TITLE_SAVE = 2
# The editor body saved alongside the title. Kept small and well under the content
# cap; the filename scenario asserts on the header, not on this content.
DOCUMENT_CONTENT = "Тело документа"


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
        self._assert_setup_save_succeeded(save, "title-bearing", VERSION_AFTER_TITLE_SAVE)
        return access_token, document_id

    @staticmethod
    def _assert_setup_save_succeeded(save, described_as: str, expected_version: int) -> None:
        assert_setup_ok(save, f"the {described_as} save")
        version = (save.body or {}).get("version")
        assert version == expected_version, (
            f"setup: expected the {described_as} save to leave the document at version "
            f"{expected_version}, got {version!r} (body={save.body})"
        )

    async def given_owner_exports_document_with_cyrillic_title_as_pdf(
        self,
    ) -> ExportResponseDto:
        access_token, document_id = await self._document_carrying_the_cyrillic_title()
        return await self._export_as_pdf(document_id, access_token)

    async def _export_as_pdf(
        self, document_id: str, access_token: str
    ) -> ExportResponseDto:
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
        return await self._owner_exports_fresh_document(export_format)

    def assert_default_filename(
        self, response: ExportResponseDto, export_format: str
    ) -> None:
        # Exact equality on the whole deterministic envelope is what proves the
        # filename is a defined default rather than empty, null, or mismatched with
        # the requested format.
        assert_export_envelope(
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
        assert_export_envelope(
            response,
            "pdf",
            self.EXPECTED_CONTENT_DISPOSITION,
            "the attachment filename to be the RFC 5987-encoded title",
        )
