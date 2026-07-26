from typing import ClassVar, Optional

from clients.application.dto.document.export_response_dto import ExportResponseDto
from statements.document_export_statements import DocumentExportStatements


class DocumentExportFormatStatements(DocumentExportStatements):
    """Format-guard statements for Scenario 1.3 (an unsupported or missing format).

    Subclasses DocumentExportStatements to reuse `_authenticated_access_token`,
    `_create_document_owned_by`, and `assert_no_file_returned`. Kept in its own
    module so the base export statements file stays under the 200-line cap.
    """

    # The sanctioned 422 shape a refused-format export must return: the canonical
    # {error_code, message} envelope (api-specs/documents_export.yaml 422 → the
    # generic Error schema), with a new INVALID_FORMAT code that will map to 422 in
    # error_handling. Pinned exactly, in the same style as the existing 422 codes
    # (INVALID_DOCUMENT_TYPE / INVALID_VERSION), NOT FastAPI's default
    # {"detail": [...]} validation shape — the guard must produce the sanctioned
    # envelope, so format cannot be a framework-validated enum param.
    EXPECTED_INVALID_FORMAT_ERROR: ClassVar[dict] = {
        "error_code": "INVALID_FORMAT",
        "message": "The format must be pdf or docx.",
    }

    async def given_owner_exports_own_document_with_format(
        self, export_format: Optional[str]
    ) -> ExportResponseDto:
        # A document owned by the caller, exported with a caller-chosen format.
        # export_format="xml" is the unsupported case; export_format=None omits the
        # query param entirely (the "no format" case). Both must be refused as 422.
        access_token = await self._authenticated_access_token()
        own_document_id = await self._create_document_owned_by(access_token)
        return await self._client.export_document(
            document_id=own_document_id,
            export_format=export_format,
            access_token=access_token,
        )

    def assert_refused_as_unprocessable(self, response: ExportResponseDto) -> None:
        assert response.status_code == 422, (
            f"expected 422 Unprocessable refusing the export with an unsupported or "
            f"missing format, got status_code={response.status_code}, body={response.body}"
        )
        assert response.body == self.EXPECTED_INVALID_FORMAT_ERROR, (
            f"expected the sanctioned invalid-format error shape "
            f"{self.EXPECTED_INVALID_FORMAT_ERROR!r}, got body={response.body!r}"
        )
