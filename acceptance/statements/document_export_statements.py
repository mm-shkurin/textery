import uuid
from typing import ClassVar, Optional

from clients.application.dto.document.export_response_dto import ExportResponseDto
from statements.document_arrange_statements import (
    ACCOUNT_PASSWORD,  # noqa: F401  (re-exported: imported from here by callers)
    SUPPORTED_DOCUMENT_TYPE,
    DocumentArrangeStatements,
)
from statements.export_envelope import assert_export_attachment


class DocumentExportStatements(DocumentArrangeStatements):
    # The sanctioned generic not-found shape (api-specs/documents_export.yaml 404 +
    # error_handling/exception_handlers.py NOT_FOUND_MESSAGE). A non-existent id and a
    # foreign id both resolve to this — never 403, which would confirm the id exists.
    EXPECTED_NOT_FOUND_ERROR: ClassVar[dict] = {
        "error_code": "NOT_FOUND",
        "message": "The requested resource was not found.",
    }
    # The exact JSON-error content type on a refused export (no charset suffix is
    # appended for application/* by Starlette). Pinned, not prefix-matched.
    EXPECTED_ERROR_CONTENT_TYPE: ClassVar[str] = "application/json"
    # The exact wire bytes of the sanctioned 404 body (Starlette JSONResponse serializes
    # with compact separators and no trailing newline). This is the raw content both the
    # non-existent and foreign cases must return byte-for-byte.
    EXPECTED_NOT_FOUND_BYTES: ClassVar[bytes] = (
        b'{"error_code":"NOT_FOUND","message":"The requested resource was not found."}'
    )

    @classmethod
    def _expected_not_found_response(cls) -> ExportResponseDto:
        # The complete sanctioned 404 export response. Both the non-existent-id case
        # and the foreign-owned case must equal this exact DTO — same status, same
        # parsed body, same raw bytes, same headers — so ownership is unprobeable.
        return ExportResponseDto(
            status_code=404,
            body=cls.EXPECTED_NOT_FOUND_ERROR,
            content_type=cls.EXPECTED_ERROR_CONTENT_TYPE,
            content_disposition=None,
            content=cls.EXPECTED_NOT_FOUND_BYTES,
        )

    async def given_authenticated_user_exports_nonexistent_document_as_pdf(
        self,
    ) -> ExportResponseDto:
        access_token = await self._authenticated_access_token()
        nonexistent_document_id = str(uuid.uuid4())
        return await self._client.export_document(
            document_id=nonexistent_document_id,
            export_format="pdf",
            access_token=access_token,
        )

    async def given_document_owned_by_another_account_exported_as_pdf(
        self,
    ) -> ExportResponseDto:
        owner_access_token = await self._authenticated_access_token()
        foreign_document_id = await self._create_document_owned_by(owner_access_token)
        caller_access_token = await self._authenticated_access_token()
        return await self._client.export_document(
            document_id=foreign_document_id,
            export_format="pdf",
            access_token=caller_access_token,
        )

    async def given_owner_exports_their_own_document_as_pdf(self) -> ExportResponseDto:
        # Positive control for the indistinguishability guard: the SAME creation +
        # export path, but exported by the owner. Its outcome must be distinguishable
        # from the sanctioned 404 — otherwise "foreign == not-found" is a tautology
        # that would stay green even if owner-scoping were dropped.
        return await self._owner_exports_fresh_document("pdf")

    async def _owner_exports_fresh_document(
        self, export_format: Optional[str]
    ) -> ExportResponseDto:
        # The arrange every owner-side export scenario shares: authenticate, create a
        # document owned by that caller, export it with the caller-chosen format. The
        # per-scenario `given_*` wrappers name the intent and delegate here.
        access_token = await self._authenticated_access_token()
        own_document_id = await self._create_document_owned_by(access_token)
        return await self._client.export_document(
            document_id=own_document_id,
            export_format=export_format,
            access_token=access_token,
        )

    def assert_distinguishable_from_not_found(self, response: ExportResponseDto) -> None:
        # The owner's own export must NOT collapse to the sanctioned not-found response;
        # a distinguishable outcome is what makes the foreign-vs-nonexistent equality a
        # real owner-scoping proof rather than a vacuous 404-equals-404.
        assert response.body != self.EXPECTED_NOT_FOUND_ERROR, (
            f"expected the owner's own export to be distinguishable from the sanctioned "
            f"not-found response, but it returned the same body={response.body!r}"
        )

    def assert_byte_identical_to_nonexistent_case(
        self, foreign: ExportResponseDto, nonexistent: ExportResponseDto
    ) -> None:
        # Indistinguishability: both the foreign (existing) document and the
        # non-existent id must produce the SAME sanctioned 404 response, pinned to
        # exact literals — same status, same parsed body, byte-for-byte the same raw
        # content, and the same headers (content type + absent Content-Disposition).
        # Pinning each side to the full expected DTO (not merely comparing the two to
        # each other) means two identical 500s, or a leaked attachment header on one
        # side, cannot pass. A frozen dataclass compares all fields recursively.
        expected = self._expected_not_found_response()
        assert nonexistent == expected, (
            f"expected the non-existent-id export to be the sanctioned 404 response "
            f"{expected!r}, got {nonexistent!r}"
        )
        assert foreign == expected, (
            f"expected the foreign-document export to be byte-identical to the "
            f"sanctioned 404 response {expected!r}, got {foreign!r}"
        )

    def assert_valid_pdf_attachment(self, response: ExportResponseDto) -> None:
        # A successful owner export delivers a real PDF, not the JSON placeholder:
        # 200, exact application/pdf, a %PDF- signature, an attachment disposition,
        # and no parsed JSON body.
        assert_export_attachment(response, "pdf")

    def assert_refused_as_not_found(self, response: ExportResponseDto) -> None:
        assert response.status_code == 404, (
            f"expected 404 Not Found refusing the export of a non-existent document, got "
            f"status_code={response.status_code}, body={response.body}"
        )
        assert response.body == self.EXPECTED_NOT_FOUND_ERROR, (
            f"expected the sanctioned generic not-found error shape "
            f"{self.EXPECTED_NOT_FOUND_ERROR!r}, got body={response.body!r}"
        )

    def assert_no_file_returned(self, response: ExportResponseDto) -> None:
        # A refused export returns the JSON error body, never a file. Pinning the
        # exact content type inherently excludes PDF/DOCX; an absent
        # Content-Disposition proves no attachment was offered.
        assert response.content_type == self.EXPECTED_ERROR_CONTENT_TYPE, (
            f"expected the exact JSON error content type "
            f"{self.EXPECTED_ERROR_CONTENT_TYPE!r} on a refused export, got "
            f"content_type={response.content_type!r}"
        )
        assert response.content_disposition is None, (
            f"expected no Content-Disposition on a refused export, got "
            f"content_disposition={response.content_disposition!r}"
        )
