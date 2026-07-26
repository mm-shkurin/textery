import uuid
from typing import ClassVar

from clients.application.application_client import ApplicationClient
from clients.application.dto.auth.login_request_dto import LoginRequestDto
from clients.application.dto.auth.register_request_dto import RegisterRequestDto
from clients.application.dto.auth.verify_request_dto import VerifyRequestDto
from clients.application.dto.document.export_response_dto import ExportResponseDto

ACCOUNT_PASSWORD = "Str0ng!Pass"
PDF_CONTENT_TYPE = "application/pdf"
DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class DocumentExportStatements:
    # The sanctioned generic not-found shape (api-specs/documents_export.yaml 404 +
    # error_handling/exception_handlers.py NOT_FOUND_MESSAGE). A non-existent id and a
    # foreign id both resolve to this — never 403, which would confirm the id exists.
    EXPECTED_NOT_FOUND_ERROR: ClassVar[dict] = {
        "error_code": "NOT_FOUND",
        "message": "The requested resource was not found.",
    }

    def __init__(self, client: ApplicationClient):
        self._client = client

    async def _authenticated_access_token(self) -> str:
        email = f"user-{uuid.uuid4()}@example.com"
        register_response = await self._client.register(
            RegisterRequestDto(
                email=email,
                password=ACCOUNT_PASSWORD,
                confirm_password=ACCOUNT_PASSWORD,
            )
        )
        code = register_response.body.get("verification_code")
        assert code is not None, (
            f"setup: expected registration to issue a verification_code, got body="
            f"{register_response.body}"
        )
        await self._client.verify(VerifyRequestDto(email=email, code=code))
        login_response = await self._client.login(
            LoginRequestDto(email=email, password=ACCOUNT_PASSWORD)
        )
        token = (login_response.body or {}).get("access_token")
        assert token is not None, (
            f"setup: expected login to issue an access_token, got body={login_response.body}"
        )
        return token

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
        # positive content type inherently excludes PDF/DOCX; an absent
        # Content-Disposition proves no attachment was offered.
        content_type = response.content_type or ""
        assert content_type.startswith("application/json"), (
            f"expected the JSON error content type on a refused export, got "
            f"content_type={response.content_type!r}"
        )
        assert response.content_disposition is None, (
            f"expected no Content-Disposition on a refused export, got "
            f"content_disposition={response.content_disposition!r}"
        )
